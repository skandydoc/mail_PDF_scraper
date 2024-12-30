from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import base64
import os.path
import pickle
from typing import List, Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

class GmailHandler:
    def __init__(self):
        self.creds = None
        self.service = None

    def authenticate(self) -> bool:
        """
        Handles Gmail authentication using OAuth2
        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            if os.path.exists('token.pickle'):
                with open('token.pickle', 'rb') as token:
                    self.creds = pickle.load(token)

            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        'credentials.json', SCOPES)
                    self.creds = flow.run_local_server(port=0)

                with open('token.pickle', 'wb') as token:
                    pickle.dump(self.creds, token)

            self.service = build('gmail', 'v1', credentials=self.creds)
            return True
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