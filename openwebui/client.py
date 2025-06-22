import requests
from poetry.console.commands import self


class Client:
    def __init__(self, token, base_url):
        self.token = token
        self.base_url = base_url
        pass

    def upload_from_string(self, content, filename, content_type, metadata):
        """
        Upload file content from an in-memory string or bytes object.

        Args:
            content (str or bytes): The content to upload
            filename (str): The filename to use for the uploaded content
            content_type (str): The MIME type of the content
            metadata (dict): Metadata for the file

        Returns:
            Response object from the API request
        """

        headers = {
            'Authorization': f'Bearer {self.token}'
        }

        # Convert string to bytes if needed
        if isinstance(content, str):
            content = content.encode('utf-8')

        files = {
            'file': (filename, content, content_type)
        }

        # For multipart/form-data, we need to send metadata as a form field
        form_data = {'metadata': str(metadata).replace("'", '"')}  # Convert Python dict to JSON string

        url = f'{self.base_url}/api/v1/files/?process=true&internal=false'
        response = requests.post(url, headers=headers, data=form_data, files=files)

        return response.json()

    def update_file_content(self, file_id, content):
        """
        Update the content of an existing file using an in-memory string.

        Args:
            file_id (str): The ID of the file to update
            content (str): The new content to replace the file with

        Returns:
            Response object from the API request
        """
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
            'accept': 'application/json'
        }

        data = {
            'content': content
        }

        url = f'{self.base_url}/api/v1/files/{file_id}/data/content/update'
        response = requests.post(url, headers=headers, json=data)
        return response

    def delete_file(self, file_id):
        """
        Delete an existing file by its ID.

        Args:
            file_id (str): The ID of the file to delete

        Returns:
            Response object from the API request
        """
        headers = {
            'Authorization': f'Bearer {self.token}',
            'accept': 'application/json'
        }

        url = f'{self.base_url}/api/v1/files/{file_id}'
        response = requests.delete(url, headers=headers)
        return response

    def add_file_to_knowledge(self, knowledge_id, file_id):
        """
        Add an existing file to a knowledge resource.

        Args:
            knowledge_id (str): The ID of the knowledge resource
            file_id (str): The ID of the file to add

        Returns:
            Response object from the API request
        """
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
            'accept': 'application/json'
        }

        data = {
            'file_id': file_id
        }

        url = f'{self.base_url}/api/v1/knowledge/{knowledge_id}/file/add'
        response = requests.post(url, headers=headers, json=data)
        return response

    def remove_file_from_knowledge(self, knowledge_id, file_id):
        """
        Remove a file from a knowledge resource.

        Args:
            knowledge_id (str): The ID of the knowledge resource
            file_id (str): The ID of the file to remove

        Returns:
            Response object from the API request
        """
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
            'accept': 'application/json'
        }

        data = {
            'file_id': file_id
        }

        url = f'{self.base_url}/api/v1/knowledge/{knowledge_id}/file/remove'
        response = requests.post(url, headers=headers, json=data)
        return response

    def get_knowledge(self, knowledge_id):
        """
        Retrieve information about a specific knowledge resource.

        Args:
            knowledge_id (str): The ID of the knowledge resource to retrieve

        Returns:
            Response object from the API request
        """
        headers = {
            'Authorization': f'Bearer {self.token}',
            'accept': 'application/json'
        }

        url = f'{self.base_url}/api/v1/knowledge/{knowledge_id}'
        response = requests.get(url, headers=headers)

        # Check if the response status code is 200
        if response.status_code != 200:
            raise Exception(f"API request failed with status code {response.status_code}: {response.text}")

        return response.json()
