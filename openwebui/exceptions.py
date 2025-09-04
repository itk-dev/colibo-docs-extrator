class WebUIError(Exception):
    """Base exception for WebUI API errors."""

    def __init__(self, message, status_code=None, response_text=None):
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(message)


class WebUINotFoundError(WebUIError):
    """Raised when a resource is not found (404)."""

    def __init__(self, resource_id, resource_type="resource"):
        self.resource_id = resource_id
        self.resource_type = resource_type
        message = f"{resource_type.capitalize()} with ID '{resource_id}' not found"
        super().__init__(message, status_code=404)


class WebUIUnauthorizedError(WebUIError):
    """Raised when authentication fails (401)."""

    def __init__(self):
        super().__init__(
            "Authentication failed - invalid or expired token", status_code=401
        )


class WebUIServerError(WebUIError):
    """Raised when server encounters an error (5xx)."""

    pass
