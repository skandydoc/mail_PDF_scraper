# Gmail PDF Attachment Processor

A secure and efficient tool for downloading and organizing PDF attachments from Gmail, with special focus on credit card statements.

Composed with Cursor - Use with Discretion. AI hallucinations and potential errors are possible.

## Features

- Search Gmail for PDF attachments using keywords
- Process password-protected PDFs and save unencrypted versions
- Organize files in Google Drive with customizable folder structure
- Extract and organize transactions from credit card statements
- Automatically create and update Google Sheets with transaction data
- Support for exact and content-based matches
- Secure authentication and session management
- IST timezone support
- Customizable file naming based on email dates

## Key Benefits

- Automatically creates separate folders for each search keyword
- Saves unencrypted versions of PDFs for easy access
- Creates a Google Sheet with transaction details
- Each group of files gets its own sheet tab
- Transactions are formatted with clear separators and file references
- Pastel green background for better readability

## Setup

1. Create a Google Cloud Project and enable Gmail, Drive, and Sheets APIs
2. Download credentials.json and place it in the project root
3. Install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

## Usage

1. Run the application:
   ```bash
   streamlit run app.py
   ```
2. Sign in with your Google account
3. Enter search keywords
4. Select files to process
5. Configure folder structure and passwords if needed
6. Process files
7. Access your processed files in Google Drive and transactions in Google Sheets

## Output Structure

- All processed files are saved in a "PDF Processor Output" folder in Google Drive
- Each search keyword gets its own subfolder
- A Google Sheet named "PDF Processor Transactions" is created
- Each keyword gets its own sheet tab
- Transactions are organized with:
  - File name as header with pastel green background
  - Transaction details in rows
  - 3-row spacing between different files
  - Clear date, description, and amount columns

## Security

- All sensitive data is handled securely
- No passwords are stored permanently
- Uses OAuth 2.0 for authentication
- Supports session management
- Follows best practices for credential handling

## License
This project is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License (CC BY-SA NC 4.0). You can view the full license [here](https://creativecommons.org/licenses/by-nc-sa/4.0/).

![CC BY-NC-SA 4.0](https://i.creativecommons.org/l/by-nc-sa/4.0/88x31.png)

## Disclaimer
This software is provided "as is", without warranty of any kind, express or implied. The creators and contributors shall not be liable for any claim, damages, or other liability arising from the use of the software.