
def build_content(item):
    """Build the content of a document."""
    # Check if all content fields are None
    if (
        item["title"] is None
        and item["description"] is None
        and item["body"] is None
    ):
        return None

    # Prepare content with available data
    content_parts = []
    if item["title"]:
        content_parts.append("# " + item["title"])
    if item["description"]:
        content_parts.append(item["description"])
    if item["body"]:
        content_parts.append(item["body"])

    return "\n\n".join(content_parts)

def filename(doc_id: int, extension: str = "md"):
    """ Build a filename for a document"""
    return "colibo-" + str(doc_id) + "." + extension

def knowledge_exists(knowledge_id: str):
    """Check if knowledge exists in the knowledge base"""
    return False