import os
import logging
import click

from dotenv import load_dotenv

from colibo.client import Client as ColiboClient
from openwebui.client import Client as WebUIClient

from db.models import init_db
from db.sync_manager import SyncManager

load_dotenv()
# Colibo settings
COLIBO_CLIENT_ID = os.environ.get("COLIBO_CLIENT_ID")
COLIBO_CLIENT_SECRET = os.environ.get("COLIBO_CLIENT_SECRET")
COLIBO_SCOPE = os.environ.get("COLIBO_SCOPE")
# Open-webui settings
WEBUI_BASE_URL = os.environ.get("WEBUI_BASE_URL")
WEBUI_TOKEN = os.environ.get("WEBUI_TOKEN")
WEBUI_KNOWLEDGE_ID = os.environ.get("WEBUI_KNOWLEDGE_ID")

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("LeantimeMCP")
logger.setLevel(logging.DEBUG)

# Initialize database
init_db()
sync_manager = SyncManager()


@click.group()
def cli():
    """My Symfony-style CLI application"""
    pass


@cli.command()
@click.option('--doc-id', default=77318, help='Id of the root document.')
def sync(doc_id: int = 77318):
    webui = WebUIClient(WEBUI_TOKEN, WEBUI_BASE_URL)
    colibo = ColiboClient(COLIBO_CLIENT_ID, COLIBO_CLIENT_SECRET, COLIBO_SCOPE)

    doc = colibo.get_document(doc_id)
    res = webui.upload_from_string(
        content='# ' + doc['title'] + "\n\n" + doc['description'],
        filename="colibo-" + str(doc['id']) + '.md',
        content_type='text/markdown',
        metadata={
            'knowledge-id': WEBUI_KNOWLEDGE_ID,
        })
    webui.add_file_to_knowledge(WEBUI_KNOWLEDGE_ID, res['id'])

    # Record sync in the database
    sync_manager.record_sync(
        colibo_doc_id=doc_id,
        webui_doc_id=res['id'],
    )

    docs = colibo.get_children(doc['id'])
    total_docs = doc['childCount'] + 1 if doc['childCount'] else 1

    # Track statistics
    processed_count = 1  # Start with 1 for the root document
    skipped_count = 0
    updated_count = 0
    new_count = 1

    # Process each child document with progress bar
    with click.progressbar(docs, label="Syncing documents", length=total_docs) as bar:
        for item in bar:
            # Check if all content fields are None
            if item['title'] is None and item['description'] is None and item['body'] is None:
                skipped_count += 1
                continue

            # Prepare content with available data
            content_parts = []
            if item['title']:
                content_parts.append('# ' + item['title'])
            if item['description']:
                content_parts.append(item['description'])
            if item['body']:
                content_parts.append(item['body'])

            # Join the content parts with double newlines
            content = '\n\n'.join(content_parts)

            # Check if the document already exists
            existing = sync_manager.get_document(item['id'])

            if existing:
                # Update existing document
                res = webui.update_file_content(existing.webui_doc_id, content)
                ## TODO check that the doc restructured successfully
                updated_count += 1
            else:
                res = webui.upload_from_string(
                    content=content,
                    filename="colibo-" + str(item['id']) + '.md',
                    content_type='text/markdown',
                    metadata={
                        'knowledge-id': WEBUI_KNOWLEDGE_ID,
                    })
                webui_doc_id = res['id']
                webui.add_file_to_knowledge(WEBUI_KNOWLEDGE_ID, webui_doc_id)
                new_count += 1

                # Record sync in the database
                sync_manager.record_sync(
                    colibo_doc_id=item['id'],
                    webui_doc_id=webui_doc_id,
                )

            processed_count += 1

    # Add a summary at the end
    click.echo("")
    click.echo(click.style(f"Sync Summary:", fg="blue", bold=True))
    click.echo(f"Total documents processed: {processed_count}")
    click.echo(f"New documents created: {new_count}")
    click.echo(f"Existing documents updated: {updated_count}")
    click.echo(f"Documents skipped: {skipped_count}")
    click.echo(f"Root document: {doc_id} (Colibo)")
    click.echo("")
    click.echo(click.style("✓ Sync completed successfully!", fg="green", bold=True))

