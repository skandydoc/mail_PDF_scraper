import streamlit as st
import os
from utils.gmail_handler import GmailHandler
from utils.drive_handler import DriveHandler
from utils.pdf_handler import PdfHandler
from utils.security import SecurityHandler
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
if 'security' not in st.session_state:
    st.session_state.security = SecurityHandler()
if 'user_session' not in st.session_state:
    st.session_state.user_session = None

# Get IST timezone
ist = pytz.timezone('Asia/Kolkata')

def format_ist_time(timestamp):
    """Convert timestamp to IST formatted string"""
    dt = datetime.fromtimestamp(int(timestamp)/1000, tz=pytz.UTC)
    ist_time = dt.astimezone(ist)
    return ist_time.strftime('%Y-%m-%d %H:%M IST')

def format_file_date(timestamp):
    """Format date for file naming"""
    dt = datetime.fromtimestamp(int(timestamp)/1000, tz=pytz.UTC)
    ist_time = dt.astimezone(ist)
    return ist_time.strftime('%d %B %Y')

def get_file_name(original_name: str, email_date: str) -> str:
    """Generate file name based on email date"""
    extension = original_name.split('.')[-1] if '.' in original_name else 'pdf'
    return f"{email_date}.{extension}"

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
                
                # Generate new filename based on email date
                new_filename = get_file_name(attachment['filename'], attachment['email_date'])
                
                # Upload to Drive with new filename
                if st.session_state.drive_handler.upload_file(
                    processed_data,
                    new_filename,
                    folder_id
                ):
                    success_count += 1
                    logger.info(f"Successfully processed and uploaded: {new_filename}")
                    
                    # Log successful upload
                    st.session_state.security.log_activity(
                        st.session_state.gmail_handler.service.users().getProfile(userId='me').execute()['emailAddress'],
                        'file_upload',
                        {
                            'filename': new_filename,
                            'original_name': attachment['filename'],
                            'timestamp': datetime.now(ist).isoformat()
                        }
                    )
        
        except Exception as e:
            logger.error(f"Error processing attachment {attachment['filename']}: {str(e)}")
            continue
            
    logger.info(f"Batch processing completed. Success: {success_count}, Password Required: {len(password_required)}")
    return success_count, password_required

def process_keyword_batch(keyword: str, attachments, parent_folder_id: str, password: str = None):
    """Process a batch of attachments for a specific keyword"""
    try:
        # Create subfolder for keyword
        keyword_folder_name = f"{keyword.strip()}_files"
        keyword_folder_id = st.session_state.drive_handler.create_folder(
            keyword_folder_name, 
            parent_folder_id
        )
        
        if not keyword_folder_id:
            st.error(f"Failed to create folder for keyword: {keyword}")
            return 0, []
            
        # Process files
        success_count, password_required = process_pdf_batch(
            attachments,
            keyword_folder_id,
            keyword,
            password
        )
        
        return success_count, password_required
        
    except Exception as e:
        logger.error(f"Error processing keyword batch {keyword}: {str(e)}")
        return 0, []

