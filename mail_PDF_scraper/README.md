# Gmail PDF Attachment Processor

A secure tool for downloading and organizing PDF attachments from Gmail, with support for transaction extraction and Google Sheets integration.

Composed with Cursor - Use with Discretion. AI hallucinations and potential errors are possible.

## Features

- Secure Gmail integration with OAuth2 authentication
- PDF attachment download and organization
- Transaction extraction from PDF statements
- Google Sheets integration for transaction data
- Folder-based organization in Google Drive
- Password-protected PDF support
- Search by keywords or content
- Batch processing capabilities

## Prerequisites

1. Python 3.8 or higher
2. Google Cloud Project with the following APIs enabled:
   - Gmail API
   - Google Drive API
   - Google Sheets API

## Setup Instructions

1. **Create a Google Cloud Project**:
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project or select an existing one
   - Enable the required APIs:
     - [Gmail API](https://console.cloud.google.com/apis/library/gmail.googleapis.com)
     - [Google Drive API](https://console.cloud.google.com/apis/library/drive.googleapis.com)
     - [Google Sheets API](https://console.cloud.google.com/apis/library/sheets.googleapis.com)

2. **Configure OAuth Consent Screen**:
   - Go to "OAuth consent screen" in the Google Cloud Console
   - Configure the consent screen (Internal or External)
   - Add the required scopes:
     - `https://www.googleapis.com/auth/gmail.readonly`
     - `https://www.googleapis.com/auth/drive.file`
     - `https://www.googleapis.com/auth/spreadsheets`

3. **Create OAuth 2.0 Credentials**:
   - Go to "Credentials" in the Google Cloud Console
   - Create OAuth 2.0 Client ID credentials
   - Download the credentials and save as `credentials.json` in the project root

4. **Set Up Python Environment**:
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   # Install dependencies
   pip install -r requirements.txt
   ```

5. **Configure Streamlit**:
   ```bash
   mkdir -p ~/.streamlit
   echo 'browser.gatherUsageStats = false' > ~/.streamlit/config.toml
   ```

## Usage

1. Start the application:
   ```bash
   streamlit run app.py
   ```

2. Sign in with your Google account when prompted

3. Use Phase 1 to:
   - Search for emails with PDF attachments
   - Download and organize PDFs in Google Drive

4. Use Phase 2 to:
   - Extract transactions from organized PDFs
   - View and analyze transaction data in Google Sheets

## Security Features

- OAuth 2.0 authentication
- Secure credential handling
- Session management
- Audit logging
- Password handling for protected PDFs

## Error Handling

If you encounter the "Google Sheets API not enabled" error:
1. Go to [Google Sheets API](https://console.cloud.google.com/apis/library/sheets.googleapis.com)
2. Select your project
3. Click 'Enable'
4. Wait a few minutes for the change to propagate
5. Sign out and sign back in to the application

## Contributing

Please read CONTRIBUTING.md for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under CC BY-SA NC 4.0 (Creative Commons Attribution-ShareAlike Non-commercial 4.0 International licence).

## Acknowledgments

- Google Cloud Platform
- Streamlit
- PyPDF2
- Google API Python Client

## Support

For support or feature requests, please visit our GitHub repository.