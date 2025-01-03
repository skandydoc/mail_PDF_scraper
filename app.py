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
from typing import Optional

# Set up logging
logger = setup_logger()

# Load environment variables
load_dotenv()

# Set page config to wide mode with menu
st.set_page_config(
    layout="wide",
    page_title="Gmail PDF Processor",
    page_icon="📧",
    menu_items={
        'Get Help': 'https://github.com/yourusername/mail_PDF_scraper',
        'Report a bug': "https://github.com/yourusername/mail_PDF_scraper/issues",
        'About': """
        # Gmail PDF Attachment Processor
        
        A secure tool for downloading and organizing PDF attachments from Gmail.
        Version: 1.0.0
        
        For support or feature requests, please visit our GitHub repository.
        """
    }
)

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

def process_pdf_batch(attachments, folder_id: str, current_keyword: str, passwords: list = None, processed_files: set = None):
    """Process a batch of PDF attachments"""
    success_count = 0
    password_required = []
    processed_filenames = []
    error_files = []
    
    if processed_files is None:
        processed_files = set()
    
    if passwords is None:
        passwords = []
    
    logger.info(f"Starting batch processing for keyword: {current_keyword}")
    
    # Process each attachment
    for attachment in attachments:
        # Generate a unique identifier for the file
        file_id = f"{attachment['message_id']}_{attachment['attachment_id']}"
        
        # Skip if already processed
        if file_id in processed_files:
            logger.info(f"Skipping already processed file: {attachment['filename']}")
            continue
            
        try:
            logger.info(f"Processing attachment: {attachment['filename']}")
            # Download
            file_data = st.session_state.gmail_handler.download_attachment(
                attachment['message_id'],
                attachment['attachment_id']
            )
            
            if file_data:
                # Process PDF with passwords if provided
                processed_data, needs_password, error_msg = st.session_state.pdf_handler.process_pdf(
                    file_data,
                    current_keyword,  # Use keyword as group key for password caching
                    passwords,
                    attachment.get('email_body', '')  # Pass email body for format detection
                )
                
                if needs_password:
                    logger.info(f"Password required for: {attachment['filename']} - {error_msg}")
                    password_required.append({
                        'filename': attachment['filename'],
                        'error': error_msg,
                        'attachment': attachment,
                        'password_hint': attachment.get('password_hint', '')
                    })
                    continue
                
                if not processed_data:
                    logger.error(f"Failed to process {attachment['filename']}: {error_msg}")
                    error_files.append({
                        'filename': attachment['filename'],
                        'error': error_msg,
                        'password_hint': attachment.get('password_hint', '')
                    })
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
                    processed_files.add(file_id)  # Mark as processed
                    processed_filenames.append(new_filename)  # Track processed filename
                    logger.info(f"Successfully processed and uploaded: {new_filename}")
                    
                    # Log successful upload
                    st.session_state.security.log_activity(
                        st.session_state.gmail_handler.service.users().getProfile(userId='me').execute()['emailAddress'],
                        'file_upload',
                        {
                            'filename': new_filename,
                            'original_name': attachment['filename'],
                            'keyword': current_keyword,
                            'folder_id': folder_id,
                            'timestamp': datetime.now(ist).isoformat()
                        }
                    )
        
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error processing attachment {attachment['filename']}: {error_msg}")
            error_files.append({
                'filename': attachment['filename'],
                'error': error_msg,
                'password_hint': attachment.get('password_hint', '')
            })
            continue
            
    logger.info(f"Batch processing completed. Success: {success_count}, Password Required: {len(password_required)}")
    return success_count, password_required, processed_files, processed_filenames, error_files

