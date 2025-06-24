from datetime import datetime, timezone, timedelta
from .models import TokenCache, get_session


class TokenManager:
    def __init__(self, service_name="colibo"):
        self.service_name = service_name
        self.session = get_session()

    def get_valid_token(self):
        """Get a valid token from the cache or return None."""
        token = (
            self.session.query(TokenCache)
            .filter_by(service_name=self.service_name)
            .first()
        )
        if token and token.is_valid():
            return token.access_token
        return None

    def cache_token(self, access_token, expires_in):
        """Cache a new token or update an existing one."""
        # Calculate expiration time
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        # Check if a record exists
        token = (
            self.session.query(TokenCache)
            .filter_by(service_name=self.service_name)
            .first()
        )

        if token:
            # Update existing token
            token.access_token = access_token
            token.expires_at = expires_at
            token.created_at = datetime.now(timezone.utc)
        else:
            # Create a new token record
            token = TokenCache(
                service_name=self.service_name,
                access_token=access_token,
                expires_at=expires_at,
            )
            self.session.add(token)

        self.session.commit()