def initialize_handlers():
    """Initialize Gmail and Drive handlers with authentication"""
    try:
        logger.info("Starting handler initialization")
        gmail_handler = GmailHandler()
        
        auth_success = gmail_handler.authenticate()
        
        if auth_success:
            st.session_state.gmail_handler = gmail_handler
            st.session_state.drive_handler = DriveHandler(gmail_handler.creds)
            
            # Create secure session
            user_info = gmail_handler.service.users().getProfile(userId='me').execute()
            st.session_state.user_session = st.session_state.security.create_session(user_info['emailAddress'])
            
            # Log successful authentication
            st.session_state.security.log_activity(
                user_info['emailAddress'],
                'authentication',
                {'status': 'success', 'timestamp': datetime.now(ist).isoformat()}
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

def sign_out():
    """Sign out the current user and clear session state"""
    try:
        if 'gmail_handler' in st.session_state and st.session_state.gmail_handler:
            # Log sign out activity
            user_info = st.session_state.gmail_handler.service.users().getProfile(userId='me').execute()
            st.session_state.security.log_activity(
                user_info['emailAddress'],
                'sign_out',
                {'timestamp': datetime.now(ist).isoformat()}
            )
        
        # Remove token file
        if os.path.exists('token.pickle'):
            os.remove('token.pickle')
        
        # Clear session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        logger.info("User signed out successfully")
        return True
    except Exception as e:
        logger.error(f"Error during sign out: {str(e)}")
        return False

def main():
    logger.info("Application started")
    
    # Create title row with sign out button
    col1, col2 = st.columns([6, 1])
    with col1:
        st.title("Secure Gmail PDF Attachment Processor")
    with col2:
        if 'gmail_handler' in st.session_state and st.session_state.gmail_handler:
            if st.button("Sign Out", type="secondary"):
                with st.spinner("Signing out..."):
                    if sign_out():
                        st.success("Signed out successfully!")
                        time.sleep(1)  # Brief pause to show success message
                        st.rerun()
                    else:
                        st.error("Error signing out. Please try again.")
    
    st.write("Tool for downloading and organizing PDF attachments from Gmail")

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
                
                if st.button("Sign In with Google", key="auth_button"):
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
                    'attachment_id': attachment['id'],
                    'email_date': format_file_date(email['date'])
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
                'filename': att['filename'],
                'email_date': att['email_date']
            }
            for att in all_attachments
            if att['id'] in st.session_state.selected_attachments
        ]

        if selected_attachments:
            st.subheader("Upload to Google Drive")
            
            # Main folder input
            main_folder = st.text_input(
                "Enter main Google Drive folder name",
                help="Enter the name of the main folder where all keyword-specific folders will be created"
            )
            
            if main_folder:
                # Create expandable sections for each keyword
                keyword_configs = {}
                
                for keyword in keywords:
                    with st.expander(f"Settings for keyword: {keyword}", expanded=True):
                        keyword_configs[keyword] = {
                            'password': st.text_input(
                                "PDF Password (if required)",
                                value="",
                                help="Enter the password for password-protected PDFs matching this keyword",
                                key=f"pwd_{keyword}"
                            )
                        }
                
                if st.button("Process Selected Files"):
                    with st.spinner("Processing files..."):
                        try:
                            # Create/check main folder
                            main_folder_id = st.session_state.drive_handler.check_folder_exists(main_folder)
                            if not main_folder_id:
                                main_folder_id = st.session_state.drive_handler.create_folder(main_folder)
                                if not main_folder_id:
                                    st.error("Failed to create main folder in Google Drive")
                                    return
                            
                            # Process each keyword with all selected files
                            total_success = 0
                            all_password_required = []
                            
                            for keyword in keywords:
                                success_count, password_required = process_keyword_batch(
                                    keyword,
                                    selected_attachments,  # Pass all attachments for each keyword
                                    main_folder_id,
                                    keyword_configs[keyword]['password']
                                )
                                
                                # Update tracking
                                total_success += success_count
                                all_password_required.extend(password_required)
                            
                            # Show results
                            if total_success > 0:
                                st.success(f"Successfully processed {total_success} files")
                            
                            if all_password_required:
                                # Group password-required files by keyword
                                password_files_by_keyword = {}
                                for file in all_password_required:
                                    keyword = next(k for k in keywords if k in file['filename'])
                                    if keyword not in password_files_by_keyword:
                                        password_files_by_keyword[keyword] = []
                                    password_files_by_keyword[keyword].append(file['filename'])
                                
                                # Show password requirements by keyword
                                for keyword, files in password_files_by_keyword.items():
                                    st.warning(
                                        f"For keyword '{keyword}': {len(files)} files require a password or the provided "
                                        f"password was incorrect. Please check the password in the keyword settings above."
                                    )
                            
                            elif total_success == 0:
                                st.error("Failed to process any files")

                        except Exception as e:
                            logger.error(f"Error in batch processing: {str(e)}")
                            st.error("An error occurred during processing")

if __name__ == "__main__":
    main() 