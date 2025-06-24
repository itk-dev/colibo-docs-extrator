# db/sync_manager.py
from datetime import datetime, timezone
from .models import SyncedDocument, get_session


class SyncManager:
    """Manager class for document synchronization operations."""

    def __init__(self, session=None):
        """Initialize with an optional session."""
        self.session = session or get_session()

    def record_sync(self, colibo_doc_id, knowledge_id, webui_doc_id: str = None):
        """Record a new sync or update an existing record."""
        doc = (
            self.session.query(SyncedDocument)
            .filter_by(colibo_doc_id=colibo_doc_id, knowledge_id=knowledge_id)
            .first()
        )

        if doc:
            # Update existing record
            if webui_doc_id is not None:
                doc.webui_doc_id = webui_doc_id
            doc.last_synced = datetime.now(timezone.utc)
        else:
            # Create a new record
            doc = SyncedDocument(
                colibo_doc_id=colibo_doc_id,
                webui_doc_id=webui_doc_id,
                knowledge_id=knowledge_id,
                last_synced=datetime.now(timezone.utc),
            )
            self.session.add(doc)

        self.session.commit()
        return doc

    def delete_document(self, colibo_doc_id, knowledge_id):
        """Permanently delete a document from the database."""
        doc = (
            self.session.query(SyncedDocument)
            .filter_by(colibo_doc_id=colibo_doc_id, knowledge_id=knowledge_id)
            .first()
        )
        if doc:
            self.session.delete(doc)
            self.session.commit()
        return doc

    def get_document(self, colibo_doc_id, knowledge_id):
        """Get a synced document by Colibo ID."""
        return (
            self.session.query(SyncedDocument)
            .filter_by(colibo_doc_id=colibo_doc_id, knowledge_id=knowledge_id)
            .first()
        )

    def get_all_documents(self):
        """Get all synced documents."""
        query = self.session.query(SyncedDocument)
        return query.all()

    def get_webui_id(self, colibo_doc_id, knowledge_id: str = None):
        """Get WebUI document ID for a given Colibo document ID."""
        doc = self.get_document(colibo_doc_id, knowledge_id)
        return doc.webui_doc_id if doc else None
