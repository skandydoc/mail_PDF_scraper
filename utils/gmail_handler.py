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
import webbrowser
import socket
import secrets

# Get module logger
logger = logging.getLogger(__name__)

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def find_free_port(start=8502, end=8999):
    """Find a free port in the given range"""
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(('localhost', port))
                return port
            except OSError:
                continue
    raise RuntimeError("No free ports found in range")

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
                        # Find a free port for OAuth callback
                        oauth_port = find_free_port()
                        logger.info(f"Using port {oauth_port} for OAuth callback")
                        
                        # Generate a secure state token
                        state = secrets.token_urlsafe(32)
                        logger.info("Generated secure state token")
                        
                        # Configure the OAuth flow
                        flow = InstalledAppFlow.from_client_secrets_file(
                            'credentials.json', 
                            SCOPES,
                            redirect_uri=f'http://localhost:{oauth_port}'
                        )
                        
                        # Get the authorization URL
                        auth_url, _ = flow.authorization_url(
                            access_type='offline',
                            include_granted_scopes='true',
                            state=state,
                            prompt='consent'
                        )
                        
                        # Open the authorization URL in the default browser
                        webbrowser.open(auth_url)
                        
                        success_html = """
                        <html>
                            <head>
                                <title>Authentication Successful</title>
                                <style>
                                    body {
                                        font-family: Arial, sans-serif;
                                        display: flex;
                                        justify-content: center;
                                        align-items: center;
                                        height: 100vh;
                                        margin: 0;
                                        background-color: #f5f5f5;
                                    }
                                    .container {
                                        text-align: center;
                                        padding: 2rem;
                                        background: white;
                                        border-radius: 8px;
                                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                                    }
                                    h1 { color: #4CAF50; margin-bottom: 1rem; }
                                    p { color: #666; margin-bottom: 1.5rem; }
                                    .spinner {
                                        border: 4px solid #f3f3f3;
                                        border-top: 4px solid #4CAF50;
                                        border-radius: 50%;
                                        width: 40px;
                                        height: 40px;
                                        animation: spin 1s linear infinite;
                                        margin: 1rem auto;
                                    }
                                    @keyframes spin {
                                        0% { transform: rotate(0deg); }
                                        100% { transform: rotate(360deg); }
                                    }
                                </style>
                                <script>
                                    function closeWindow() {
                                        if (window.opener) {
                                            window.opener.postMessage('oauth-complete', '*');
                                        }
                                        setTimeout(function() {
                                            window.close();
                                            if (!window.closed) {
                                                window.location.href = 'http://localhost:8501';
                                            }
                                        }, 2000);
                                    }
                                    window.onload = closeWindow;
                                </script>
                            </head>
                            <body>
                                <div class="container">
                                    <h1>Authentication Successful!</h1>
                                    <div class="spinner"></div>
                                    <p>This window will close automatically in 2 seconds...</p>
                                </div>
                            </body>
                        </html>
                        """
                        
                        # Run the local server to handle the OAuth callback
                        self.creds = flow.run_local_server(
                            host='localhost',
                            port=oauth_port,
                            authorization_prompt_message='',
                            success_message=success_html,
                            open_browser=False,
                            timeout_seconds=120,
                            state=state
                        )
                        
                        logger.info("OAuth flow completed successfully")
                        
                    except Exception as e:
                        logger.error(f"Error in OAuth flow: {str(e)}")
                        raise RuntimeError(
                            "Authentication failed. Please ensure you have enabled the Gmail API "
                            "and configured the OAuth consent screen in Google Cloud Console."
                        )

                # Save credentials for future use
                try:
                    logger.info("Saving credentials to token.pickle")
                    with open('token.pickle', 'wb') as token:
                        pickle.dump(self.creds, token)
                    # Set secure file permissions
                    os.chmod('token.pickle', 0o600)
                    logger.info("Credentials saved successfully")
                except Exception as e:
                    logger.warning(f"Could not save credentials: {str(e)}")
                    # Continue even if saving fails

            self.service = build('gmail', 'v1', credentials=self.creds)
            logger.info("Gmail service initialized successfully")
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