def process_keyword_batch(keyword: str, attachments, parent_folder_id: str, password: str = None, processed_files: set = None):
    """Process a batch of attachments for a specific keyword"""
    try:
        if not attachments:
            return 0, [], processed_files, [], ""
            
        # Create subfolder for keyword
        keyword_folder_name = f"{keyword.strip()}_files"
        keyword_folder_id = st.session_state.drive_handler.create_folder(
            keyword_folder_name, 
            parent_folder_id
        )
        
        if not keyword_folder_id:
            st.error(f"Failed to create folder for keyword: {keyword}")
            return 0, [], processed_files, [], ""
            
        # Process files
        success_count, password_required, updated_processed_files, processed_filenames = process_pdf_batch(
            attachments,
            keyword_folder_id,
            keyword,
            password,
            processed_files
        )
        
        return success_count, password_required, updated_processed_files, processed_filenames, keyword_folder_name
        
    except Exception as e:
        logger.error(f"Error processing keyword batch {keyword}: {str(e)}")
        return 0, [], processed_files, [], ""

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

def display_results_table(all_attachments, table_name: str = "", selected_attachments_key: str = ""):
    """Display results in a table with integrated selection"""
    if not all_attachments:
        return []
        
    # Create DataFrame for display
    df_data = []
    for att in all_attachments:
        selected = att['id'] in st.session_state[selected_attachments_key] if selected_attachments_key else False
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
            ),
            "Subject": st.column_config.TextColumn("Subject", width="large"),
            "Sender": st.column_config.TextColumn("Sender", width="medium"),
            "Date": st.column_config.TextColumn("Date", width="medium"),
            "Filename": st.column_config.TextColumn("Filename", width="large"),
            "Size": st.column_config.TextColumn("Size", width="small")
        },
        disabled=False,
        hide_index=True,
        key=f"{table_name}_results_table",
        use_container_width=True,
        on_change=None  # Prevent auto-scroll
    )
    
    # Update selected attachments based on table selection
    st.session_state[selected_attachments_key] = {
        att['id'] for att, row in zip(all_attachments, edited_df)
        if row['Select']
    }
    
    return edited_df

def get_pattern_from_subject(subject: str, sender_email: str) -> str:
    """Extract pattern from email subject safely"""
    try:
        if not subject or not subject.strip():
            return f"No Subject - {sender_email}"
        words = subject.strip().split()
        if not words:
            return f"No Subject - {sender_email}"
        return f"{words[0]} - {sender_email}"
    except Exception as e:
        logger.error(f"Error extracting pattern from subject: {str(e)}")
        return f"No Subject - {sender_email}"

def display_content_matches(content_matches, selected_content_attachments_key: str = "selected_content_attachments"):
    """Display content matches grouped by subject pattern and sender"""
    if not content_matches:
        return
        
    # Group content matches by subject pattern and sender
    subject_patterns = {}
    for email in content_matches:
        pattern = get_pattern_from_subject(email.get('subject', ''), email.get('sender_email', 'unknown'))
        if pattern not in subject_patterns:
            subject_patterns[pattern] = []
        subject_patterns[pattern].append(email)
    
    # Display each group in a separate table
    for pattern, emails in subject_patterns.items():
        st.subheader(f"Content Matches - {pattern}")
        
        # Initialize selected attachments for this group
        group_key = f"{selected_content_attachments_key}_{pattern}"
        if group_key not in st.session_state:
            st.session_state[group_key] = set()
        
        # Create list of attachments for this group
        group_attachments = []
        for email in emails:
            for attachment in email['attachments']:
                group_attachments.append({
                    'subject': email.get('subject', 'No Subject'),
                    'sender': email.get('sender', 'Unknown'),
                    'sender_email': email.get('sender_email', 'Unknown'),
                    'date': format_ist_time(email['date']),
                    'filename': attachment['filename'],
                    'size': f"{attachment['size']/1024:.1f} KB",
                    'id': f"{email['id']}_{attachment['id']}",
                    'message_id': email['id'],
                    'attachment_id': attachment['id'],
                    'email_date': format_file_date(email['date']),
                    'password_hint': email.get('password_hint', '')
                })
        
        # Select all / Deselect all buttons for this group
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"Select All - {pattern}"):
                st.session_state[group_key] = {att['id'] for att in group_attachments}
                st.rerun()
        with col2:
            if st.button(f"Deselect All - {pattern}"):
                st.session_state[group_key] = set()
                st.rerun()
        
        # Display group table
        edited_df = display_results_table(group_attachments, f"content_matches_{pattern}", group_key)
        
        # Add selected attachments from this group to the main selection
        st.session_state[selected_content_attachments_key].update(st.session_state[group_key])

