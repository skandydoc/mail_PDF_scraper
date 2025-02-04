from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

class SheetsHandler:
    def __init__(self, credentials: Credentials):
        """
        Initialize Sheets handler with credentials
        Args:
            credentials: Google OAuth2 credentials
        """
        self.service = build('sheets', 'v4', credentials=credentials)
        
    def create_spreadsheet(self, title: str) -> Optional[str]:
        """
        Create a new Google Sheets spreadsheet
        Args:
            title: Title of the spreadsheet
        Returns:
            str: Spreadsheet ID if successful, None otherwise
        """
        try:
            spreadsheet = {
                'properties': {
                    'title': title
                }
            }
            spreadsheet = self.service.spreadsheets().create(
                body=spreadsheet,
                fields='spreadsheetId'
            ).execute()
            return spreadsheet.get('spreadsheetId')
        except Exception as e:
            logger.error(f"Error creating spreadsheet: {str(e)}")
            return None

    def create_sheet(self, spreadsheet_id: str, title: str) -> Optional[int]:
        """
        Create a new sheet in an existing spreadsheet
        Args:
            spreadsheet_id: ID of the spreadsheet
            title: Title of the new sheet
        Returns:
            int: Sheet ID if successful, None otherwise
        """
        try:
            body = {
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': title
                        }
                    }
                }]
            }
            response = self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            return response['replies'][0]['addSheet']['properties']['sheetId']
        except Exception as e:
            logger.error(f"Error creating sheet: {str(e)}")
            return None

    def write_transactions(self, spreadsheet_id: str, sheet_name: str, 
                         transactions: List[Dict[str, Any]], file_name: str) -> bool:
        """
        Write transactions to a sheet with proper formatting
        Args:
            spreadsheet_id: ID of the spreadsheet
            sheet_name: Name of the sheet
            transactions: List of transaction dictionaries
            file_name: Name of the source file
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get the sheet ID
            sheet_metadata = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheet_id = None
            for sheet in sheet_metadata.get('sheets', ''):
                if sheet['properties']['title'] == sheet_name:
                    sheet_id = sheet['properties']['sheetId']
                    break
            
            if sheet_id is None:
                sheet_id = self.create_sheet(spreadsheet_id, sheet_name)
            
            # Get the last row in the sheet
            range_name = f"{sheet_name}!A:A"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            last_row = len(result.get('values', [])) + 1
            
            # Prepare the header row with file name
            header = [[file_name]]
            header_range = f"{sheet_name}!A{last_row}"
            
            # Prepare transaction data
            data = []
            for trans in transactions:
                row = [
                    trans.get('date', ''),
                    trans.get('description', ''),
                    trans.get('amount', ''),
                    trans.get('category', '')
                ]
                data.append(row)
            
            # Prepare the requests
            requests = []
            
            # Format header row with pastel green background
            requests.append({
                'updateCells': {
                    'rows': [{
                        'values': [{
                            'userEnteredFormat': {
                                'backgroundColor': {
                                    'red': 0.85,
                                    'green': 0.92,
                                    'blue': 0.85
                                },
                                'textFormat': {
                                    'bold': True
                                }
                            }
                        }]
                    }],
                    'fields': 'userEnteredFormat',
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': last_row - 1,
                        'endRowIndex': last_row,
                        'startColumnIndex': 0,
                        'endColumnIndex': 1
                    }
                }
            })
            
            # Write the data
            body = {
                'values': header + data + [[''] * 4] * 3  # Add 3 empty rows after data
            }
            
            self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=header_range,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            # Apply the formatting
            body = {'requests': requests}
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Error writing transactions: {str(e)}")
            return False 