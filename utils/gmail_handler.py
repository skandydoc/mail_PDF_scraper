from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import base64
import os.path
import pickle
from typing import List, Dict, Any
import logging
import webbrowser

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

class GmailHandler:
    def __init__(self):
        self.creds = None
        self.service = None

    def _create_local_server_handler(self):
        """Create a custom success handler for OAuth flow"""
        success_html = """
        <html>
            <head>
                <title>Authentication Successful</title>
                <script>
                    window.onload = function() {
                        setTimeout(function() {
                            window.close();
                        }, 1000);
                    }
                </script>
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding-top: 50px; }
                    .success { color: #4CAF50; }
                    .message { margin-top: 20px; }
                </style>
            </head>
            <body>
                <h2 class="success">✓ Authentication Successful!</h2>
                <p class="message">This window will close automatically...</p>
            </body>
        </html>
        """
        return lambda x: success_html

    def authenticate(self) -> bool:
        """
        Handles Gmail authentication using OAuth2
        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            if not os.path.exists('credentials.json'):
                logger.error("credentials.json not found in project root directory")
                raise FileNotFoundError(
                    "credentials.json not found. Please follow the setup instructions in README.md "
                    "to create and download your Google Cloud credentials."
                )

            if os.path.exists('token.pickle'):
                with open('token.pickle', 'rb') as token:
                    self.creds = pickle.load(token)

            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    try:
                        self.creds.refresh(Request())
                    except Exception as e:
                        logger.error(f"Error refreshing credentials: {str(e)}")
                        self.creds = None
                
                if not self.creds:
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            'credentials.json', 
                            SCOPES,
                            redirect_uri='http://localhost:0'
                        )
                        
                        # Run the local server with custom success page
                        self.creds = flow.run_local_server(
                            port=0,
                            success_message=None,
                            authorization_prompt_message=None,
                            success_handler=self._create_local_server_handler()
                        )
                        
                    except Exception as e:
                        logger.error(f"Error in OAuth flow: {str(e)}")
                        raise RuntimeError(
                            "Authentication failed. Please ensure you have enabled the Gmail API "
                            "and configured the OAuth consent screen in Google Cloud Console."
                        )

                # Save credentials for future use
                try:
                    with open('token.pickle', 'wb') as token:
                        pickle.dump(self.creds, token)
                    # Set secure file permissions
                    os.chmod('token.pickle', 0o600)
                except Exception as e:
                    logger.warning(f"Could not save credentials: {str(e)}")
                    # Continue even if saving fails

            self.service = build('gmail', 'v1', credentials=self.creds)
            return True

        except FileNotFoundError as e:
            logger.error(str(e))
            raise
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            return False

    def search_emails(self, keywords: List[str], max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Search emails based on keywords and return those with PDF attachments
        Args:
            keywords: List of search keywords
            max_results: Maximum number of emails to retrieve
        Returns:
            List of dictionaries containing email details
        """
        try:
            if not self.service:
                raise RuntimeError("Gmail service not initialized. Please authenticate first.")

            # Construct search query
            query = ' OR '.join(f'"{keyword}"' for keyword in keywords)
            query += ' has:attachment filename:pdf'

            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            email_list = []

            for message in messages:
                try:
                    email_data = self.service.users().messages().get(
                        userId='me',
                        id=message['id']
                    ).execute()

                    attachments = []
                    subject = ''
                    sender = ''

                    # Get email headers
                    for header in email_data['payload']['headers']:
                        if header['name'] == 'Subject':
                            subject = header['value']
                        elif header['name'] == 'From':
                            sender = header['value']

                    # Get attachments
                    if 'parts' in email_data['payload']:
                        attachments = self._process_parts(email_data['payload']['parts'], message['id'])

                    if attachments:
                        email_list.append({
                            'id': message['id'],
                            'subject': subject,
                            'sender': sender,
                            'date': email_data['internalDate'],
                            'attachments': attachments
                        })

                except Exception as e:
                    logger.error(f"Error processing message {message['id']}: {str(e)}")
                    continue

            return email_list

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