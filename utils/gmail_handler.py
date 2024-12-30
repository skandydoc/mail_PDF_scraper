from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import base64
import os.path
import pickle
from typing import List, Dict, Any
import logging
from datetime import datetime
import re

# Get module logger
logger = logging.getLogger(__name__)

# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/drive.file'  # For file uploads
]

class GmailHandler:
    def __init__(self):
        self.creds = None
        self.service = None
        logger.info("Gmail handler initialized")

    def authenticate(self) -> bool:
        """
        Handles Gmail authentication using OAuth2
        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            logger.info("Starting authentication process")
            
            if not os.path.exists('credentials.json'):
                logger.error("credentials.json not found in project root directory")
                raise FileNotFoundError(
                    "credentials.json not found. Please follow the setup instructions in README.md "
                    "to create and download your Google Cloud credentials."
                )

            if os.path.exists('token.pickle'):
                logger.info("Found existing token.pickle file")
                with open('token.pickle', 'rb') as token:
                    self.creds = pickle.load(token)

            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    logger.info("Refreshing expired credentials")
                    try:
                        self.creds.refresh(Request())
                        logger.info("Credentials refreshed successfully")
                    except Exception as e:
                        logger.error(f"Error refreshing credentials: {str(e)}")
                        self.creds = None
                
                if not self.creds:
                    logger.info("Starting OAuth flow")
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            'credentials.json', 
                            SCOPES
                        )
                        
                        # Simple local server with minimal HTML
                        self.creds = flow.run_local_server(
                            port=0,  # Let the OS choose an available port
                            authorization_prompt_message='',
                            success_message='Authentication successful! You may close this window.',
                            open_browser=True
                        )
                        
                        logger.info("OAuth flow completed successfully")
                        
                        # Save credentials immediately
                        try:
                            logger.info("Saving credentials to token.pickle")
                            with open('token.pickle', 'wb') as token:
                                pickle.dump(self.creds, token)
                            os.chmod('token.pickle', 0o600)
                            logger.info("Credentials saved successfully")
                        except Exception as e:
                            logger.warning(f"Could not save credentials: {str(e)}")
                        
                        # Initialize service immediately
                        self.service = build('gmail', 'v1', credentials=self.creds)
                        logger.info("Gmail service initialized successfully")
                        return True
                        
                    except Exception as e:
                        logger.error(f"Error in OAuth flow: {str(e)}")
                        raise RuntimeError(
                            "Authentication failed. Please ensure you have enabled the Gmail API "
                            "and configured the OAuth consent screen in Google Cloud Console."
                        )

            self.service = build('gmail', 'v1', credentials=self.creds)
            logger.info("Gmail service initialized successfully")
            return True

        except FileNotFoundError as e:
            logger.error(str(e))
            raise
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            return False

    def search_emails(self, keywords: List[str], max_results: int = None) -> List[Dict[str, Any]]:
        """
        Search emails based on keywords and return those with PDF attachments
        Args:
            keywords: List of search keywords
            max_results: Maximum number of emails to retrieve (None for no limit)
        Returns:
            List of dictionaries containing email details and match type
        """
        try:
            if not self.service:
                raise RuntimeError("Gmail service not initialized. Please authenticate first.")

            # Construct search query for exact matches
            exact_query = ' OR '.join(f'subject:"{keyword}"' for keyword in keywords)
            exact_query += ' has:attachment filename:pdf'
            
            # Construct search query for content matches
            content_query = ' OR '.join(f'"{keyword}"' for keyword in keywords)
            content_query += ' -(' + exact_query + ') has:attachment filename:pdf'  # Exclude exact matches

            results = []
            
            # Search for exact matches
            exact_results = self.service.users().messages().list(
                userId='me',
                q=exact_query,
                maxResults=max_results
            ).execute()
            
            exact_messages = exact_results.get('messages', [])
            
            # Search for content matches
            content_results = self.service.users().messages().list(
                userId='me',
                q=content_query,
                maxResults=max_results
            ).execute()
            
            content_messages = content_results.get('messages', [])

            # Process exact matches
            for message in exact_messages:
                try:
                    email_data = self.service.users().messages().get(
                        userId='me',
                        id=message['id'],
                        format='full'
                    ).execute()

                    attachments = []
                    subject = ''
                    sender = ''
                    password_hint = ''

                    # Get email headers
                    for header in email_data['payload']['headers']:
                        if header['name'] == 'Subject':
                            subject = header['value']
                        elif header['name'] == 'From':
                            sender = header['value']

                    # Get email body and look for password hints
                    if 'parts' in email_data['payload']:
                        for part in email_data['payload']['parts']:
                            if part.get('mimeType') == 'text/plain':
                                body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                                # Look for common password hint patterns
                                hint_patterns = [
                                    r'password[:\s]+([^\n]+)',
                                    r'passcode[:\s]+([^\n]+)',
                                    r'pin[:\s]+([^\n]+)',
                                    r'key[:\s]+([^\n]+)'
                                ]
                                for pattern in hint_patterns:
                                    match = re.search(pattern, body, re.IGNORECASE)
                                    if match:
                                        password_hint = match.group(1).strip()
                                        break

                    # Get attachments
                    if 'parts' in email_data['payload']:
                        attachments = self._process_parts(email_data['payload']['parts'], message['id'])

                    if attachments:
                        results.append({
                            'id': message['id'],
                            'subject': subject,
                            'sender': sender,
                            'date': email_data['internalDate'],
                            'attachments': attachments,
                            'match_type': 'exact',
                            'password_hint': password_hint
                        })

                except Exception as e:
                    logger.error(f"Error processing message {message['id']}: {str(e)}")
                    continue

            # Process content matches
            for message in content_messages:
                try:
                    email_data = self.service.users().messages().get(
                        userId='me',
                        id=message['id'],
                        format='full'
                    ).execute()

                    attachments = []
                    subject = ''
                    sender = ''
                    password_hint = ''

                    # Get email headers and process similar to exact matches
                    for header in email_data['payload']['headers']:
                        if header['name'] == 'Subject':
                            subject = header['value']
                        elif header['name'] == 'From':
                            sender = header['value']

                    # Get email body and look for password hints
                    if 'parts' in email_data['payload']:
                        for part in email_data['payload']['parts']:
                            if part.get('mimeType') == 'text/plain':
                                body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                                # Look for common password hint patterns
                                hint_patterns = [
                                    r'password[:\s]+([^\n]+)',
                                    r'passcode[:\s]+([^\n]+)',
                                    r'pin[:\s]+([^\n]+)',
                                    r'key[:\s]+([^\n]+)'
                                ]
                                for pattern in hint_patterns:
                                    match = re.search(pattern, body, re.IGNORECASE)
                                    if match:
                                        password_hint = match.group(1).strip()
                                        break

                    # Get attachments
                    if 'parts' in email_data['payload']:
                        attachments = self._process_parts(email_data['payload']['parts'], message['id'])

                    if attachments:
                        results.append({
                            'id': message['id'],
                            'subject': subject,
                            'sender': sender,
                            'date': email_data['internalDate'],
                            'attachments': attachments,
                            'match_type': 'content',
                            'password_hint': password_hint
                        })

                except Exception as e:
                    logger.error(f"Error processing message {message['id']}: {str(e)}")
                    continue

            return results

        except Exception as e:
            logger.error(f"Error searching emails: {str(e)}")
            return []

    def _process_parts(self, parts: List[Dict[str, Any]], message_id: str) -> List[Dict[str, Any]]:
        """
        Process email parts to extract PDF attachments
        Args:
            parts: List of email parts
            message_id: Email message ID
        Returns:
            List of attachment details
        """
        attachments = []
        for part in parts:
            if part.get('filename', '').lower().endswith('.pdf'):
                attachment = {
                    'id': part['body'].get('attachmentId'),
                    'filename': part['filename'],
                    'size': part['body'].get('size', 0),
                    'message_id': message_id
                }
                attachments.append(attachment)
            if 'parts' in part:
                attachments.extend(self._process_parts(part['parts'], message_id))
        return attachments

    def download_attachment(self, message_id: str, attachment_id: str) -> bytes:
        """
        Download a specific attachment
        Args:
            message_id: Email message ID
            attachment_id: Attachment ID
        Returns:
            Attachment data as bytes
        """
        try:
            if not self.service:
                raise RuntimeError("Gmail service not initialized. Please authenticate first.")

            attachment = self.service.users().messages().attachments().get(
                userId='me',
                messageId=message_id,
                id=attachment_id
            ).execute()

            data = attachment['data']
            return base64.urlsafe_b64decode(data.encode('UTF-8'))
        except Exception as e:
            logger.error(f"Error downloading attachment: {str(e)}")
            return None 