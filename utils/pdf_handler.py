from PyPDF2 import PdfReader, PdfWriter
import logging
import hashlib
from typing import Optional, Dict, Tuple
import io

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PdfHandler:
    def __init__(self):
        self._password_cache: Dict[str, str] = {}
        
    def process_pdf(self, pdf_data: bytes, keyword: str, password: Optional[str] = None) -> Tuple[bytes, bool]:
        """
        Process a PDF file, handling password protection if present
        Args:
            pdf_data: Raw PDF file data
            keyword: Search keyword associated with this PDF (for password caching)
            password: PDF password if known
        Returns:
            Tuple of (processed PDF data, whether password was needed)
        """
        try:
            # Create PDF reader from bytes
            pdf_file = io.BytesIO(pdf_data)
            reader = PdfReader(pdf_file)
            
            # Check if PDF is encrypted
            if reader.is_encrypted:
                # Try cached password for the keyword
                if not password and keyword in self._password_cache:
                    password = self._password_cache[keyword]
                
                if not password:
                    return pdf_data, True  # Need password from user
                
                try:
                    # Try to decrypt with provided password
                    reader.decrypt(password)
                    # Cache successful password
                    self._password_cache[keyword] = password
                except:
                    return pdf_data, True  # Wrong password
            
            # Create new PDF without encryption
            writer = PdfWriter()
            
            # Copy all pages to new PDF
            for page in reader.pages:
                writer.add_page(page)
            
            # Save to bytes
            output = io.BytesIO()
            writer.write(output)
            return output.getvalue(), False
            
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            raise

    def clear_password_cache(self):
        """Clear the password cache"""
        self._password_cache.clear()

    @staticmethod
    def verify_pdf_integrity(pdf_data: bytes) -> str:
        """
        Calculate SHA-256 hash of PDF data for integrity verification
        Args:
            pdf_data: PDF file data
        Returns:
            SHA-256 hash of the PDF
        """
        return hashlib.sha256(pdf_data).hexdigest() 