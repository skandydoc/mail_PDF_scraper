# Gmail PDF Processor

Composed with Cursor - Use with Discretion. AI hallucinations and potential errors are possible.

A secure application for processing PDF attachments from Gmail, organizing them in Google Drive, and extracting transaction data.

## Features

- Secure Gmail authentication
- PDF attachment processing
- Automatic Google Drive organization
- Transaction data extraction
- Password-protected PDF support
- Clean and intuitive UI

## Quick Start with Docker

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop)
2. Clone this repository:
   ```bash
   git clone https://github.com/skandydoc/mail_PDF_scraper.git
   cd mail_PDF_scraper
   ```
3. Place your Google OAuth credentials in `credentials/credentials.json`
4. Run the application:
   ```bash
   docker-compose up
   ```
5. Open your browser and navigate to: http://localhost:8501

## Manual Setup

1. Install Python 3.11 or later
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Place Google OAuth credentials in `credentials/credentials.json`
5. Run the application:
   ```bash
   streamlit run app.py
   ```

## Usage

1. Sign in with your Google account
2. Select operation phase:
   - Phase 1: Email Processing & PDF Storage
   - Phase 2: Transaction Extraction
3. Follow the on-screen instructions for each phase

## Security Features

- Secure OAuth2 authentication
- No password storage
- Encrypted session management
- Secure file handling
- CSRF protection

## License

This project is licensed under CC BY-SA NC 4.0 (Creative Commons Attribution-ShareAlike Non-commercial 4.0 International License).

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Support

For support, please open an issue in the GitHub repository. 