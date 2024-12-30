import os
import argparse
from utils.encryption import Encryptor
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def decrypt_folder(folder_path: str, encryption_key: str, output_folder: str):
    """
    Decrypt all encrypted files in a folder
    Args:
        folder_path: Path to folder containing encrypted files
        encryption_key: Base64 encoded encryption key
        output_folder: Path to folder where decrypted files will be saved
    """
    try:
        # Create output folder if it doesn't exist
        os.makedirs(output_folder, exist_ok=True)
        
        # Initialize encryptor
        encryptor = Encryptor(encryption_key)
        
        # Get all encrypted files and their IVs
        encrypted_files = {}
        for filename in os.listdir(folder_path):
            if filename.startswith('encrypted_'):
                base_name = filename[len('encrypted_'):]
                iv_file = f'iv_{base_name}.bin'
                if os.path.exists(os.path.join(folder_path, iv_file)):
                    encrypted_files[filename] = iv_file

        if not encrypted_files:
            logger.warning("No encrypted files found in the specified folder")
            return

        # Process each file
        for enc_file, iv_file in encrypted_files.items():
            try:
                # Read encrypted file
                with open(os.path.join(folder_path, enc_file), 'rb') as f:
                    encrypted_data = f.read()

                # Read IV
                with open(os.path.join(folder_path, iv_file), 'rb') as f:
                    iv = f.read()

                # Decrypt
                decrypted_data = encryptor.decrypt_file(encrypted_data, iv)

                # Save decrypted file
                output_filename = enc_file[len('encrypted_'):]
                output_path = os.path.join(output_folder, output_filename)
                
                with open(output_path, 'wb') as f:
                    f.write(decrypted_data)
                
                logger.info(f"Successfully decrypted: {output_filename}")

            except Exception as e:
                logger.error(f"Error decrypting {enc_file}: {str(e)}")
                continue

    except Exception as e:
        logger.error(f"Error processing folder: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Decrypt files downloaded from Gmail PDF Scraper')
    parser.add_argument('folder_path', help='Path to folder containing encrypted files')
    parser.add_argument('encryption_key', help='Base64 encoded encryption key')
    parser.add_argument('--output', '-o', default='decrypted_files',
                      help='Output folder for decrypted files (default: decrypted_files)')

    args = parser.parse_args()

    decrypt_folder(args.folder_path, args.encryption_key, args.output)

if __name__ == '__main__':
    main() 