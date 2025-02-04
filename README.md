# Gmail PDF Processor

Composed with Cursor - Use with Discretion. AI hallucinations and potential errors are possible.

A secure application for processing PDF attachments from Gmail, organizing them in Google Drive, and extracting transaction data.

## Features

- Secure Gmail authentication using OAuth2
- Search emails by keywords
- Process PDF attachments with password protection
- Organize files in Google Drive with custom folder structure
- Extract transaction data from PDFs
- Export data to Google Sheets
- Secure session management and activity logging

## Quick Start

1. Double-click `run.sh` to start the application
   - This will automatically set up the virtual environment and install dependencies
   - The app will open in your default web browser

OR

2. Manual Setup:
```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r mail_PDF_scraper/requirements.txt

# Run the application
cd mail_PDF_scraper
streamlit run app.py
```

## Prerequisites

- Python 3.8 or higher
- Google account with Gmail and Drive access
- Google Cloud project with Gmail and Drive APIs enabled
- OAuth2 credentials (credentials.json) in the credentials folder

## Configuration

1. Place your `credentials.json` file in the `credentials` folder
2. First run will require Google authentication
3. Streamlit configuration is in `.streamlit/config.toml`

## Usage

1. Select operation phase (Email Processing or Transaction Extraction)
2. For Email Processing:
   - Enter search keywords and possible PDF passwords
   - Select files to process
   - Files will be organized in Google Drive
3. For Transaction Extraction:
   - Select folders to process
   - Data will be exported to Google Sheets

## Security Features

- OAuth2 authentication
- Secure session management
- Password handling for protected PDFs
- Activity logging
- CSRF protection enabled

## Project Structure

```
mail_PDF_scraper/
├── app.py              # Main application
├── requirements.txt    # Python dependencies
├── run.sh             # Startup script
├── credentials/       # OAuth credentials
└── logs/             # Application logs
```

## License

This work is licensed under CC BY-SA NC 4.0 (Creative Commons Attribution-ShareAlike Non-commercial 4.0 International License).

## Support

For issues and feature requests, please create an issue in the GitHub repository. 