@cli.command()
@click.option('--colibo-id', help='Colibo document ID to delete', required=True, type=int)
def delete_doc(colibo_id):
    """Delete a document from WebUI and mark it as deleted in the database."""
    webui = WebUIClient(WEBUI_TOKEN, WEBUI_BASE_URL)

    # Get document from the database
    doc = sync_manager.get_document(colibo_id)
    if not doc:
        click.echo(click.style(f"Document with Colibo ID {colibo_id} not found in database", fg="red", bold=True))
        return

    # Delete from WebUI
    try:
        webui.delete_file(doc.webui_doc_id)
        sync_manager.delete_document(colibo_id)

        click.echo("")
        click.echo(click.style("✓ Document deleted successfully!", fg="green", bold=True))
        click.echo(f"Colibo ID: {colibo_id}")
        click.echo(f"WebUI ID: {doc.webui_doc_id}")
    except Exception as e:
        click.echo("")
        click.echo(click.style("✗ Failed to delete document!", fg="red", bold=True))
        click.echo(f"Error: {str(e)}")

@cli.command()
@click.option('--confirm', is_flag=True, help='Confirm deletion without prompting')
def delete_all_docs(confirm):
    """Delete all documents from WebUI and remove them from the database."""
    webui = WebUIClient(WEBUI_TOKEN, WEBUI_BASE_URL)

    # Get all documents
    docs = sync_manager.get_all_documents(include_deleted=True)
    if not docs:
        click.echo(click.style("No documents found to delete", fg="yellow", bold=True))
        return

    # Confirm deletion
    if not confirm:
        click.echo(f"This will delete {len(docs)} documents from WebUI and the database.")
        click.echo(click.style("WARNING: This action cannot be undone!", fg="red", bold=True))
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
                webui.delete_file(doc.webui_doc_id)

                # Delete from database
                sync_manager.delete_document(doc.colibo_doc_id)

                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append((doc.colibo_doc_id, doc.webui_doc_id, str(e)))

    # Print summary
    click.echo("")
    if success_count > 0:
        click.echo(click.style(f"✓ Successfully deleted {success_count} documents", fg="green", bold=True))

    if error_count > 0:
        click.echo(click.style(f"✗ Failed to delete {error_count} documents", fg="red", bold=True))

        # Show errors if there are any
        if errors:
            click.echo("\nErrors:")
            for colibo_id, webui_id, error in errors:
                click.echo(f"  - Colibo ID: {colibo_id}, WebUI ID: {webui_id}")
                click.echo(f"    Error: {error}")

@cli.command()
def list_docs():
    """List all synced documents."""
    docs = sync_manager.get_all_documents(include_deleted=False)
    if not docs:
        click.echo("No synced documents found")
        return

    # Create a table with Click's formatting
    headers = ["Colibo ID", "WebUI ID", "Last Synced"]
    rows = []

    for doc in docs:
        # Format the datetime to be more readable
        last_synced = doc.last_synced.strftime("%Y-%m-%d %H:%M:%S")

        rows.append([
            str(doc.colibo_doc_id),
            doc.webui_doc_id,
            last_synced,
        ])

    # Print the table
    click.echo(click.style("\nSynced Documents:", fg="green", bold=True))

    # Calculate column widths based on content
    col_widths = [max(len(str(row[i])) for row in [headers] + rows) for i in range(len(headers))]

    # Print header
    header_row = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    click.echo(click.style(header_row, bold=True))
    click.echo("-" * len(header_row))

    # Print rows
    for row in rows:
        formatted_row = " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row))
        click.echo(formatted_row)

    click.echo("-" * len(header_row))
    click.echo(f"\nTotal: {len(rows)} documents")


if __name__ == '__main__':
    cli()

