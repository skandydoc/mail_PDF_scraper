def list_all_folders(self):
    """List all folders in Google Drive that the user has access to"""
    try:
        results = []
        page_token = None
        
        while True:
            # Query for folders only
            query = "mimeType='application/vnd.google-apps.folder' and trashed=false"
            response = self.service.files().list(
                q=query,
                spaces='drive',
                fields='nextPageToken, files(id, name, parents)',
                pageToken=page_token
            ).execute()
            
            results.extend(response.get('files', []))
            page_token = response.get('nextPageToken')
            
            if not page_token:
                break
        
        return results
    except Exception as e:
        logger.error(f"Error listing all folders: {str(e)}")
        return []

def get_folder_path(self, folder_id):
    """Get the full path of a folder"""
    try:
        path_parts = []
        current_id = folder_id
        
        while current_id:
            # Get folder details
            folder = self.service.files().get(
                fileId=current_id,
                fields='id, name, parents'
            ).execute()
            
            path_parts.insert(0, folder.get('name', ''))
            
            # Move to parent folder
            parents = folder.get('parents', [])
            current_id = parents[0] if parents else None
            
            # Avoid infinite loops (shouldn't happen, but just in case)
            if len(path_parts) > 100:
                break
        
        return '/'.join(path_parts[:-1])  # Exclude the current folder name
    except Exception as e:
        logger.error(f"Error getting folder path for {folder_id}: {str(e)}")
        return "Unknown Path" 