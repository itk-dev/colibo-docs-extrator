from datetime import datetime
from markdownify import markdownify

import requests


class Client:
    def __init__(self, base_url, client_id, client_secret, scope):
        self.base_url = base_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self.access_token = None

    @property
    def access_token(self):
        if self._access_token is None:
            self._get_access_token()
        return self._access_token

    @access_token.setter
    def access_token(self, value):
        self._access_token = value

    def _get_access_token(self):
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
            "scope": self.scope,
        }
        response = requests.post(
            f"{self.base_url}/auth/oauth2/connect/token", data=data
        )
        self.access_token = response.json()["access_token"]

        return True

    def _html_clean_up(self, html_content):
        if html_content is None:
            return None

        # Remove CDATA sections
        import re

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

            return markdown_content
        except ImportError:
            print("markdownify package is not installed. Run 'pip install markdownify'")
            return None
        except Exception as e:
            print(f"An error occurred while converting HTML to Markdown: {e}")
            return None

    def get_document(self, document_id):
        """Get a single document by ID."""
        access_token = self.access_token
        headers = {
            "Authorization": f"Bearer {access_token}",
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

            if "created" in response and response["created"]:
                try:
                    created = datetime.fromisoformat(
                        json["created"].replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    pass

            if "updated" in response and response["updated"]:
                try:
                    updated = datetime.fromisoformat(
                        json["updated"].replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    pass

            # Convert deleted field to boolean (None -> False, anything else -> True)
            deleted = False if json.get("deleted") is None else True

            # Split keywords into array by comma
            keywords = json.get("fields", {}).get("keywords", "")
            keywords_array = (
                [keyword.strip() for keyword in keywords.split(",")] if keywords else []
            )

            # Extract the requested fields
            return {
                "id": json.get("id"),
                "childCount": json.get("childCount"),
                "created": created,
                "updated": updated,
                "revisioning": json.get("revisioning"),
                "deleted": deleted,
                "title": json.get("fields", {}).get("title"),
                "description": json.get("fields", {}).get("description"),
                "keywords": keywords_array,
            }
        return None

    def get_children(self, document_id):
        """Get all children of a document by ID."""
        access_token = self.access_token
        headers = {
            "Authorization": f"Bearer {access_token}",
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
            created = None
            updated = None

            if "created" in item and item["created"]:
                try:
                    created = datetime.fromisoformat(
                        item["created"].replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    pass

            if "updated" in item and item["updated"]:
                try:
                    updated = datetime.fromisoformat(
                        item["updated"].replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    pass

            # Split keywords into array by comma
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
                "created": created,
                "updated": updated,
                "title": item.get("fields", {}).get("title"),
                "description": item.get("fields", {}).get("description"),
                "body": body,
                "keywords": keywords_array,
            }
