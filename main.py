import click
import contextlib
import logging
import os


from dotenv import load_dotenv

from colibo.client import Client as ColiboClient
from openwebui.client import Client as WebUIClient

from db.models import init_db
from db.sync_manager import SyncManager

load_dotenv()
# Colibo settings
COLIBO_BASE_URL = os.environ.get("COLIBO_BASE_URL")
COLIBO_CLIENT_ID = os.environ.get("COLIBO_CLIENT_ID")
COLIBO_CLIENT_SECRET = os.environ.get("COLIBO_CLIENT_SECRET")
COLIBO_SCOPE = os.environ.get("COLIBO_SCOPE")
# Open-webui settings
WEBUI_BASE_URL = os.environ.get("WEBUI_BASE_URL")
WEBUI_TOKEN = os.environ.get("WEBUI_TOKEN")
WEBUI_KNOWLEDGE_ID = os.environ.get("WEBUI_KNOWLEDGE_ID")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("colibo-sync")
logger.setLevel(logging.DEBUG)

# Initialize database
init_db()
sync_manager = SyncManager()


@click.group()
def cli():
    """Calibo document synchronization tool."""
    pass


@contextlib.contextmanager
def silent_progressbar(iterable, **kwargs):
    """A context manager that yields the iterable without displaying progress."""
    yield iterable


###
# @todo:
#   - files attached in calibo docs
#   - maybe move knowledge id to CLI option
#   - validation of knowledge id
#   - Use docs delete field
###


@cli.command()
@click.option("--root-doc-id", help="Id of the root document.")
@click.option("--quiet", is_flag=True, help="Do not display progress.")
@click.option(
    "--knowledge-id",
    help="ID of the knowledge resource to retrieve",
    default=WEBUI_KNOWLEDGE_ID,
)
def sync(root_doc_id, quiet: bool = False, knowledge_id: str = WEBUI_KNOWLEDGE_ID):
    """Synchronize documents from Colibo to Open-Webui."""
    webui = WebUIClient(WEBUI_TOKEN, WEBUI_BASE_URL)
    colibo = ColiboClient(
        COLIBO_BASE_URL, COLIBO_CLIENT_ID, COLIBO_CLIENT_SECRET, COLIBO_SCOPE
    )

    # Custom echo function that respects the quiet flag
    def echo(*args, **kwargs):
        if not quiet:
            click.echo(*args, **kwargs)

    doc = colibo.get_document(root_doc_id)
    echo(f"Syncing root document {root_doc_id} (Colibo)")
    res = webui.upload_from_string(
        content="# " + doc["title"] + "\n\n" + doc["description"],
        filename="colibo-" + str(doc["id"]) + ".md",
        content_type="text/markdown",
        metadata={},
    )
    webui.add_file_to_knowledge(knowledge_id, res["id"])

    # Record sync in the database
    sync_manager.record_sync(
        colibo_doc_id=root_doc_id,
        webui_doc_id=res["id"],
        knowledge_id=knowledge_id,
    )

    docs = colibo.get_children(doc["id"])

    # Track statistics
    processed_count = 1  # Start with 1 for the root document
    skipped_count = 0
    updated_count = 0
    new_count = 1
    page_count = 0
    link_count = 0

    # Choose the appropriate progress bar based on the quiet flag
    progress_context = silent_progressbar if quiet else click.progressbar

    # Process each child document with a progress bar
    with progress_context(docs, label="Syncing child documents") as bar:
        for item in bar:
            # Check if all content fields are None
            if (
                item["title"] is None
                and item["description"] is None
                and item["body"] is None
            ):
                skipped_count += 1
                continue

            # Prepare content with available data
            content_parts = []
            if item["title"]:
                content_parts.append("# " + item["title"])
            if item["description"]:
                content_parts.append(item["description"])
            if item["body"]:
                content_parts.append(item["body"])

            # Join the content parts with double newlines
            content = "\n\n".join(content_parts)

            # Check if the document already exists
            existing = sync_manager.get_document(item["id"], knowledge_id)

            if existing:
                # Update existing document
                res = webui.update_file_content(existing.webui_doc_id, content)
                ## TODO check that the doc restructured successfully
                updated_count += 1
            else:
                res = webui.upload_from_string(
                    content=content,
                    filename="colibo-" + str(item["id"]) + ".md",
                    content_type="text/markdown",
                    metadata={},
                )
                webui_doc_id = res["id"]
                red = webui.add_file_to_knowledge(knowledge_id, webui_doc_id)
                ## TODO check that the doc is add to the knowledge successfully
                new_count += 1

                # Record sync in the database
                sync_manager.record_sync(
                    colibo_doc_id=item["id"],
                    webui_doc_id=webui_doc_id,
                    knowledge_id=knowledge_id,
                )

            doctype = item.get("doctype", {})
            if doctype == "page":
                page_count += 1
            elif doctype == "link":
                link_count += 1

            processed_count += 1

    # Add a summary at the end
    echo("")
    echo(click.style(f"Sync Summary:", fg="blue", bold=True))
    echo(f"Total documents processed: {processed_count}")
    echo(f"New documents created: {new_count}")
    echo(f"Existing documents updated: {updated_count}")
    echo(f"Documents skipped: {skipped_count}")
    echo(f"Page documents: {page_count}")
    echo(f"Link documents: {link_count}")
    echo(f"Root document: {root_doc_id} (Colibo)")
    echo("")
    echo(click.style("✓ Sync completed successfully!", fg="green", bold=True))


