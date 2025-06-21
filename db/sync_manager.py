# db/sync_manager.py
from datetime import datetime
from .models import SyncedDocument, get_session

class SyncManager:
    """Manager class for document synchronization operations."""

    def __init__(self, session=None):
        """Initialize with an optional session."""
        self.session = session or get_session()

    def record_sync(self, colibo_doc_id, webui_doc_id, title=None, filename=None):
        """Record a new sync or update existing record."""
        doc = self.session.query(SyncedDocument).filter_by(colibo_doc_id=colibo_doc_id).first()

        if doc:
            # Update existing record
            doc.webui_doc_id = webui_doc_id
            if title:
                doc.title = title
            if filename:
                doc.filename = filename
            doc.last_synced = datetime.utcnow()
            doc.is_deleted = False
        else:
            # Create new record
            doc = SyncedDocument(
                colibo_doc_id=colibo_doc_id,
                webui_doc_id=webui_doc_id,
                title=title,
                filename=filename or f"colibo-{colibo_doc_id}.md"
            )
            self.session.add(doc)

        self.session.commit()
        return doc

    def mark_deleted(self, colibo_doc_id):
        """Mark a document as deleted."""
        doc = self.session.query(SyncedDocument).filter_by(colibo_doc_id=colibo_doc_id).first()
        if doc:
            doc.is_deleted = True
            doc.last_synced = datetime.utcnow()
            self.session.commit()
        return doc

    def get_document(self, colibo_doc_id):
        """Get a synced document by Colibo ID."""
        return self.session.query(SyncedDocument).filter_by(colibo_doc_id=colibo_doc_id).first()

    def get_all_documents(self, include_deleted=False):
        """Get all synced documents."""
        query = self.session.query(SyncedDocument)
        if not include_deleted:
            query = query.filter_by(is_deleted=False)
        return query.all()

    def get_webui_id(self, colibo_doc_id):
        """Get WebUI document ID for a given Colibo document ID."""
        doc = self.get_document(colibo_doc_id)
        return doc.webui_doc_id if doc else None