[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

# Colibo document extractor

A synchronization tool that extracts documents from Colibo and uploads them to Open-WebUI knowledge base.

## Overview

Colibo document extractor is a command-line utility that synchronizes documents between Colibo (a document management
system) and Open-WebUI (a knowledge base platform). It allows you to extract documents from Colibo, maintaining their
structure, and upload them to your Open-WebUI knowledge base for enhanced accessibility and AI-powered search.

## Features

- **Document Synchronization**: Synchronize documents from Colibo to Open-WebUI starting from a specified root document
- **Content Management**: Update existing documents when content changes
- **Document Tracking**: Keep track of synchronized documents in a local database
- **Document Deletion**: Remove documents from Open-WebUI either individually or in bulk
- **Listing Functionality**: View all currently synchronized documents

## Installation

TODO: write about the setup local (if not using docker image).

## Configuration

Create a file in the project root with the following variables: `.env`

``` 
# Colibo settings
COLIBO_BASE_URL=https://xxxx
COLIBO_CLIENT_ID=your_client_id
COLIBO_CLIENT_SECRET=your_client_secret
COLIBO_SCOPE=your_scope

# Open-webui settings
WEBUI_BASE_URL=your_webui_url
WEBUI_TOKEN=your_webui_token
WEBUI_KNOWLEDGE_ID=your_knowledge_id

# Application
DATABASE_URL=sqlite:///sync.db
```

## Usage

### Synchronize Documents

Synchronize documents from Colibo to Open-WebUI (if `--force-update` not given, only documents updated since last sync
is updated in open-webui):

``` bash
python main.py sync --root-doc-id xxxxx
```

Options:

- `--root-doc-id`: ID of the root document in Colibo
- `--quiet`: Suppress progress display
- `--knowledge-id`: Knowledge id from Open-Webui
- `--force-update`: Force update all documents

### Delete a Document

Delete a specific document from Open-WebUI:

``` bash
python main.py sync:delete --colibo-id ID
```

Options:

- `--knowledge-id`: Knowledge id from Open-Webui

### Delete All Documents

Remove all synchronized documents from Open-WebUI:

``` bash
python main.py sync:delete-all
```

Options:

- `--knowledge-id`: Knowledge id from Open-Webui
- `--confirm` to bypass the confirmation prompt.

### List Documents

List all synchronized documents:

``` bash
python main.py db:list
```

### Get knowledge

Check that knowledge exists in Open-Webui.

```bash
python main.py knowledge:get --knowledge-id xxxx-xxxx-xxxx
```

Options:

- `--knowledge-id`: Knowledge id from Open-Webui (defaults to ID from environment)

### Get data from colibo (debug)

This command appears to be a debugging tool that provides detailed information about a Colibo document and its children.
Usage example:

``` bash
python main.py debug:colibo:sync --root-doc-id XXXX
```

Options:

- : ID of the root document to debug `--root-doc-id`

### Get single document from colibo

This command retrieves and displays information about a specific document from Colibo.
Usage example:

``` bash
python main.py debug:colibo:get-doc DOC_ID
```

Arguments:

- `DOC_ID`: The ID of the Colibo document to retrieve (required)

## Docker Support

A Dockerfile is provided for containerized deployment.
Build the container:

``` bash
docker build -t colibo-document-extrator .
```

Run the container:

``` bash
docker run --rm --volume .env:/app/.env --volume ./sync.db:/app/sync.db colibo-document-extrator --help
```

## Todo

- Add support for files attached to Colibo documents
- Handle external links in colibo

## License

[License Information]