@cli.command()
@click.option(
    "--colibo-id", help="Colibo document ID to delete", required=True, type=int
)
@click.option(
    "--knowledge-id",
    help="ID of the knowledge resource to retrieve",
    default=WEBUI_KNOWLEDGE_ID,
)
def delete_doc(colibo_id, knowledge_id: str = WEBUI_KNOWLEDGE_ID):
    """Delete a document from WebUI and mark it as deleted in the database."""
    webui = WebUIClient(WEBUI_TOKEN, WEBUI_BASE_URL)

    # Get a document from the database
    doc = sync_manager.get_document(colibo_id, knowledge_id)
    if not doc:
        click.echo(
            click.style(
                f"Document with Colibo ID {colibo_id} not found in database",
                fg="red",
                bold=True,
            )
        )
        return

    # Delete from WebUI
    try:
        webui.remove_file_from_knowledge(knowledge_id, doc.webui_doc_id)
        webui.delete_file(doc.webui_doc_id)
        sync_manager.delete_document(colibo_id, knowledge_id)

        click.echo("")
        click.echo(
            click.style("✓ Document deleted successfully!", fg="green", bold=True)
        )
        click.echo(f"Colibo ID: {colibo_id}")
        click.echo(f"WebUI ID: {doc.webui_doc_id}")
    except Exception as e:
        click.echo("")
        click.echo(click.style("✗ Failed to delete document!", fg="red", bold=True))
        click.echo(f"Error: {str(e)}")


@cli.command()
@click.option("--confirm", is_flag=True, help="Confirm deletion without prompting")
@click.option(
    "--knowledge-id",
    help="ID of the knowledge resource to retrieve",
    default=WEBUI_KNOWLEDGE_ID,
)
def delete_all_docs(confirm, knowledge_id: str = WEBUI_KNOWLEDGE_ID):
    """Delete all documents from WebUI and remove them from the database."""
    webui = WebUIClient(WEBUI_TOKEN, WEBUI_BASE_URL)

    # Get all documents
    docs = sync_manager.get_all_documents()
    if not docs:
        click.echo(click.style("No documents found to delete", fg="yellow", bold=True))
        return

    # Confirm deletion
    if not confirm:
        click.echo(
            f"This will delete {len(docs)} documents from WebUI and the database."
        )
        click.echo(
            click.style("WARNING: This action cannot be undone!", fg="red", bold=True)
        )
        if not click.confirm("Do you want to continue?"):
            click.echo("Operation cancelled.")
            return

    # Track statistics
    success_count = 0
    error_count = 0
    errors = []

    # Process each document
    with click.progressbar(docs, label="Deleting documents") as bar:
        for doc in bar:
            try:
                # Delete from WebUI
                webui.remove_file_from_knowledge(knowledge_id, doc.webui_doc_id)
                webui.delete_file(doc.webui_doc_id)

                # Delete from database
                sync_manager.delete_document(doc.colibo_doc_id, knowledge_id)

                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append((doc.colibo_doc_id, doc.webui_doc_id, str(e)))

    # Print summary
    click.echo("")
    if success_count > 0:
        click.echo(
            click.style(
                f"✓ Successfully deleted {success_count} documents",
                fg="green",
                bold=True,
            )
        )

    if error_count > 0:
        click.echo(
            click.style(
                f"✗ Failed to delete {error_count} documents", fg="red", bold=True
            )
        )

        # Show errors if there are any
        if errors:
            click.echo("\nErrors:")
            for colibo_id, webui_id, error in errors:
                click.echo(f"  - Colibo ID: {colibo_id}, WebUI ID: {webui_id}")
                click.echo(f"    Error: {error}")


