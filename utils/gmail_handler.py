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
from datetime import datetime

# Get module logger
logger = logging.getLogger(__name__)

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

class GmailHandler:
    def __init__(self):
        self.creds = None
        self.service = None
        logger.info("Gmail handler initialized")

    def _create_local_server_handler(self):
        """Create a custom success handler for OAuth flow"""
        def success_handler(url):
            return """
            <html>
                <head>
                    <title>Authentication Successful</title>
                    <meta http-equiv="refresh" content="2;url=http://localhost:8501">
                    <script>
                        function closeAndRedirect() {
                            if (window.opener) {
                                window.opener.location.reload();
                                setTimeout(function() {
                                    window.close();
                                    window.location.href = 'http://localhost:8501';
                                }, 500);
                            } else {
                                window.location.href = 'http://localhost:8501';
                            }
                        }
                        
                        // Execute immediately and also set as onload handler
                        closeAndRedirect();
                        window.onload = closeAndRedirect;
                        
                        // Final fallback
                        setTimeout(function() {
                            window.location.href = 'http://localhost:8501';
                        }, 2000);
                    </script>
                    <style>
                        body { 
                            font-family: Arial, sans-serif; 
                            text-align: center; 
                            padding-top: 50px;
                            background-color: #f0f2f6;
                            margin: 0;
                            height: 100vh;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                        }
                        .success { 
                            color: #4CAF50;
                            margin-bottom: 20px;
                            font-size: 24px;
                        }
                        .message { 
                            margin-top: 20px;
                            color: #666;
                            font-size: 16px;
                        }
                        .container {
                            background: white;
                            padding: 40px;
                            border-radius: 10px;
                            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                            max-width: 400px;
                            width: 90%;
                            animation: fadeIn 0.5s ease-out;
                        }
                        @keyframes fadeIn {
                            from { opacity: 0; transform: translateY(20px); }
                            to { opacity: 1; transform: translateY(0); }
                        }
                        .checkmark {
                            font-size: 48px;
                            color: #4CAF50;
                            margin-bottom: 20px;
                            animation: scaleIn 0.5s ease-out;
                        }
                        @keyframes scaleIn {
                            from { transform: scale(0); }
                            to { transform: scale(1); }
                        }
                        .spinner {
                            width: 30px;
                            height: 30px;
                            border: 3px solid #f3f3f3;
                            border-top: 3px solid #4CAF50;
                            border-radius: 50%;
                            margin: 20px auto;
                            animation: spin 1s linear infinite;
                        }
                        @keyframes spin {
                            0% { transform: rotate(0deg); }
                            100% { transform: rotate(360deg); }
                        }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="checkmark">✓</div>
                        <h2 class="success">Authentication Successful!</h2>
                        <div class="spinner"></div>
                        <p class="message">Redirecting back to application...</p>
                    </div>
                </body>
            </html>
            """
        return success_handler

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
                        
                        # Run the local server with custom success page
                        self.creds = flow.run_local_server(
                            port=0,
                            success_handler=self._create_local_server_handler(),
                            authorization_prompt_message=None,
                            open_browser=True
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