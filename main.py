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
            webui.add_file_to_knowledge(WEBUI_KNOWLEDGE_ID, res['id'])
            logger.info(f"Successfully uploaded item {item['id']}")

@cli.command()
@click.option('--colibo-id', help='Colibo document ID to delete', required=True, type=int)
def delete_doc(colibo_id):
    """Delete a document from WebUI and mark it as deleted in the database."""
    webui = WebUIClient(WEBUI_TOKEN, WEBUI_BASE_URL)

    # Get document from database
    doc = sync_manager.get_document(colibo_id)
    if not doc:
        logger.error(f"Document with Colibo ID {colibo_id} not found in database")
        return

    # Delete from WebUI
    try:
        webui.delete_file(doc.webui_doc_id)
        logger.info(f"Deleted document {colibo_id} from WebUI")

        # Mark as deleted in database
        sync_manager.mark_deleted(colibo_id)
        logger.info(f"Marked document {colibo_id} as deleted in database")
    except Exception as e:
        logger.error(f"Failed to delete document {colibo_id}: {str(e)}")

@cli.command()
def list_docs():
    """List all synced documents."""
    docs = sync_manager.get_all_documents(include_deleted=False)
    if not docs:
        logger.info("No synced documents found")
        return

    for doc in docs:
        logger.info(f"Colibo ID: {doc.colibo_doc_id}, WebUI ID: {doc.webui_doc_id}, "
                    f"Title: {doc.title}, Last Synced: {doc.last_synced}")

if __name__ == '__main__':
    cli()

