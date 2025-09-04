from datetime import datetime
from markdownify import markdownify

import requests
import urllib.parse
import re
from datetime import datetime, timedelta

from db.token_manager import TokenManager


class Client:
    def __init__(self, base_url, client_id, client_secret, scope):
        self.base_url = base_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self.access_token = None
        self.token_manager = TokenManager("colibo")

    def _get_token(self):
        """Get a valid access token, renewing if necessary."""
        # Try to get from the cache first
        cached_token = self.token_manager.get_valid_token()
        if cached_token:
            self.access_token = cached_token
            return cached_token

        # If not in cache or expired, get a new one
        return self._refresh_token()

    def _refresh_token(self):
        """Fetch a new token from the API."""
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": self.scope,
        }
        response = requests.post(
            f"{self.base_url}/auth/oauth2/connect/token", data=data
        )
        response.raise_for_status()
        token_data = response.json()

        # Store the token and calculate expiry time
        self.access_token = token_data["access_token"]
        # Convert expires_in (seconds) to a datetime
        expires_in = token_data.get("expires_in", 3600)

        # Cache the token
        self.token_manager.cache_token(self.access_token, expires_in)

        return self.access_token

    def _extract_id_from_url(self, url):
        """
        Extract the numeric ID from a URL that belongs to the base domain.

        This method parses a URL and extracts the numeric ID that typically appears
        as the last segment of the path (e.g., '81181' from
        'https://intranet.aarhuskommune.dk/documents/81181').

        Args:
            url (str): The full URL from which to extract the ID.

        Returns:
            str or None: The extracted numeric ID as a string if found and valid,
                        None if the URL doesn't belong to the base domain or
                        doesn't contain a valid numeric ID as the last path segment.
        """
        # Parse the full URL and the base URL
        parsed_url = urllib.parse.urlparse(url)
        parsed_base = urllib.parse.urlparse(self.base_url)

        # Ensure the URL belongs to the base domain
        if parsed_url.netloc != parsed_base.netloc:
            return None

        # Split the path into segments
        path_segments = parsed_url.path.strip("/").split("/")

        # The ID should be the last segment in the path
        if path_segments and path_segments[-1].isdigit():
            return path_segments[-1]

        return None

    def _html_clean_up(self, html_content):
        if html_content is None:
            return None

        # Remove CDATA sections
        html_content = re.sub(
            r"<!\[CDATA\[(.*?)\]\]>", r"\1", html_content, flags=re.DOTALL
        )

        # Remove extra whitespace
        html_content = " ".join(html_content.split())

        # Remove common problematic elements or replace them with better tags
        html_content = html_content.replace("&nbsp;", " ")

        # Fix common HTML issues
        html_content = html_content.replace("<br>", "<br />")

        # Remove any HTML comments
        html_content = re.sub(r"<!--.*?-->", "", html_content, flags=re.DOTALL)

        # Handle special characters and entities
        html_content = html_content.replace("&oslash;", "ø")
        html_content = html_content.replace("&aelig;", "æ")
        html_content = html_content.replace("&aring;", "å")
        html_content = html_content.replace("&Oslash;", "Ø")
        html_content = html_content.replace("&Aelig;", "Æ")
        html_content = html_content.replace("&Aring;", "Å")

        return html_content

    def _html_to_markdown(self, html_content):
        """Convert HTML content to Markdown format."""
        try:
            if html_content is None:
                return None

            # Configure markdownify with options to handle HTML properly
            markdown_content = markdownify(
                html_content,
                strip=["script", "style"],
                heading_style="ATX",
                bullets="-",
                convert_links=True,
            )

            markdown_content = re.sub(r"<br\s*/?>", "\n\n", markdown_content)

            return markdown_content
        except ImportError:
            print("markdownify package is not installed. Run 'pip install markdownify'")
            return None
        except Exception as e:
            print(f"An error occurred while converting HTML to Markdown: {e}")
            return None

    def get_document(self, document_id):
        """Get a single document by ID."""
        headers = {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json",
        }
        response = requests.get(
            f"{self.base_url}/api/documents/{document_id}", headers=headers
        )

        # Check if the response is successful
        response.raise_for_status()

        # Parse the JSON response
        json = response.json()

        if response:
            # Convert date strings to datetime objects
            created = None
            updated = None

            if "created" in json and json["created"]:
                try:
                    created = datetime.fromisoformat(
                        json["created"].replace("Z", "+00:00")
                    ).replace(tzinfo=None)
                except (ValueError, AttributeError):
                    pass

            if "updated" in json and json["updated"]:
                try:
                    updated = datetime.fromisoformat(
                        json["updated"].replace("Z", "+00:00")
                    ).replace(tzinfo=None)
                except (ValueError, AttributeError):
                    pass

            # Split keywords into an array by comma
            keywords = json.get("fields", {}).get("keywords", "")
            keywords_array = (
                [keyword.strip() for keyword in keywords.split(",")] if keywords else []
            )

            body = (
                json.get("fields", {}).get("body", "")
                if json.get("fields", {}).get("body")
                else None
            )
            if body:
                body = self._html_clean_up(body)
                body = self._html_to_markdown(body)

            doctype = json.get("type", {}).get("name").lower()

            # Extract the requested fields
            return {
                "id": json.get("id"),
                "doctype": doctype,
                "childCount": json.get("childCount"),
                "created": created,
                "updated": updated,
                "revisioning": json.get("revisioning"),
                "title": json.get("fields", {}).get("title"),
                "description": json.get("fields", {}).get("description"),
                "body": body,
                "keywords": keywords_array,
            }
        return None

    def get_children(
        self, document_id, max_depth=10, current_depth=0, visited_ids=None
    ):
        """
        Get all children of a document by ID recursively up to a specified maximum depth.

        Args:
            document_id: The ID of the document to get children for
            max_depth: Maximum depth of recursion (default: 10)
            current_depth: Current depth in the recursion (used internally)
            visited_ids: Set of already visited document IDs to prevent circular references (used internally)

        Returns:
            Generator yielding document information with all descendants up to max_depth
        """
        if current_depth >= max_depth:
            return

        # Initialize visited_ids set if not provided
        if visited_ids is None:
            visited_ids = set()

        # Check if we've already visited this document
        if document_id in visited_ids:
            return

        # Mark this document as visited
        visited_ids.add(document_id)

        headers = {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json",
        }
        response = requests.get(
            f"{self.base_url}/api/documents/{document_id}/children", headers=headers
        )

        # Check if the response is successful
        response.raise_for_status()

        # Parse the JSON response
        json = response.json()

        # Extract only id, created, and updated fields from each child
        for item in json:
            # if item['id'] in visited_ids:
            #     # Skip it if it has already been visited
            #     continue

            created = None
            updated = None

            doctype = item.get("type", {}).get("name").lower()
            match doctype:
                case "link":
                    url = item.get("fields", {}).get("url")
                    if url:
                        linked_doc_id = self._extract_id_from_url(url)
                        if linked_doc_id in visited_ids:
                            # Skip it if it has already been visited
                            continue

                        if linked_doc_id:
                            linked_doc = self.get_document(linked_doc_id)
                            yield linked_doc

                            if linked_doc["childCount"]:
                                yield from self.get_children(
                                    linked_doc_id,
                                    max_depth,
                                    current_depth + 1,
                                    visited_ids,
                                )
                        else:
                            # TODO: Extern link
                            # print(f"External document_id: {document_id} ({url})")
                            # yield from self.get_children(document_id, max_depth, current_depth + 1, visited_ids)
                            pass

                    # Stop processing this doc, we do not yield the link page.
                    continue
                case "folder":
                    yield from self.get_children(
                        item.get("id"), max_depth, current_depth + 1, visited_ids
                    )

            if "created" in item and item["created"]:
                try:
                    created = datetime.fromisoformat(
                        item["created"].replace("Z", "+00:00")
                    ).replace(tzinfo=None)
                except (ValueError, AttributeError):
                    pass

            if "updated" in item and item["updated"]:
                try:
                    updated = datetime.fromisoformat(
                        item["updated"].replace("Z", "+00:00")
                    ).replace(tzinfo=None)
                except (ValueError, AttributeError):
                    pass

            # Split keywords into an array by comma
            keywords = item.get("fields", {}).get("keywords", "")
            keywords_array = (
                [keyword.strip() for keyword in keywords.split(",")] if keywords else []
            )

            body = (
                item.get("fields", {}).get("body", "")
                if item.get("fields", {}).get("body")
                else None
            )
            body = self._html_clean_up(body)
            body = self._html_to_markdown(body)

            yield {
                "id": item.get("id"),
                "doctype": doctype,
                "created": created,
                "updated": updated,
                "title": item.get("fields", {}).get("title"),
                "description": item.get("fields", {}).get("description"),
                "body": body,
                "keywords": keywords_array,
            }
