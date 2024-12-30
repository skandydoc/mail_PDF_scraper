import streamlit as st
import os
from utils.gmail_handler import GmailHandler
from utils.drive_handler import DriveHandler
from utils.encryption import Encryptor
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize session state
if 'gmail_handler' not in st.session_state:
    st.session_state.gmail_handler = None
if 'drive_handler' not in st.session_state:
    st.session_state.drive_handler = None
if 'encryptor' not in st.session_state:
    encryption_key = os.getenv('ENCRYPTION_KEY')
    st.session_state.encryptor = Encryptor(encryption_key)

def initialize_handlers():
    """Initialize Gmail and Drive handlers with authentication"""
    try:
        gmail_handler = GmailHandler()
        if gmail_handler.authenticate():
            st.session_state.gmail_handler = gmail_handler
            st.session_state.drive_handler = DriveHandler(gmail_handler.creds)
            return True
        return False
    except Exception as e:
        logger.error(f"Error initializing handlers: {str(e)}")
        return False

def main():
    st.title("Secure Gmail PDF Attachment Scraper")
    st.write("HIPAA-compliant tool for downloading PDF attachments from Gmail")

    # Authentication
    if not st.session_state.gmail_handler:
        st.warning("Please authenticate with Google to continue")
        if st.button("Authenticate"):
            with st.spinner("Authenticating..."):
                if initialize_handlers():
                    st.success("Authentication successful!")
                    st.rerun()
                else:
                    st.error("Authentication failed. Please try again.")
        return

    # Search Parameters
    st.subheader("Search Parameters")
    keywords = st.text_area(
        "Enter search keywords (one per line)",
        help="Enter keywords to search for in emails. The search will find emails containing any of these keywords."
    ).split('\n')
    keywords = [k.strip() for k in keywords if k.strip()]

    if not keywords:
        st.warning("Please enter at least one keyword")
        return

    # Search Emails
    if st.button("Search Emails"):
        with st.spinner("Searching emails..."):
            emails = st.session_state.gmail_handler.search_emails(keywords)
            if not emails:
                st.warning("No emails found with PDF attachments matching the keywords")
                return
            
            st.session_state.search_results = emails
            st.success(f"Found {len(emails)} emails with PDF attachments")

    # Display Results and Select Attachments
    if 'search_results' in st.session_state:
        st.subheader("Search Results")
        
        selected_attachments = []
        for email in st.session_state.search_results:
            with st.expander(f"Email: {email['subject']}"):
                st.write(f"From: {email['sender']}")
                st.write(f"Date: {email['date']}")
                
                for attachment in email['attachments']:
                    if st.checkbox(
                        f"Select: {attachment['filename']} ({attachment['size']} bytes)",
                        key=f"{email['id']}_{attachment['id']}"
                    ):
                        selected_attachments.append({
                            'message_id': email['id'],
                            'attachment_id': attachment['id'],
                            'filename': attachment['filename']
                        })

        if selected_attachments:
            st.subheader("Upload to Google Drive")
            folder_name = st.text_input(
                "Enter Google Drive folder name",
                help="Enter the name of the folder where files will be uploaded. A new folder will be created if it doesn't exist."
            )

            if folder_name and st.button("Download and Upload Selected Files"):
                with st.spinner("Processing files..."):
                    try:
                        # Check/Create folder
                        folder_id = st.session_state.drive_handler.check_folder_exists(folder_name)
                        if not folder_id:
                            folder_id = st.session_state.drive_handler.create_folder(folder_name)
                            if not folder_id:
                                st.error("Failed to create folder in Google Drive")
                                return

                        # Process each selected attachment
                        success_count = 0
                        for attachment in selected_attachments:
                            try:
                                # Download
                                file_data = st.session_state.gmail_handler.download_attachment(
                                    attachment['message_id'],
                                    attachment['attachment_id']
                                )
                                
                                if file_data:
                                    # Encrypt
                                    encrypted_data, iv = st.session_state.encryptor.encrypt_file(file_data)
                                    
                                    # Upload encrypted file
                                    if st.session_state.drive_handler.upload_file(
                                        encrypted_data,
                                        f"encrypted_{attachment['filename']}",
                                        folder_id
                                    ):
                                        success_count += 1
                                    
                                    # Upload IV (needed for decryption)
                                    st.session_state.drive_handler.upload_file(
                                        iv,
                                        f"iv_{attachment['filename']}.bin",
                                        folder_id
                                    )
                            
                            except Exception as e:
                                logger.error(f"Error processing attachment {attachment['filename']}: {str(e)}")
                                continue

                        if success_count > 0:
                            st.success(f"Successfully processed {success_count} files")
                        else:
                            st.error("Failed to process any files")

                    except Exception as e:
                        logger.error(f"Error in batch processing: {str(e)}")
                        st.error("An error occurred during processing")

if __name__ == "__main__":
    main() 