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
import pytz

# Set up logging
logger = setup_logger()

# Load environment variables
load_dotenv()

# Set page config to wide mode
st.set_page_config(layout="wide")

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
if 'pdf_password' not in st.session_state:
    st.session_state.pdf_password = None

# Get IST timezone
ist = pytz.timezone('Asia/Kolkata')

def format_ist_time(timestamp):
    """Convert timestamp to IST formatted string"""
    dt = datetime.fromtimestamp(int(timestamp)/1000, tz=pytz.UTC)
    ist_time = dt.astimezone(ist)
    return ist_time.strftime('%Y-%m-%d %H:%M IST')

def process_pdf_batch(attachments, folder_id: str, current_keyword: str, password: str = None):
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
                # Process PDF with password if provided
                processed_data, needs_password = st.session_state.pdf_handler.process_pdf(
                    file_data,
                    current_keyword,
                    password
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
                            'timestamp': datetime.now(ist).isoformat()
                        }
                    )
        
        except Exception as e:
            logger.error(f"Error processing attachment {attachment['filename']}: {str(e)}")
            continue
            
    logger.info(f"Batch processing completed. Success: {success_count}, Password Required: {len(password_required)}")
    return success_count, password_required

def display_results_table(all_attachments):
    """Display results in a table with integrated selection"""
    # Create DataFrame for display
    df_data = []
    for att in all_attachments:
        selected = att['id'] in st.session_state.selected_attachments
        df_data.append({
            'Select': selected,
            'Subject': att['subject'],
            'Sender': att['sender'],
            'Date': att['date'],
            'Filename': att['filename'],
            'Size': att['size']
        })
    
    # Display table with selection column
    edited_df = st.data_editor(
        df_data,
        column_config={
            "Select": st.column_config.CheckboxColumn(
                "Select",
                help="Select files to process",
                default=False,
            )
        },
        hide_index=True,
        use_container_width=True,
        key="results_table"
    )
    
    # Update selected attachments based on table selection
    st.session_state.selected_attachments = {
        att['id'] for att, row in zip(all_attachments, edited_df)
        if row['Select']
    }
    
    return edited_df

def initialize_handlers():
    """Initialize Gmail and Drive handlers with authentication"""
    try:
        logger.info("Starting handler initialization")
        gmail_handler = GmailHandler()
        
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
            st.session_state.auth_completed = True
            st.session_state.auth_error = None
            return True
            
        logger.error("Authentication failed in handler initialization")
        st.session_state.auth_completed = False
        st.session_state.auth_error = "Authentication failed. Please try again."
        return False
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error initializing handlers: {error_msg}")
        st.session_state.auth_completed = False
        st.session_state.auth_error = error_msg
        return False

def main():
    logger.info("Application started")
    st.title("Secure Gmail PDF Attachment Scraper")
    st.write("HIPAA-compliant tool for downloading PDF attachments from Gmail")

    # Initialize session states
    if 'auth_completed' not in st.session_state:
        st.session_state.auth_completed = False
    if 'auth_error' not in st.session_state:
        st.session_state.auth_error = None

    # Authentication
    if 'gmail_handler' not in st.session_state or not st.session_state.gmail_handler:
        auth_container = st.container()
        
        with auth_container:
            if not st.session_state.auth_completed:
                st.warning("Please authenticate with Google to continue")
                
                if st.session_state.auth_error:
                    st.error(st.session_state.auth_error)
                    st.session_state.auth_error = None
                
                if st.button("Authenticate", key="auth_button"):
                    with st.spinner("Authenticating with Google..."):
                        if initialize_handlers():
                            st.success("Authentication successful!")
                            time.sleep(0.5)  # Brief pause to show success message
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
        
        # Initialize selected attachments in session state if not present
        if 'selected_attachments' not in st.session_state:
            st.session_state.selected_attachments = set()
        
        # Create a list of all attachments with their email info
        all_attachments = []
        for email in st.session_state.search_results:
            for attachment in email['attachments']:
                all_attachments.append({
                    'subject': email['subject'],
                    'sender': email['sender'],
                    'date': format_ist_time(email['date']),
                    'filename': attachment['filename'],
                    'size': f"{attachment['size']/1024:.1f} KB",
                    'id': f"{email['id']}_{attachment['id']}",
                    'message_id': email['id'],
                    'attachment_id': attachment['id']
                })
        
        # Select all / Deselect all buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Select All"):
                st.session_state.selected_attachments = {att['id'] for att in all_attachments}
                st.rerun()
        with col2:
            if st.button("Deselect All"):
                st.session_state.selected_attachments = set()
                st.rerun()
        
        # Display results table with integrated selection
        edited_df = display_results_table(all_attachments)
        
        # Get selected attachments details
        selected_attachments = [
            {
                'message_id': att['message_id'],
                'attachment_id': att['attachment_id'],
                'filename': att['filename']
            }
            for att in all_attachments
            if att['id'] in st.session_state.selected_attachments
        ]

        if selected_attachments:
            st.subheader("Upload to Google Drive")
            
            # Password input for PDF files
            st.session_state.pdf_password = st.text_input(
                "PDF Password (if required)",
                value=st.session_state.pdf_password or "",
                help="Enter the password for password-protected PDFs. Leave empty if files are not password-protected."
            )
            
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

                        # Process files with password if provided
                        success_count = 0
                        password_required_files = []
                        
                        for keyword in keywords:
                            batch_success, batch_password_required = process_pdf_batch(
                                selected_attachments,
                                folder_id,
                                keyword,
                                st.session_state.pdf_password
                            )
                            success_count += batch_success
                            password_required_files.extend(batch_password_required)
                        
                        # Show results
                        if success_count > 0:
                            st.success(f"Successfully processed {success_count} files")
                        
                        if password_required_files:
                            st.warning(
                                f"{len(password_required_files)} files require a password or the provided password was incorrect. "
                                "Please enter the correct password above and try again."
                            )
                        elif success_count == 0:
                            st.error("Failed to process any files")

                    except Exception as e:
                        logger.error(f"Error in batch processing: {str(e)}")
                        st.error("An error occurred during processing")

if __name__ == "__main__":
    main() 