def show_processing_results(results_by_keyword):
    """Display processing results for each keyword and folder"""
    for keyword, result in results_by_keyword.items():
        with st.expander(f"Results for '{keyword}'", expanded=True):
            if result['success_count'] > 0:
                st.success(
                    f"Successfully processed {result['success_count']} files into folder '{result['folder_name']}'"
                )
            
            # Show password required files
            if result['password_required']:
                st.warning(
                    f"{len(result['password_required'])} files require a password or the provided "
                    f"passwords were incorrect."
                )
                st.write("Files requiring password:")
                for file_info in result['password_required']:
                    hint_text = f" (Password hint: {file_info['password_hint']})" if file_info.get('password_hint') else ""
                    st.write(f"- {file_info['filename']}: {file_info['error']}{hint_text}")
                
                # Add password input for retry
                new_password = st.text_input(
                    f"Enter password for {keyword} files",
                    type="password",
                    key=f"new_password_{keyword}"
                )
                if new_password and st.button(f"Retry with new password - {keyword}"):
                    with st.spinner("Retrying with new password..."):
                        # Get the attachments that need password
                        retry_attachments = [file_info['attachment'] for file_info in result['password_required']]
                        # Retry processing with new password
                        success_count, still_need_password, processed_files, processed_filenames, errors = process_pdf_batch(
                            retry_attachments,
                            result['folder_id'],
                            keyword,
                            passwords=[new_password],
                            processed_files=result['processed_files']
                        )
                        if success_count > 0:
                            st.success(f"Successfully processed {success_count} additional files")
                            # Update the results
                            result['success_count'] += success_count
                            result['password_required'] = still_need_password
                            result['processed_files'].update(processed_files)
                            result['processed_filenames'].extend(processed_filenames)
                            st.rerun()
            
            # Show error files
            if result.get('error_files'):
                st.error("Some files encountered errors during processing:")
                for error_file in result['error_files']:
                    hint_text = f" (Password hint: {error_file['password_hint']})" if error_file.get('password_hint') else ""
                    st.write(f"- {error_file['filename']}: {error_file['error']}{hint_text}")
            
            # Show successfully processed files
            if result['processed_files']:
                st.write("Successfully processed files:")
                for file in result['processed_filenames']:
                    st.write(f"- {file}")
                    
            if result['success_count'] == 0 and not result['password_required'] and not result.get('error_files'):
                st.error(f"No files were processed for keyword '{keyword}'")

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

def get_group_password(attachments: list, passwords: list) -> Optional[str]:
    """
    Find working password for a group by testing the first file
    Args:
        attachments: List of attachments in the group
        passwords: List of passwords to try
    Returns:
        str: Working password if found, None otherwise
    """
    if not attachments or not passwords:
        return None
        
    # Get the first attachment
    first_attachment = attachments[0]
    file_data = st.session_state.gmail_handler.download_attachment(
        first_attachment['message_id'],
        first_attachment['attachment_id']
    )
    
    if file_data:
        return st.session_state.pdf_handler.find_working_password(file_data, passwords)
    return None

def show_selection_summary():
    """Display summary of selected files"""
    st.subheader("Selection Summary")
    
    total_selected = 0
    summary_data = []
    
    # Count exact matches
    for keyword in st.session_state.exact_matches_by_keyword:
        keyword_key = f"selected_attachments_{keyword}"
        if keyword_key in st.session_state:
            count = len(st.session_state[keyword_key])
            if count > 0:
                summary_data.append({
                    "Group": f"Exact Matches - {keyword}",
                    "Selected Files": count
                })
                total_selected += count
    
    # Count content matches
    for sender in st.session_state.content_matches_by_sender:
        sender_key = f"selected_content_{sender}"
        if sender_key in st.session_state:
            count = len(st.session_state[sender_key])
            if count > 0:
                summary_data.append({
                    "Group": f"Content Matches - {sender}",
                    "Selected Files": count
                })
                total_selected += count
    
    # Display summary table
    if summary_data:
        st.table(summary_data)
        st.info(f"Total files selected: {total_selected}")
    else:
        st.warning("No files selected")

