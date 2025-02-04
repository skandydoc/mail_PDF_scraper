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

    def create_folder(self, folder_name: str, parent_folder_id: str = None) -> str:
        """
        Create a folder in Google Drive
        Args:
            folder_name: Name of the folder to create
            parent_folder_id: Optional ID of parent folder
        Returns:
            str: Folder ID if successful, None otherwise
        """
        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            # Add parent folder if specified
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
            
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

    def list_all_folders(self):
        """List all folders in Google Drive that the user has access to"""
        try:
            results = []
            page_token = None
            
            # First verify if we have valid credentials and permissions
            try:
                # Test API access with a simple request
                about = self.service.about().get(fields="user").execute()
                logger.info(f"Drive API access verified for user: {about.get('user', {}).get('emailAddress', 'unknown')}")
            except Exception as e:
                logger.error(f"Failed to verify Drive API access: {str(e)}")
                raise Exception("Unable to access Google Drive. Please check your permissions and try signing in again.")
            
            while True:
                try:
                    # Query for folders only, including shared folders
                    query = "mimeType='application/vnd.google-apps.folder' and trashed=false"
                    response = self.service.files().list(
                        q=query,
                        spaces='drive',
                        fields='nextPageToken, files(id, name, parents)',
                        pageToken=page_token,
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True,
                        pageSize=100  # Optimize performance with reasonable page size
                    ).execute()
                    
                    current_batch = response.get('files', [])
                    if current_batch:
                        # Filter out folders with no access
                        accessible_folders = []
                        for folder in current_batch:
                            try:
                                # Verify we can actually access the folder
                                self.service.files().get(
                                    fileId=folder['id'],
                                    fields='id, name',
                                    supportsAllDrives=True
                                ).execute()
                                accessible_folders.append(folder)
                            except Exception as e:
                                logger.warning(f"Skipping inaccessible folder {folder.get('name', 'unknown')}: {str(e)}")
                                continue
                        
                        results.extend(accessible_folders)
                    
                    page_token = response.get('nextPageToken')
                    if not page_token:
                        break
                    
                except Exception as e:
                    logger.error(f"Error during folder listing: {str(e)}")
                    # If we have some results, return them with a warning
                    if results:
                        logger.warning("Returning partial folder list due to error")
                        break
                    else:
                        raise Exception("Failed to list folders. Please check your permissions.")
            
            if not results:
                logger.warning("No accessible folders found in Google Drive")
                
            return results
            
        except Exception as e:
            logger.error(f"Error listing all folders: {str(e)}")
            raise Exception(f"Error accessing Google Drive folders: {str(e)}")

    def get_folder_path(self, folder_id):
        """Get the full path of a folder"""
        try:
            path_parts = []
            current_id = folder_id
            visited_ids = set()  # Prevent infinite loops
            
            while current_id:
                if current_id in visited_ids:
                    logger.warning(f"Circular reference detected in folder path for ID: {current_id}")
                    break
                    
                visited_ids.add(current_id)
                
                try:
                    # Get folder details with support for shared drives
                    folder = self.service.files().get(
                        fileId=current_id,
                        fields='id, name, parents',
                        supportsAllDrives=True
                    ).execute()
                    
                    path_parts.insert(0, folder.get('name', 'Unknown'))
                    
                    # Move to parent folder
                    parents = folder.get('parents', [])
                    current_id = parents[0] if parents else None
                    
                    # Avoid excessive depth
                    if len(path_parts) > 100:
                        logger.warning(f"Path depth limit reached for folder ID: {folder_id}")
                        path_parts.insert(0, "...")
                        break
                        
                except Exception as e:
                    logger.error(f"Error getting folder details for {current_id}: {str(e)}")
                    path_parts.insert(0, "Unknown")
                    break
            
            return '/'.join(path_parts[:-1]) or "Root"  # Return "Root" for top-level folders
            
        except Exception as e:
            logger.error(f"Error getting folder path for {folder_id}: {str(e)}")
            return "Unknown Path" 