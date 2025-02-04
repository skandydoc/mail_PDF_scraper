import PyPDF2
import logging
from typing import Tuple, List, Optional, Dict, Any
from io import BytesIO
import time
import re
from datetime import datetime

# Get module logger
logger = logging.getLogger(__name__)

class PdfHandler:
    def __init__(self):
        """Initialize PDF handler"""
        self.password_cache = {}
        self.group_passwords = {}  # Cache for group-wise passwords
        self.format_cache = {}  # Cache for password formats by sender/group
        logger.info("PDF handler initialized")
    
    def clear_password_cache(self):
        """Clear all password caches"""
        self.password_cache = {}
        self.group_passwords = {}
        self.format_cache = {}
        logger.info("Password caches cleared")
    
    def _create_pdf_reader(self, file_data: bytes) -> PyPDF2.PdfReader:
        """Create a fresh PDF reader instance"""
        try:
            return PyPDF2.PdfReader(BytesIO(file_data))
        except Exception as e:
            logger.error(f"Error creating PDF reader: {str(e)}")
            raise
    
    def _try_decrypt_with_password(self, pdf_reader: PyPDF2.PdfReader, password: str) -> bool:
        """Try to decrypt PDF with a single password"""
        try:
            if not pdf_reader.is_encrypted:
                return True
            
            if pdf_reader.decrypt(password):
                # Verify we can actually read the content
                _ = pdf_reader.pages[0].extract_text()
                return True
            return False
        except Exception as e:
            logger.debug(f"Decryption attempt failed: {str(e)}")
            return False
    
    def _extract_password_format(self, email_body: str) -> Optional[str]:
        """Extract password format information from email body"""
        # Common patterns for password format descriptions
        patterns = [
            r"password.*?(?:is|:).*?(?:date of birth|DOB).*?(?:format|in).*?(\w+)",
            r"password.*?(?:is|:).*?last (\d+) digits",
            r"password.*?(?:is|:).*?first (\d+) digits",
            r"password format.*?(\w+)",
            r"password.*?in.*?(\w+).*?format",
            r"format.*?(\w+).*?(?:for password|as password)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, email_body.lower())
            if match:
                return match.group(1)
        return None
    
    def _generate_variants_from_format(self, password: str, format_hint: Optional[str]) -> List[str]:
        """Generate password variants based on format hint"""
        variants = [password]  # Always try the original password first
        
        if not format_hint:
            return variants
            
        format_hint = format_hint.lower()
        
        # Handle different format types
        if "dob" in format_hint or "date of birth" in format_hint:
            # Try common date formats
            clean_pass = password.replace("/", "").replace("-", "").strip()
            if len(clean_pass) == 8:
                variants.extend([
                    clean_pass,  # DDMMYYYY
                    f"{clean_pass[4:]}{clean_pass[2:4]}{clean_pass[:2]}",  # YYYYMMDD
                    f"{clean_pass[:4]}{clean_pass[4:6]}{clean_pass[6:]}",  # MMDDYYYY
                ])
        elif "last" in format_hint and any(d.isdigit() for d in format_hint):
            # Extract number of digits
            num_digits = int(''.join(filter(str.isdigit, format_hint)))
            if len(password) >= num_digits:
                variants.append(password[-num_digits:])
        elif "first" in format_hint and any(d.isdigit() for d in format_hint):
            # Extract number of digits
            num_digits = int(''.join(filter(str.isdigit, format_hint)))
            if len(password) >= num_digits:
                variants.append(password[:num_digits])
        
        # Add basic variants
        variants.extend([
            password.strip(),
            password.replace(" ", ""),
            ''.join(filter(str.isdigit, password))
        ])
        
        return list(set(variants))  # Remove duplicates

    def _extract_transactions(self, pdf_reader: PyPDF2.PdfReader) -> List[Dict[str, Any]]:
        """
        Extract transactions from a PDF file
        Args:
            pdf_reader: PyPDF2.PdfReader instance
        Returns:
            List[Dict[str, Any]]: List of transaction dictionaries
        """
        transactions = []
        
        try:
            # Extract text from all pages
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            
            # Common patterns for credit card statements
            date_pattern = r'(\d{2}/\d{2}/\d{2,4}|\d{2}-\d{2}-\d{2,4})'
            amount_pattern = r'(?:Rs\.|INR|₹)\s*(\d+(?:,\d+)*(?:\.\d{2})?)'
            
            # Split text into lines
            lines = text.split('\n')
            
            for line in lines:
                # Skip empty lines
                if not line.strip():
                    continue
                
                # Try to extract date
                date_match = re.search(date_pattern, line)
                if not date_match:
                    continue
                
                # Try to extract amount
                amount_match = re.search(amount_pattern, line)
                if not amount_match:
                    continue
                
                # Extract description (text between date and amount)
                date_end = date_match.end()
                amount_start = amount_match.start()
                description = line[date_end:amount_start].strip()
                
                # Skip if description is empty
                if not description:
                    continue
                
                # Create transaction dictionary
                transaction = {
                    'date': date_match.group(1),
                    'description': description,
                    'amount': amount_match.group(1).replace(',', ''),
                    'category': ''  # Can be enhanced with categorization logic
                }
                
                transactions.append(transaction)
        
        except Exception as e:
            logger.error(f"Error extracting transactions: {str(e)}")
        
        return transactions
    
    def process_pdf(self, file_data: bytes, group_key: str, passwords: List[str] = None, email_body: Optional[str] = None) -> Tuple[bytes, bool, str, List[Dict[str, Any]]]:
        """
        Process a PDF file with improved group-wise password handling and transaction extraction
        Args:
            file_data: PDF file data
            group_key: Key to identify the group for password caching
            passwords: List of passwords to try
            email_body: Optional email body text for password format hints
        Returns:
            Tuple[bytes, bool, str, List[Dict]]: (Processed file data, needs_password flag, error message, transactions)
        """
        try:
            if not file_data:
                return None, False, "Empty file data received", []

            # Create PDF reader
            try:
                pdf_reader = self._create_pdf_reader(file_data)
            except Exception as e:
                return None, False, f"Error opening PDF: {str(e)}", []

            transactions = []
            output_pdf = None

            # If not encrypted, extract transactions and return as is
            if not pdf_reader.is_encrypted:
                transactions = self._extract_transactions(pdf_reader)
                return file_data, False, "", transactions

            # Try group password first if available
            if group_key in self.group_passwords:
                group_password = self.group_passwords[group_key]
                logger.info(f"Trying cached group password for {group_key}")
                if self._try_decrypt_with_password(pdf_reader, group_password):
                    logger.info("Successfully decrypted with group password")
                    transactions = self._extract_transactions(pdf_reader)
                    
                    # Create unencrypted PDF
                    output = BytesIO()
                    writer = PyPDF2.PdfWriter()
                    for page in pdf_reader.pages:
                        writer.add_page(page)
                    writer.write(output)
                    output_pdf = output.getvalue()
                    
                    return output_pdf, False, "", transactions

            # If no passwords provided
            if not passwords:
                return None, True, "Password required", []

            # Try each password
            for password in passwords:
                if not password.strip():
                    continue

                # Try original password
                pdf_reader = self._create_pdf_reader(file_data)  # Fresh reader for each attempt
                if self._try_decrypt_with_password(pdf_reader, password):
                    logger.info(f"Found working password")
                    self.group_passwords[group_key] = password  # Cache for group
                    transactions = self._extract_transactions(pdf_reader)
                    
                    # Create unencrypted PDF
                    output = BytesIO()
                    writer = PyPDF2.PdfWriter()
                    for page in pdf_reader.pages:
                        writer.add_page(page)
                    writer.write(output)
                    output_pdf = output.getvalue()
                    
                    return output_pdf, False, "", transactions

                # Generate and try variants
                variants = self._generate_variants_from_format(password, self._extract_password_format(email_body) if email_body else None)
                for variant in variants:
                    pdf_reader = self._create_pdf_reader(file_data)  # Fresh reader for each attempt
                    if self._try_decrypt_with_password(pdf_reader, variant):
                        logger.info(f"Found working password variant")
                        self.group_passwords[group_key] = variant  # Cache for group
                        transactions = self._extract_transactions(pdf_reader)
                        
                        # Create unencrypted PDF
                        output = BytesIO()
                        writer = PyPDF2.PdfWriter()
                        for page in pdf_reader.pages:
                            writer.add_page(page)
                        writer.write(output)
                        output_pdf = output.getvalue()
                        
                        return output_pdf, False, "", transactions

                time.sleep(0.1)  # Small delay between attempts

            return None, True, "File has not been decrypted", []

        except Exception as e:
            error_msg = f"Error processing PDF: {str(e)}"
            logger.error(error_msg)
            return None, False, error_msg, []
    
    def find_working_password(self, file_data: bytes, passwords: List[str], email_body: Optional[str] = None) -> Optional[str]:
        """
        Find a working password for a PDF file
        Args:
            file_data: PDF file data
            passwords: List of passwords to try
            email_body: Optional email body text for password format hints
        Returns:
            str: Working password if found, None otherwise
        """
        try:
            pdf_reader = self._create_pdf_reader(file_data)
            if not pdf_reader.is_encrypted:
                return None

            for password in passwords:
                if not password.strip():
                    continue

                # Try original password
                if self._try_decrypt_with_password(pdf_reader, password):
                    logger.info(f"Found working password: {password}")
                    return password

                # Generate and try variants
                variants = self._generate_variants_from_format(password, self._extract_password_format(email_body) if email_body else None)
                for variant in variants:
                    pdf_reader = self._create_pdf_reader(file_data)  # Fresh reader
                    if self._try_decrypt_with_password(pdf_reader, variant):
                        logger.info(f"Found working password variant: {variant}")
                        return variant

                time.sleep(0.1)  # Small delay between attempts

            return None

        except Exception as e:
            logger.error(f"Error finding working password: {str(e)}")
            return None 