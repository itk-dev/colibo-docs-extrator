from datetime import datetime

import requests


class Client:
    def __init__(self, client_id, client_secret, scope):
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
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'client_credentials',
            'scope': self.scope
        }
        response = requests.post('https://intranet.aarhuskommune.dk/auth/oauth2/connect/token', data=data)
        self.access_token = response.json()['access_token']

        return True

    # https://intranet.aarhuskommune.dk/api/documents/77318
    def get_document(self, document_id):
        access_token = self.access_token
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        response = requests.get(f'https://intranet.aarhuskommune.dk/api/documents/{document_id}', headers=headers)

        # Check if response is successful
        response.raise_for_status()

        # Parse the JSON response
        json = response.json()

        if response:
            # Convert date strings to datetime objects
            created = None
            updated = None

            if 'created' in response and response['created']:
                try:
                    created = datetime.fromisoformat(json['created'].replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    pass

            if 'updated' in response and response['updated']:
                try:
                    updated = datetime.fromisoformat(json['updated'].replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    pass

            # Convert deleted field to boolean (None -> False, anything else -> True)
            deleted = False if json.get('deleted') is None else True

            # Split keywords into array by comma
            keywords = json.get('fields', {}).get('keywords', '')
            keywords_array = [keyword.strip() for keyword in keywords.split(',')] if keywords else []

            # Extract the requested fields
            return {
                'id': json.get('id'),
                'childCount': json.get('childCount'),
                'created': created,
                'updated': updated,
                'revisioning': json.get('revisioning'),
                'deleted': deleted,
                'description': json.get('fields', {}).get('description'),
                'title': json.get('fields', {}).get('title'),
                'keywords': keywords_array
            }
        return None

    # https://intranet.aarhuskommune.dk/api/documents/5214/children
    def get_children(self, document_id):
        access_token = self.access_token
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        response = requests.get(f'https://intranet.aarhuskommune.dk/api/documents/{document_id}/children', headers=headers)
        return response.json()