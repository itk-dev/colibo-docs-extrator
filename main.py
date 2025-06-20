import os
import logging

from colibo.client import Client
from dotenv import load_dotenv

load_dotenv()
COLIBO_CLIENT_ID = os.environ.get("COLIBO_CLIENT_ID")
COLIBO_CLIENT_SECRET = os.environ.get("COLIBO_CLIENT_SECRET")
COLIBO_SCOPE = os.environ.get("COLIBO_SCOPE")

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("LeantimeMCP")
logger.setLevel(logging.DEBUG)

client = Client(COLIBO_CLIENT_ID, COLIBO_CLIENT_SECRET, COLIBO_SCOPE)

doc = client.get_document(77318)

from pprint import pprint
pprint(doc)
