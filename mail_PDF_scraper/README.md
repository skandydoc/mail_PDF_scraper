# Gmail PDF Processor

A secure and efficient tool for processing PDF attachments from Gmail, with support for transaction extraction and organization.

Composed with Cursor - Use with Discretion. AI hallucinations and potential errors are possible.

## Features

- Secure Gmail authentication using OAuth2
- PDF attachment download and processing
- Smart organization of files in Google Drive
- Transaction extraction from PDFs
- Google Sheets integration for transaction tracking
- Password-protected PDF support
- Audit logging and security features
- Two-phase processing:
  1. Email Processing & PDF Storage
  2. Transaction Extraction

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/mail_PDF_scraper.git
cd mail_PDF_scraper
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up Google Cloud Project and obtain credentials:
   - Create a project in Google Cloud Console
   - Enable Gmail, Drive, and Sheets APIs
   - Create OAuth2 credentials
   - Download credentials as `credentials.json`

5. Configure Streamlit:
```bash
mkdir -p .streamlit
echo 'browser.gatherUsageStats = false' > .streamlit/config.toml
```

## Usage

You can run the application in two ways:

1. Using the convenience script (recommended):
```bash
./run.sh
```

2. Or manually:
```bash
cd mail_PDF_scraper
streamlit run app.py
```

After starting the application:
1. Open the URL shown in your terminal (typically http://localhost:8501)
2. Authenticate with your Google account
3. Select operation phase:
   - Phase 1: Process emails and store PDFs
   - Phase 2: Extract transactions from stored PDFs
4. Follow the UI prompts for each phase

## Project Structure

```
mail_PDF_scraper/
├── app.py                    # Main application file
├── run.sh                    # Convenience script to run the app
├── requirements.txt          # Python dependencies
├── credentials.json          # Google OAuth credentials
├── utils/                    # Utility modules
│   ├── gmail_handler.py      # Gmail API integration
│   ├── drive_handler.py      # Google Drive integration
│   ├── sheets_handler.py     # Google Sheets integration
│   ├── pdf_handler.py        # PDF processing
│   ├── security.py          # Security features
│   └── logger_config.py     # Logging configuration
├── logs/                    # Application logs
├── audit_logs/             # Security audit logs
└── .streamlit/             # Streamlit configuration
```

## Security Features

- OAuth2 authentication
- Secure credential handling
- Audit logging
- Session management
- Password handling for protected PDFs

## Error Handling

- Comprehensive error logging
- User-friendly error messages
- Graceful failure recovery
- Transaction validation

## Contributing

Please read CONTRIBUTING.md for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under CC BY-SA NC 4.0 (Creative Commons Attribution-ShareAlike Non-commercial 4.0 International licence).

## Acknowledgments

- Google Cloud Platform
- Streamlit
- PyPDF2
- Python community

## Support

For support, please open an issue in the GitHub repository or contact the maintainers.