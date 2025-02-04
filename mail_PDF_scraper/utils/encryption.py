from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
import base64
import os
from typing import Tuple, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Encryptor:
    def __init__(self, key: Optional[str] = None):
        """
        Initialize encryptor with a key
        Args:
            key: Base64 encoded 32-byte key, if None a new one will be generated
        """
        if key:
            self.key = base64.b64decode(key)
        else:
            self.key = get_random_bytes(32)

    def get_key(self) -> str:
        """
        Get the base64 encoded encryption key
        Returns:
            Base64 encoded key
        """
        return base64.b64encode(self.key).decode('utf-8')

    def encrypt_file(self, file_data: bytes) -> Tuple[bytes, bytes]:
        """
        Encrypt file data using AES-256-CBC
        Args:
            file_data: Raw file data to encrypt
        Returns:
            Tuple of (encrypted data, IV)
        """
        try:
            iv = get_random_bytes(AES.block_size)
            cipher = AES.new(self.key, AES.MODE_CBC, iv)
            
            # Pad the data to be a multiple of 16 bytes
            padded_data = pad(file_data, AES.block_size)
            
            # Encrypt the padded data
            encrypted_data = cipher.encrypt(padded_data)
            
            return encrypted_data, iv
        except Exception as e:
            logger.error(f"Encryption error: {str(e)}")
            raise

    def decrypt_file(self, encrypted_data: bytes, iv: bytes) -> bytes:
        """
        Decrypt file data using AES-256-CBC
        Args:
            encrypted_data: Encrypted file data
            iv: Initialization vector used for encryption
        Returns:
            Decrypted file data
        """
        try:
            cipher = AES.new(self.key, AES.MODE_CBC, iv)
            
            # Decrypt the data
            padded_data = cipher.decrypt(encrypted_data)
            
            # Remove padding
            original_data = unpad(padded_data, AES.block_size)
            
            return original_data
        except Exception as e:
            logger.error(f"Decryption error: {str(e)}")
            raise

    @staticmethod
    def generate_key() -> str:
        """
        Generate a new random encryption key
        Returns:
            Base64 encoded key
        """
        key = get_random_bytes(32)
        return base64.b64encode(key).decode('utf-8') 