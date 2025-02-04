import logging
import logging.handlers
import os
from datetime import datetime

def setup_logger():
    """Configure application-wide logging"""
    
    # Create logs directory if it doesn't exist
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # File handler for app.log
    log_file = os.path.join(log_dir, 'app.log')
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10485760,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add only file handler
    root_logger.addHandler(file_handler)
    
    # Set secure permissions for log directory and file
    os.chmod(log_dir, 0o750)
    os.chmod(log_file, 0o640)
    
    # Disable propagation to console
    root_logger.propagate = False
    
    return root_logger 