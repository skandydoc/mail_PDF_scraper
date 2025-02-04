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
        try:
            self.service = build('sheets', 'v4', credentials=credentials)
            # Test the service by trying to access the spreadsheets API
            self.service.spreadsheets().get(spreadsheetId='dummy').execute()
        except Exception as e:
            if 'Invalid spreadsheet ID' in str(e):
                # This is expected - it means the service is working
                logger.info("Sheets handler initialized successfully")
            else:
                logger.error(f"Error initializing sheets handler: {str(e)}")
                raise Exception(f"Failed to initialize sheets handler: {str(e)}")
        
    def verify_initialization(self) -> bool:
        """Verify that the handler is properly initialized"""
        try:
            # Try to access the API
            self.service.spreadsheets().get(spreadsheetId='dummy').execute()
            return True
        except Exception as e:
            if 'Invalid spreadsheet ID' in str(e):
                # This is expected - it means the service is working
                return True
            logger.error(f"Sheets handler verification failed: {str(e)}")
            return False
    
    def create_spreadsheet(self, title: str) -> Optional[str]:
        """
        Create a new Google Sheets spreadsheet
        Args:
            title: Title of the spreadsheet
        Returns:
            str: Spreadsheet ID if successful, None otherwise
        """
        try:
            if not self.verify_initialization():
                raise Exception("Sheets handler is not properly initialized")
                
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

    def create_sheet(self, spreadsheet_id: str, sheet_name: str) -> bool:
        """Create a new sheet in the spreadsheet"""
        try:
            # Check if sheet already exists
            sheet_metadata = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheets = sheet_metadata.get('sheets', [])
            for sheet in sheets:
                if sheet['properties']['title'] == sheet_name:
                    return True  # Sheet already exists
            
            # Create new sheet
            body = {
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': sheet_name
                        }
                    }
                }]
            }
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating sheet {sheet_name}: {str(e)}")
            return False

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
                if sheet_id is None:
                    logger.error(f"Failed to create sheet: {sheet_name}")
                    return False
            
            # Get the last row in the sheet
            range_name = f"{sheet_name}!A:A"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            last_row = len(result.get('values', [])) + 1
            
            # Add spacing if not first entry
            if last_row > 1:
                last_row += 3  # Add extra spacing between file entries
            
            # Prepare the header rows
            header = [
                [file_name],  # File name row
                ["Date", "Description", "Amount", "Category"]  # Column headers
            ]
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
            
            # Add empty rows after data
            empty_rows = [[""] * 4] * 3
            
            # Prepare all formatting requests
            requests = []
            
            # Format file name row with pastel green background
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
                                    'bold': True,
                                    'fontSize': 12
                                },
                                'horizontalAlignment': 'LEFT',
                                'verticalAlignment': 'MIDDLE'
                            }
                        }]
                    }],
                    'fields': 'userEnteredFormat',
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': last_row - 1,
                        'endRowIndex': last_row,
                        'startColumnIndex': 0,
                        'endColumnIndex': 4
                    }
                }
            })
            
            # Format column headers
            requests.append({
                'updateCells': {
                    'rows': [{
                        'values': [
                            {'userEnteredFormat': {'textFormat': {'bold': True}}} for _ in range(4)
                        ]
                    }],
                    'fields': 'userEnteredFormat',
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': last_row,
                        'endRowIndex': last_row + 1,
                        'startColumnIndex': 0,
                        'endColumnIndex': 4
                    }
                }
            })
            
            # Format empty rows with light background
            if data:  # Only if we have data
                requests.append({
                    'updateCells': {
                        'rows': [{
                            'values': [{
                                'userEnteredFormat': {
                                    'backgroundColor': {
                                        'red': 0.95,
                                        'green': 0.95,
                                        'blue': 0.95
                                    }
                                }
                            } for _ in range(4)]
                        } for _ in range(3)],  # 3 empty rows
                        'fields': 'userEnteredFormat',
                        'range': {
                            'sheetId': sheet_id,
                            'startRowIndex': last_row + len(header) + len(data),
                            'endRowIndex': last_row + len(header) + len(data) + 3,
                            'startColumnIndex': 0,
                            'endColumnIndex': 4
                        }
                    }
                })
            
            # Auto-resize columns
            requests.append({
                'autoResizeDimensions': {
                    'dimensions': {
                        'sheetId': sheet_id,
                        'dimension': 'COLUMNS',
                        'startIndex': 0,
                        'endIndex': 4
                    }
                }
            })
            
            # Write the data
            body = {
                'values': header + data + empty_rows
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

    def write_transactions_with_formatting(self, spreadsheet_id: str, sheet_name: str, transactions: list) -> bool:
        """Write transactions to sheet with formatting"""
        try:
            if not transactions:
                return True
            
            # Group transactions by source file
            transactions_by_file = {}
            for trans in transactions:
                source_file = trans.get('Source File', 'Unknown')
                if source_file not in transactions_by_file:
                    transactions_by_file[source_file] = []
                transactions_by_file[source_file].append(trans)
            
            # Prepare header row
            headers = [
                'Date', 'Description', 'Amount', 'Type', 'Category',
                'Card Number', 'Bank Name', 'Card Type', 'Source File'
            ]
            
            # Get sheet ID
            sheet_metadata = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheet_id = None
            for sheet in sheet_metadata.get('sheets', []):
                if sheet['properties']['title'] == sheet_name:
                    sheet_id = sheet['properties']['sheetId']
                    break
            
            if not sheet_id:
                logger.error(f"Sheet {sheet_name} not found")
                return False
            
            # Clear existing content
            range_name = f"{sheet_name}!A1:Z"
            self.service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            # Write headers
            header_range = f"{sheet_name}!A1:I1"
            self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=header_range,
                valueInputOption='RAW',
                body={'values': [headers]}
            ).execute()
            
            # Format headers
            header_format = {
                'requests': [{
                    'repeatCell': {
                        'range': {
                            'sheetId': sheet_id,
                            'startRowIndex': 0,
                            'endRowIndex': 1,
                            'startColumnIndex': 0,
                            'endColumnIndex': len(headers)
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'backgroundColor': {'red': 0.8, 'green': 0.8, 'blue': 0.8},
                                'textFormat': {'bold': True},
                                'horizontalAlignment': 'CENTER'
                            }
                        },
                        'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
                    }
                }]
            }
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=header_format
            ).execute()
            
            # Write transactions file by file
            current_row = 2  # Start after header
            
            for source_file, file_transactions in transactions_by_file.items():
                # Write file name with pastel green background
                file_range = f"{sheet_name}!A{current_row}"
                self.service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=file_range,
                    valueInputOption='RAW',
                    body={'values': [[source_file]]}
                ).execute()
                
                # Format file name row
                file_format = {
                    'requests': [{
                        'repeatCell': {
                            'range': {
                                'sheetId': sheet_id,
                                'startRowIndex': current_row - 1,
                                'endRowIndex': current_row,
                                'startColumnIndex': 0,
                                'endColumnIndex': len(headers)
                            },
                            'cell': {
                                'userEnteredFormat': {
                                    'backgroundColor': {'red': 0.9, 'green': 1.0, 'blue': 0.9},
                                    'textFormat': {'bold': True},
                                    'horizontalAlignment': 'LEFT'
                                }
                            },
                            'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
                        }
                    }]
                }
                
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=file_format
                ).execute()
                
                current_row += 1
                
                # Write transactions
                values = []
                for trans in file_transactions:
                    values.append([
                        trans.get('Date', ''),
                        trans.get('Description', ''),
                        trans.get('Amount', ''),
                        trans.get('Type', ''),
                        trans.get('Category', ''),
                        trans.get('Card Number', ''),
                        trans.get('Bank Name', ''),
                        trans.get('Card Type', ''),
                        trans.get('Source File', '')
                    ])
                
                if values:
                    data_range = f"{sheet_name}!A{current_row}:I{current_row + len(values) - 1}"
                    self.service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range=data_range,
                        valueInputOption='RAW',
                        body={'values': values}
                    ).execute()
                    
                    current_row += len(values)
                
                # Add spacing rows with light background
                for _ in range(3):
                    spacing_format = {
                        'requests': [{
                            'repeatCell': {
                                'range': {
                                    'sheetId': sheet_id,
                                    'startRowIndex': current_row - 1,
                                    'endRowIndex': current_row,
                                    'startColumnIndex': 0,
                                    'endColumnIndex': len(headers)
                                },
                                'cell': {
                                    'userEnteredFormat': {
                                        'backgroundColor': {'red': 0.95, 'green': 1.0, 'blue': 0.95}
                                    }
                                },
                                'fields': 'userEnteredFormat(backgroundColor)'
                            }
                        }]
                    }
                    
                    self.service.spreadsheets().batchUpdate(
                        spreadsheetId=spreadsheet_id,
                        body=spacing_format
                    ).execute()
                    
                    current_row += 1
            
            # Auto-resize columns
            auto_resize = {
                'requests': [{
                    'autoResizeDimensions': {
                        'dimensions': {
                            'sheetId': sheet_id,
                            'dimension': 'COLUMNS',
                            'startIndex': 0,
                            'endIndex': len(headers)
                        }
                    }
                }]
            }
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=auto_resize
            ).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Error writing transactions to sheet: {str(e)}")
            return False 