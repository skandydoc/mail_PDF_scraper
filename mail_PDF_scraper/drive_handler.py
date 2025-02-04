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