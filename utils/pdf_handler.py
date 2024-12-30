import PyPDF2
import logging
from typing import Tuple

# Get module logger
logger = logging.getLogger(__name__)

class PdfHandler:
    def __init__(self):
        """Initialize PDF handler"""
        self.password_cache = {}
        logger.info("PDF handler initialized")
    
    def clear_password_cache(self):
        """Clear the password cache"""
        self.password_cache = {}
        logger.info("Password cache cleared")
    
    def process_pdf(self, file_data: bytes, keyword: str, password: str = None) -> Tuple[bytes, bool]:
        """
        Process a PDF file
        Args:
            file_data: PDF file data
            keyword: Search keyword
            password: PDF password if required
        Returns:
            Tuple[bytes, bool]: (Processed file data, needs_password flag)
        """
        try:
            if not file_data:
                logger.error("Empty file data received")
                return None, False
            
            # Try to open PDF
            pdf_reader = PyPDF2.PdfReader(file_data)
            
            # Check if PDF is valid
            if not pdf_reader.pages or len(pdf_reader.pages) == 0:
                logger.error("Invalid PDF file - no pages found")
                return None, False
            
            # Check if PDF is encrypted
            if pdf_reader.is_encrypted:
                if not password:
                    logger.info("PDF is encrypted but no password provided")
                    return None, True
                
                try:
                    # Try to decrypt with provided password
                    if not pdf_reader.decrypt(password):
                        logger.warning("Incorrect password provided for PDF")
                        return None, True
                except Exception as e:
                    logger.error(f"Error decrypting PDF: {str(e)}")
                    return None, True
            
            # Verify file is readable
            try:
                # Try to read first page to verify PDF is valid
                _ = pdf_reader.pages[0].extract_text()
            except Exception as e:
                logger.error(f"Error reading PDF content: {str(e)}")
                return None, False
            
            # Return original file data since we don't need to modify it
            return file_data, False
            
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            return None, False 