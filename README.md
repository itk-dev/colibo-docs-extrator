# Colibo document extractor

A synchronization tool that extracts documents from Colibo and uploads them to Open WebUI knowledge base.

## Overview

Colibo Loader is a command-line utility that synchronizes documents between Colibo (a document management system) and
Open WebUI (a knowledge base platform). It allows you to extract documents from Colibo, maintaining their structure, and
upload them to your Open WebUI knowledge base for enhanced accessibility and AI-powered search.

## Features

- **Document Synchronization**: Synchronize documents from Colibo to Open WebUI starting from a specified root document
- **Content Management**: Update existing documents when content changes
- **Document Tracking**: Keep track of synchronized documents in a local database
- **Document Deletion**: Remove documents from WebUI either individually or in bulk
- **Listing Functionality**: View all currently synchronized documents

## Installation

TODO: write about the setup for both local and docke image.

## Configuration

Create a file in the project root with the following variables: `.env`

``` 
# Colibo settings
COLIBO_CLIENT_ID=your_client_id
COLIBO_CLIENT_SECRET=your_client_secret
COLIBO_SCOPE=your_scope

# Open-webui settings
WEBUI_BASE_URL=your_webui_url
WEBUI_TOKEN=your_webui_token
WEBUI_KNOWLEDGE_ID=your_knowledge_id
```

## Usage

### Synchronize Documents

Synchronize documents from Colibo to Open WebUI:

``` bash
python main.py sync --root-doc-id xxxxx
```

Options:

- : ID of the root document in Colibo (default: 77318) `--root-doc-id`
- : Suppress progress display `--quiet`

### Delete a Document

Delete a specific document from WebUI:

``` bash
python main.py delete-doc --colibo-id ID
```

### Delete All Documents

Remove all synchronized documents from WebUI:

``` bash
python main.py delete-all-docs
```

Add `--confirm` to bypass the confirmation prompt.

### List Documents

View all synchronized documents:

``` bash
python main.py list-docs
```

## Project Structure

- `colibo/`: Colibo client implementation
- `openwebui/`: Open WebUI client implementation
- `db/`: Database models and synchronization management
- : Command-line interface and main functionality `main.py`

## Docker Support

A Dockerfile is provided for containerized deployment.
Build the container:

``` bash
docker build -t colibo-loader .
```

Run the container:

``` bash
docker run --env-file .env colibo-loader python main.py sync
```

## Todo
- 

- Add support for files attached to Colibo documents
- Make knowledge ID a CLI option
- Implement validation for knowledge ID

## License

[License Information]
