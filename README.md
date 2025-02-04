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
- Cross-platform support (Windows, macOS, Linux)

## Quick Start

### Windows Users:
1. Double-click `run.bat` in the mail_PDF_scraper folder
   - This will automatically set up the virtual environment and install dependencies
   - The app will open in your default web browser

### macOS/Linux Users:
1. Double-click `run.sh` in the mail_PDF_scraper folder
   - This will automatically set up the virtual environment and install dependencies
   - The app will open in your default web browser

### Manual Setup (All Platforms):
```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

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
- Secure credential storage

## Project Structure

```
mail_PDF_scraper/
├── app.py              # Main application
├── requirements.txt    # Python dependencies
├── run.sh             # Unix startup script
├── run.bat            # Windows startup script
├── credentials/       # OAuth credentials
├── logs/             # Application logs
└── utils/            # Utility modules
```

## Error Handling

The application includes comprehensive error handling:
- Validates Python installation
- Checks for required credentials
- Handles virtual environment setup
- Provides clear error messages
- Logs errors for debugging

## License

This work is licensed under CC BY-SA NC 4.0 (Creative Commons Attribution-ShareAlike Non-commercial 4.0 International License).

## Support

For issues and feature requests, please create an issue in the GitHub repository.

## Development

To contribute to the project:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Troubleshooting

Common issues and solutions:
- If the app fails to start, check Python installation and version
- For authentication errors, verify credentials.json is in place
- For permission issues, ensure proper Google Cloud API access
- Check logs/ directory for detailed error messages