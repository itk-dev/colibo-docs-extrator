import os
import logging

from dotenv import load_dotenv

from colibo.client import Client as ColiboClient
from openwebui.client import Client as WebUIClient

load_dotenv()

COLIBO_CLIENT_ID = os.environ.get("COLIBO_CLIENT_ID")
COLIBO_CLIENT_SECRET = os.environ.get("COLIBO_CLIENT_SECRET")
COLIBO_SCOPE = os.environ.get("COLIBO_SCOPE")

WEBUI_BASE_URL = os.environ.get("WEBUI_BASE_URL")
WEBUI_TOKEN = os.environ.get("WEBUI_TOKEN")
WEBUI_KNOWLEDGE_ID = os.environ.get("WEBUI_KNOWLEDGE_ID")


logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("LeantimeMCP")
logger.setLevel(logging.DEBUG)

webui = WebUIClient(WEBUI_TOKEN, WEBUI_BASE_URL)
colibo = ColiboClient(COLIBO_CLIENT_ID, COLIBO_CLIENT_SECRET, COLIBO_SCOPE)

doc = colibo.get_document(77318)
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
    res = webui.upload_from_string(
        content='# ' + item['title'] + "\n\n" + item['description'] + "\n\n" + item['body'],
        filename="colibo-" + str(item['id']) + '.md',
        content_type='text/markdown',
        metadata={
            'knowledge-id': WEBUI_KNOWLEDGE_ID,
    })
    webui.add_file_to_knowledge(WEBUI_KNOWLEDGE_ID, res['id'])
