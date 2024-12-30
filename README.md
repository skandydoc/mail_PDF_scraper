# Gmail PDF Attachment Processor

A secure and efficient tool for downloading and organizing PDF attachments from Gmail.

## Features

- Search Gmail for PDF attachments using keywords
- Process password-protected PDFs
- Organize files in Google Drive with customizable folder structure
- Support for exact and content-based matches
- Secure authentication and session management
- IST timezone support
- Customizable file naming based on email dates

## Setup

1. Create a Google Cloud Project and enable Gmail and Drive APIs
2. Download credentials.json and place it in the project root
3. Install dependencies:
   ```bash
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

## License
This project is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License. You can view the full license [here](https://creativecommons.org/licenses/by-nc-sa/4.0/).
![CC BY-NC-SA 4.0](https://i.creativecommons.org/l/by-nc-sa/4.0/88x31.png)

## Disclaimer
This software is provided "as is", without warranty of any kind, express or implied. The creators and contributors shall not be liable for any claim, damages, or other liability arising from the use of the software.