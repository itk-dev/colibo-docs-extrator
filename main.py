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
    logger.info(f"Uploading document {doc['id']}")
    res = webui.upload_from_string(
        content='# ' + doc['title'] + "\n\n" + doc['description'],
        filename="colibo-" + str(doc['id']) + '.md',
        content_type='text/markdown',
        metadata={
            'knowledge-id': WEBUI_KNOWLEDGE_ID,
        })
    webui.add_file_to_knowledge(WEBUI_KNOWLEDGE_ID, res['id'])

    docs = colibo.get_children(doc['id'])
    for item in docs:
        # Check if all content fields are None
        if item['title'] is None and item['description'] is None and item['body'] is None:
            logger.info(f"Skipping item {item['id']} as all content fields are None")
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
            logger.info(f"Updating item {item['id']}")
            res = webui.update_file_content(existing.webui_doc_id, content)

            ## TODO: handle update result?

            logger.info(f"Successfully updated item {item['id']}")
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
            logger.info(f"Successfully uploaded item {item['id']}")

            # Record sync in the database
            sync_manager.record_sync(
                colibo_doc_id=item['id'],
                webui_doc_id=webui_doc_id,
            )

            # Add a summary at the end
        total_docs = doc['childCount'] + 1 if doc['childCount'] else 1
        click.echo("")
        click.echo(click.style(f"Sync Summary:", fg="blue", bold=True))
        click.echo(f"Total documents processed: {total_docs}")
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
        logger.error(f"Document with Colibo ID {colibo_id} not found in database")
        return

    # Delete from WebUI
    try:
        webui.delete_file(doc.webui_doc_id)
        sync_manager.mark_deleted(colibo_id)

        click.echo("")
        click.echo(click.style("✓ Document deleted successfully!", fg="green", bold=True))
        click.echo(f"Colibo ID: {colibo_id}")
        click.echo(f"WebUI ID: {doc.webui_doc_id}")
    except Exception as e:
        click.echo("")
        click.echo(click.style("✗ Failed to delete document!", fg="red", bold=True))
        click.echo(f"Error: {str(e)}")


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

