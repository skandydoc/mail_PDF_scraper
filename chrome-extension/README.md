# Gmail PDF Processor Chrome Extension

A Chrome extension that helps you process and organize PDF attachments from your Gmail account. This extension provides a convenient way to search, download, and organize PDF attachments directly from your browser.

Composed with Cursor - Use with Discretion. AI hallucinations and potential errors are possible.

## Features

- 🔍 Search PDF attachments using keywords
- 📅 Filter by date range
- 👥 Organize attachments by sender
- 🔒 Handle password-protected PDFs
- ⬇️ Batch download capabilities
- 🎯 Direct Gmail integration
- 🔐 Secure OAuth2 authentication

## Installation

1. Clone this repository or download the ZIP file
2. Open Chrome and navigate to `chrome://extensions/`
3. Enable "Developer mode" in the top right corner
4. Click "Load unpacked" and select the `chrome-extension` directory

## Setup

1. Create a new project in the [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the Gmail API and Google Drive API
3. Create OAuth 2.0 credentials
4. Replace `${YOUR_CLIENT_ID}` in `manifest.json` with your actual OAuth client ID

## Usage

1. Click the extension icon in Chrome
2. Sign in with your Google account
3. Enter search keywords (comma-separated)
4. Specify the date range (e.g., "7 days", "1 month")
5. Optional: Check "Organize by sender" to group results
6. Click "Process PDFs" to search for attachments
7. Download individual PDFs or use batch download

## Security

- Uses OAuth 2.0 for secure authentication
- No passwords are stored locally
- All communication is encrypted
- Follows Chrome extension security best practices

## Development

To modify or enhance the extension:

1. Make changes to the source files
2. Reload the extension in Chrome
3. Test thoroughly before distribution

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under CC BY-SA NC 4.0 (Creative Commons Attribution-ShareAlike Non-commercial 4.0 International License).

## Support

For support, feature requests, or bug reports, please open an issue in the GitHub repository.

## Acknowledgments

- Gmail API
- Chrome Extensions API
- Google Drive API 