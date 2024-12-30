from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from typing import Optional
import io
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DriveHandler:
    def __init__(self, credentials: Credentials):
        """
        Initialize Drive handler with credentials
        Args:
            credentials: Google OAuth2 credentials
        """
        self.service = build('drive', 'v3', credentials=credentials)

    def create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> Optional[str]:
        """
        Create a folder in Google Drive
        Args:
            folder_name: Name of the folder to create
            parent_id: Optional parent folder ID
        Returns:
            Folder ID if successful, None otherwise
        """
        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_id:
                file_metadata['parents'] = [parent_id]

            folder = self.service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()

            return folder.get('id')
        except Exception as e:
            logger.error(f"Error creating folder: {str(e)}")
            return None

    def upload_file(self, file_data: bytes, filename: str, folder_id: Optional[str] = None) -> bool:
        """
        Upload a file to Google Drive
        Args:
            file_data: File content in bytes
            filename: Name of the file
            folder_id: Optional folder ID to upload to
        Returns:
            bool: True if upload successful, False otherwise
        """
        try:
            file_metadata = {'name': filename}
            if folder_id:
                file_metadata['parents'] = [folder_id]

            media = MediaIoBaseUpload(
                io.BytesIO(file_data),
                mimetype='application/pdf',
                resumable=True
            )

            self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()

            return True
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            return False

    def check_folder_exists(self, folder_name: str) -> Optional[str]:
        """
        Check if a folder exists in Google Drive
        Args:
            folder_name: Name of the folder to check
        Returns:
            Folder ID if exists, None otherwise
        """
        try:
            query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()

            files = results.get('files', [])
            return files[0]['id'] if files else None
        except Exception as e:
            logger.error(f"Error checking folder: {str(e)}")
            return None 