import streamlit as st
import os
from utils.gmail_handler import GmailHandler
from utils.drive_handler import DriveHandler
from utils.pdf_handler import PdfHandler
from utils.hipaa_compliance import HipaaCompliance
from utils.logger_config import setup_logger
from dotenv import load_dotenv
import logging
from datetime import datetime
import time

# Set up logging
logger = setup_logger()

# Load environment variables
load_dotenv()

# Initialize session state
if 'authentication_state' not in st.session_state:
    st.session_state.authentication_state = 'not_started'
    logger.info("Initialized authentication state")
if 'gmail_handler' not in st.session_state:
    st.session_state.gmail_handler = None
if 'drive_handler' not in st.session_state:
    st.session_state.drive_handler = None
if 'pdf_handler' not in st.session_state:
    st.session_state.pdf_handler = PdfHandler()
if 'hipaa' not in st.session_state:
    st.session_state.hipaa = HipaaCompliance()
if 'user_session' not in st.session_state:
    st.session_state.user_session = None

def initialize_handlers():
    """Initialize Gmail and Drive handlers with authentication"""
    try:
        logger.info("Starting handler initialization")
        gmail_handler = GmailHandler()
        st.session_state.authentication_state = 'in_progress'
        
        auth_success = gmail_handler.authenticate()
        
        if auth_success:
            st.session_state.gmail_handler = gmail_handler
            st.session_state.drive_handler = DriveHandler(gmail_handler.creds)
            
            # Create HIPAA-compliant session
            user_info = gmail_handler.service.users().getProfile(userId='me').execute()
            st.session_state.user_session = st.session_state.hipaa.create_session(user_info['emailAddress'])
            
            # Log successful authentication
            st.session_state.hipaa.log_activity(
                user_info['emailAddress'],
                'authentication',
                {'status': 'success', 'timestamp': datetime.utcnow().isoformat()}
            )
            
            logger.info(f"Authentication successful for user: {user_info['emailAddress']}")
            st.session_state.authentication_state = 'completed'
            return True
            
        logger.error("Authentication failed in handler initialization")
        st.session_state.authentication_state = 'failed'
        return False
    except Exception as e:
        logger.error(f"Error initializing handlers: {str(e)}")
        st.session_state.authentication_state = 'failed'
        return False

def process_pdf_batch(attachments, folder_id: str, current_keyword: str):
    """Process a batch of PDF attachments"""
    success_count = 0
    password_required = []
    
    logger.info(f"Starting batch processing for keyword: {current_keyword}")
    
    for attachment in attachments:
        try:
            logger.info(f"Processing attachment: {attachment['filename']}")
            # Download
            file_data = st.session_state.gmail_handler.download_attachment(
                attachment['message_id'],
                attachment['attachment_id']
            )
            
            if file_data:
                # Process PDF and check for password protection
                processed_data, needs_password = st.session_state.pdf_handler.process_pdf(
                    file_data,
                    current_keyword
                )
                
                if needs_password:
                    logger.info(f"Password required for: {attachment['filename']}")
                    password_required.append(attachment)
                    continue
                
                # Verify data integrity
                file_hash = st.session_state.hipaa.verify_data_integrity(processed_data)
                
                # Upload to Drive
                if st.session_state.drive_handler.upload_file(
                    processed_data,
                    attachment['filename'],
                    folder_id
                ):
                    success_count += 1
                    logger.info(f"Successfully processed and uploaded: {attachment['filename']}")
                    
                    # Log successful upload
                    st.session_state.hipaa.log_activity(
                        st.session_state.gmail_handler.service.users().getProfile(userId='me').execute()['emailAddress'],
                        'file_upload',
                        {
                            'filename': attachment['filename'],
                            'hash': file_hash,
                            'timestamp': datetime.utcnow().isoformat()
                        }
                    )
        
        except Exception as e:
            logger.error(f"Error processing attachment {attachment['filename']}: {str(e)}")
            continue
            
    logger.info(f"Batch processing completed. Success: {success_count}, Password Required: {len(password_required)}")
    return success_count, password_required

def main():
    logger.info("Application started")
    st.title("Secure Gmail PDF Attachment Scraper")
    st.write("HIPAA-compliant tool for downloading PDF attachments from Gmail")

    # Authentication
    if not st.session_state.gmail_handler or not st.session_state.user_session:
        if st.session_state.authentication_state == 'not_started':
            st.warning("Please authenticate with Google to continue")
            if st.button("Authenticate"):
                initialize_handlers()
                st.rerun()
        
        elif st.session_state.authentication_state == 'in_progress':
            st.info("Authentication in progress... Please complete the authentication in your browser.")
            with st.spinner("Waiting for authentication to complete..."):
                time.sleep(0.5)  # Short delay to prevent too frequent reruns
                st.rerun()
        
        elif st.session_state.authentication_state == 'failed':
            st.error("Authentication failed. Please try again.")
            if st.button("Retry Authentication"):
                st.session_state.authentication_state = 'not_started'
                st.rerun()
        
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

    # Clear password cache when keywords change
    if 'last_keywords' not in st.session_state or st.session_state.last_keywords != keywords:
        st.session_state.pdf_handler.clear_password_cache()
        st.session_state.last_keywords = keywords

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

            if folder_name and st.button("Process Selected Files"):
                with st.spinner("Processing files..."):
                    try:
                        # Check/Create folder
                        folder_id = st.session_state.drive_handler.check_folder_exists(folder_name)
                        if not folder_id:
                            folder_id = st.session_state.drive_handler.create_folder(folder_name)
                            if not folder_id:
                                st.error("Failed to create folder in Google Drive")
                                return

                        # Process files
                        success_count = 0
                        password_required_files = []
                        
                        for keyword in keywords:
                            keyword_attachments = selected_attachments
                            batch_success, batch_password_required = process_pdf_batch(
                                keyword_attachments,
                                folder_id,
                                keyword
                            )
                            success_count += batch_success
                            password_required_files.extend(batch_password_required)
                        
                        # Handle password-protected files
                        if password_required_files:
                            st.warning("Some files require a password")
                            password = st.text_input("Enter PDF password", type="password")
                            
                            if password and st.button("Process Password-Protected Files"):
                                with st.spinner("Processing password-protected files..."):
                                    batch_success, still_password_required = process_pdf_batch(
                                        password_required_files,
                                        folder_id,
                                        keywords[0],  # Use first keyword for password caching
                                        password
                                    )
                                    success_count += batch_success
                                    
                                    if still_password_required:
                                        st.error("Incorrect password for some files")
                        
                        if success_count > 0:
                            st.success(f"Successfully processed {success_count} files")
                        else:
                            st.error("Failed to process any files")

                    except Exception as e:
                        logger.error(f"Error in batch processing: {str(e)}")
                        st.error("An error occurred during processing")

if __name__ == "__main__":
    main() 