@cli.command()
def list_docs():
    """List all synced documents."""
    docs = sync_manager.get_all_documents()
    if not docs:
        click.echo("No synced documents found")
        return

    # Create a table with Click's formatting
    headers = ["Colibo ID", "WebUI ID", "Last Synced"]
    rows = []

    for doc in docs:
        # Format the datetime to be more readable
        last_synced = doc.last_synced.strftime("%Y-%m-%d %H:%M:%S")

        rows.append(
            [
                str(doc.colibo_doc_id),
                doc.webui_doc_id,
                last_synced,
            ]
        )

    # Print the table
    click.echo(click.style("\nSynced Documents:", fg="green", bold=True))

    # Calculate column widths based on content
    col_widths = [
        max(len(str(row[i])) for row in [headers] + rows) for i in range(len(headers))
    ]

    # Print header
    header_row = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    click.echo(click.style(header_row, bold=True))
    click.echo("-" * len(header_row))

    # Print rows
    for row in rows:
        formatted_row = " | ".join(
            str(cell).ljust(col_widths[i]) for i, cell in enumerate(row)
        )
        click.echo(formatted_row)

    click.echo("-" * len(header_row))
    click.echo(f"\nTotal: {len(rows)} documents")


@cli.command()
@click.option(
    "--knowledge-id",
    help="ID of the knowledge resource to retrieve",
    default=WEBUI_KNOWLEDGE_ID,
)
def get_knowledge(knowledge_id):
    """Retrieve information about a specific knowledge resource."""
    webui = WebUIClient(WEBUI_TOKEN, WEBUI_BASE_URL)

    try:
        knowledge = webui.get_knowledge(knowledge_id)
        click.echo(click.style(f"✓ Knowledge resource found:", fg="green", bold=True))
        click.echo(f"ID: {knowledge['id']}")
        click.echo(f"Name: {knowledge['name']}")
        click.echo(f"Description: {knowledge['description']}")
    except Exception as e:
        click.echo(
            click.style("✗ Failed to retrieve knowledge resource!", fg="red", bold=True)
        )
        click.echo(f"Error: {str(e)}")

@cli.command()
@click.option("--root-doc-id", help="Id of the root document.")
def debug(root_doc_id):
    colibo = ColiboClient(
        COLIBO_BASE_URL, COLIBO_CLIENT_ID, COLIBO_CLIENT_SECRET, COLIBO_SCOPE
    )
    doc = colibo.get_document(root_doc_id)
    click.echo(click.style("Root document information:", fg="green", bold=True))
    click.echo(f"Fetched root document {root_doc_id}")
    click.echo(f"Title: {doc['title']}")
    click.echo(f"Description: {doc['description']}")
    click.echo(f"Body: {doc['body']}")
    click.echo(f"Child count: {doc['childCount']}")
    click.echo(f"Created at: {doc['created']}")
    click.echo(f"Updated at: {doc['updated']}")
    click.echo(f"Keywords: {doc['keywords']}")
    click.echo(f"\n")

    counter = 0
    docs = colibo.get_children(doc["id"], visited_ids={ root_doc_id })
    click.echo(click.style("Child docs:", fg="green", bold=True))
    for item in docs:
        counter += 1
        doctype = item['doctype']
        doctype_color = "white"
        if doctype == "page":
            doctype_color = "green"
        elif doctype == "link":
            doctype_color = "red"
        elif doctype == "folder":
            doctype_color = "yellow"
        elif doctype == "file":
            doctype_color = "blue"

        click.echo(f"Fetched child document {item['id']}")
        click.echo(f"Type: {click.style(doctype, fg=doctype_color)}")
        click.echo(f"Title: {item['title']}")
        click.echo(f"Created at: {item['created']}")
        click.echo(f"Updated at: {item['updated']}")
        click.echo(f"Keywords: {doc['keywords']}")
        click.echo(f"\n")
    click.echo(f"Total child docs: {click.style(counter, fg='blue')}")


if __name__ == "__main__":
    cli()