def show_final_status(results_by_group):
    """Display final processing status"""
    st.subheader("Processing Summary")
    
    status_data = []
    total_success = 0
    total_password_required = 0
    total_errors = 0
    
    for group_name, result in results_by_group.items():
        status_data.append({
            "Group": group_name,
            "Successfully Processed": result['success_count'],
            "Password Required": len(result['password_required']),
            "Errors": len(result.get('error_files', []))
        })
        total_success += result['success_count']
        total_password_required += len(result['password_required'])
        total_errors += len(result.get('error_files', []))
    
    if status_data:
        st.table(status_data)
        st.info(f"""
        Total Summary:
        - Successfully Processed: {total_success}
        - Password Required: {total_password_required}
        - Errors: {total_errors}
        """)

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

    # Password list input
    passwords = st.text_area(
        "Enter possible passwords (one per line)",
        help="Enter passwords that might be needed for PDF files. These will be available for selection for each group of files."
    ).split('\n')
    passwords = [p.strip() for p in passwords if p.strip()]

    # Clear password cache when keywords or passwords change
    if ('last_keywords' not in st.session_state or st.session_state.last_keywords != keywords or
        'last_passwords' not in st.session_state or st.session_state.last_passwords != passwords):
        st.session_state.pdf_handler.clear_password_cache()
        st.session_state.last_keywords = keywords
        st.session_state.last_passwords = passwords

    # Initialize session state for matches
    if 'exact_matches_by_keyword' not in st.session_state:
        st.session_state.exact_matches_by_keyword = {}
    if 'content_matches_by_sender' not in st.session_state:
        st.session_state.content_matches_by_sender = {}

    # Search Emails
    if st.button("Search Emails"):
        with st.spinner("Searching emails..."):
            emails = st.session_state.gmail_handler.search_emails(keywords)
            if not emails:
                st.warning("No emails found with PDF attachments matching the keywords")
                return
            
            st.session_state.search_results = emails
            st.success(f"Found {len(emails)} emails with PDF attachments")
            
            # Clear previous matches
            st.session_state.exact_matches_by_keyword = {}
            st.session_state.content_matches_by_sender = {}
            
            # Group matches by type and keyword/sender
            for email in emails:
                if email['match_type'] == 'exact':
                    # Find matching keyword
                    matching_keyword = next((k for k in keywords if k.lower() in email['subject'].lower()), 'Other')
                    if matching_keyword not in st.session_state.exact_matches_by_keyword:
                        st.session_state.exact_matches_by_keyword[matching_keyword] = []
                    st.session_state.exact_matches_by_keyword[matching_keyword].append(email)
                else:
                    sender_key = f"{email.get('sender_email', 'unknown')}"
                    if sender_key not in st.session_state.content_matches_by_sender:
                        st.session_state.content_matches_by_sender[sender_key] = []
                    st.session_state.content_matches_by_sender[sender_key].append(email)

    # Display Results and Select Attachments
    if 'search_results' in st.session_state:
        # Display exact matches by keyword
        if st.session_state.exact_matches_by_keyword:
            st.subheader("Exact Matches")
            
            for keyword, matches in st.session_state.exact_matches_by_keyword.items():
                with st.expander(f"Exact Matches - {keyword}", expanded=True):
                    # Initialize selected attachments for this keyword
                    keyword_key = f"selected_attachments_{keyword}"
                    if keyword_key not in st.session_state:
                        st.session_state[keyword_key] = set()
                    
                    # Create attachment list for this keyword
                    keyword_attachments = []
                    for email in matches:
                        for attachment in email['attachments']:
                            keyword_attachments.append({
                                'subject': email['subject'],
                                'sender': email['sender'],
                                'sender_email': email.get('sender_email', 'Unknown'),
                                'date': format_ist_time(email['date']),
                                'filename': attachment['filename'],
                                'size': f"{attachment['size']/1024:.1f} KB",
                                'id': f"{email['id']}_{attachment['id']}",
                                'message_id': email['id'],
                                'attachment_id': attachment['id'],
                                'email_date': format_file_date(email['date']),
                                'password_hint': email.get('password_hint', '')
                            })
                    
                    # Select all / Deselect all buttons
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"Select All - {keyword}"):
                            st.session_state[keyword_key] = {att['id'] for att in keyword_attachments}
                            st.rerun()
                    with col2:
                        if st.button(f"Deselect All - {keyword}"):
                            st.session_state[keyword_key] = set()
                            st.rerun()
                    
                    # Display table
                    edited_df = display_results_table(keyword_attachments, f"exact_{keyword}", keyword_key)
        
        # Display content matches by sender
        if st.session_state.content_matches_by_sender:
            st.subheader("Content Matches")
            
            for sender, matches in st.session_state.content_matches_by_sender.items():
                with st.expander(f"Content Matches - {sender}", expanded=True):
                    # Initialize selected attachments for this sender
                    sender_key = f"selected_content_{sender}"
                    if sender_key not in st.session_state:
                        st.session_state[sender_key] = set()
                    
                    # Create attachment list for this sender
                    sender_attachments = []
                    for email in matches:
                        for attachment in email['attachments']:
                            sender_attachments.append({
                                'subject': email.get('subject', 'No Subject'),
                                'sender': email.get('sender', 'Unknown'),
                                'sender_email': email.get('sender_email', 'Unknown'),
                                'date': format_ist_time(email['date']),
                                'filename': attachment['filename'],
                                'size': f"{attachment['size']/1024:.1f} KB",
                                'id': f"{email['id']}_{attachment['id']}",
                                'message_id': email['id'],
                                'attachment_id': attachment['id'],
                                'email_date': format_file_date(email['date']),
                                'password_hint': email.get('password_hint', '')
                            })
                    
                    # Select all / Deselect all buttons
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"Select All - {sender}"):
                            st.session_state[sender_key] = {att['id'] for att in sender_attachments}
                            st.rerun()
                    with col2:
                        if st.button(f"Deselect All - {sender}"):
                            st.session_state[sender_key] = set()
                            st.rerun()
                    
                    # Display table
                    edited_df = display_results_table(sender_attachments, f"content_{sender}", sender_key)
                    
                    # Add selected attachments from this group to the main selection
                    st.session_state[sender_key].update(
                        att['id'] for att in sender_attachments
                        if att['id'] in st.session_state[sender_key]
                    )

        # Get selected attachments from all groups
        selected_exact_attachments = []
        for keyword, matches in st.session_state.exact_matches_by_keyword.items():
            keyword_key = f"selected_attachments_{keyword}"
            if keyword_key in st.session_state:
                for email in matches:
                    for attachment in email['attachments']:
                        if f"{email['id']}_{attachment['id']}" in st.session_state[keyword_key]:
                            selected_exact_attachments.append({
                                'subject': email['subject'],
                                'sender': email['sender'],
                                'sender_email': email.get('sender_email', 'Unknown'),
                                'date': format_ist_time(email['date']),
                                'filename': attachment['filename'],
                                'size': f"{attachment['size']/1024:.1f} KB",
                                'id': f"{email['id']}_{attachment['id']}",
                                'message_id': email['id'],
                                'attachment_id': attachment['id'],
                                'email_date': format_file_date(email['date']),
                                'password_hint': email.get('password_hint', '')
                            })

        selected_content_attachments = []
        for sender, matches in st.session_state.content_matches_by_sender.items():
            sender_key = f"selected_content_{sender}"
            if sender_key in st.session_state:
                for email in matches:
                    for attachment in email['attachments']:
                        if f"{email['id']}_{attachment['id']}" in st.session_state[sender_key]:
                            selected_content_attachments.append({
                                'subject': email.get('subject', 'No Subject'),
                                'sender': email.get('sender', 'Unknown'),
                                'sender_email': email.get('sender_email', 'Unknown'),
                                'date': format_ist_time(email['date']),
                                'filename': attachment['filename'],
                                'size': f"{attachment['size']/1024:.1f} KB",
                                'id': f"{email['id']}_{attachment['id']}",
                                'message_id': email['id'],
                                'attachment_id': attachment['id'],
                                'email_date': format_file_date(email['date']),
                                'password_hint': email.get('password_hint', '')
                            })

        if selected_exact_attachments or selected_content_attachments:
            st.subheader("Upload to Google Drive")
            
            # Show selection summary
            show_selection_summary()
            
            # Main folder input
            main_folder = st.text_input(
                "Enter main Google Drive folder name",
                help="Enter the name of the main folder where all files will be organized"
            )
            
            if main_folder and st.button("Process Selected Files"):
                with st.spinner("Processing files..."):
                    try:
                        # Create main folder
                        main_folder_id = st.session_state.drive_handler.check_folder_exists(main_folder)
                        if not main_folder_id:
                            main_folder_id = st.session_state.drive_handler.create_folder(main_folder)
                            if not main_folder_id:
                                st.error("Failed to create main folder in Google Drive")
                                return
                        
                        results_by_group = {}
                        processed_files = set()
                        
                        # Process exact matches by keyword
                        for keyword in st.session_state.exact_matches_by_keyword:
                            keyword_attachments = [att for att in selected_exact_attachments if att['subject'].lower().find(keyword.lower()) != -1]
                            if keyword_attachments:
                                # Find working password for this group
                                working_password = get_group_password(keyword_attachments, passwords) if passwords else None
                                group_passwords = [working_password] if working_password else passwords
                                
                                folder_name = f"{keyword}_exact_matches"
                                success_count, password_required, processed_files, processed_filenames, error_files = process_pdf_batch(
                                    keyword_attachments,
                                    main_folder_id,
                                    folder_name,
                                    passwords=group_passwords,
                                    processed_files=processed_files
                                )
                                
                                results_by_group[folder_name] = {
                                    'success_count': success_count,
                                    'password_required': password_required,
                                    'processed_files': processed_files,
                                    'processed_filenames': processed_filenames,
                                    'error_files': error_files,
                                    'folder_name': folder_name,
                                    'folder_id': main_folder_id
                                }
                        
                        # Process content matches by sender
                        for sender in st.session_state.content_matches_by_sender:
                            sender_attachments = [att for att in selected_content_attachments if att['sender_email'] == sender]
                            if sender_attachments:
                                # Find working password for this group
                                working_password = get_group_password(sender_attachments, passwords) if passwords else None
                                group_passwords = [working_password] if working_password else passwords
                                
                                folder_name = f"content_matches_{sender}"
                                success_count, password_required, processed_files, processed_filenames, error_files = process_pdf_batch(
                                    sender_attachments,
                                    main_folder_id,
                                    folder_name,
                                    passwords=group_passwords,
                                    processed_files=processed_files
                                )
                                
                                results_by_group[folder_name] = {
                                    'success_count': success_count,
                                    'password_required': password_required,
                                    'processed_files': processed_files,
                                    'processed_filenames': processed_filenames,
                                    'error_files': error_files,
                                    'folder_name': folder_name,
                                    'folder_id': main_folder_id
                                }
                        
                        # Show final status
                        show_final_status(results_by_group)
                        
                        # Show detailed results
                        show_processing_results(results_by_group)
                        
                    except Exception as e:
                        logger.error(f"Error in batch processing: {str(e)}")
                        st.error(f"An error occurred during processing: {str(e)}")

if __name__ == "__main__":
    main() 