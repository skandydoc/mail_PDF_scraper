import os
import json
from datetime import datetime
import logging
import pytz

# Configure logging
logger = logging.getLogger(__name__)

class SecurityHandler:
    def __init__(self):
        """Initialize security handler"""
        self.audit_dir = 'audit_logs'
        self._ensure_audit_dir()
        
    def _ensure_audit_dir(self):
        """Ensure audit directory exists"""
        if not os.path.exists(self.audit_dir):
            os.makedirs(self.audit_dir)
            logger.info("Created audit logs directory")
    
    def _get_audit_file(self):
        """Get current day's audit file path"""
        today = datetime.now().strftime('%Y-%m-%d')
        return os.path.join(self.audit_dir, f'audit_log_{today}.json')
    
    def log_activity(self, user_email: str, activity_type: str, details: dict):
        """
        Log user activity
        Args:
            user_email: User's email address
            activity_type: Type of activity (e.g., 'file_upload', 'authentication')
            details: Dictionary containing activity details
        """
        try:
            audit_file = self._get_audit_file()
            
            # Read existing logs
            logs = []
            if os.path.exists(audit_file):
                with open(audit_file, 'r') as f:
                    logs = json.load(f)
            
            # Add new log entry
            log_entry = {
                'timestamp': datetime.now(pytz.UTC).isoformat(),
                'user_email': user_email,
                'activity_type': activity_type,
                'details': details
            }
            logs.append(log_entry)
            
            # Write updated logs
            with open(audit_file, 'w') as f:
                json.dump(logs, f, indent=2)
            
            logger.info(f"Activity logged: {activity_type}")
            
        except Exception as e:
            logger.error(f"Error logging activity: {str(e)}")
    
    def create_session(self, user_email: str) -> str:
        """
        Create a new session for user
        Args:
            user_email: User's email address
        Returns:
            str: Session identifier
        """
        session_id = datetime.now().strftime('%Y%m%d%H%M%S')
        self.log_activity(
            user_email,
            'session_created',
            {
                'session_id': session_id,
                'created_at': datetime.now(pytz.UTC).isoformat()
            }
        )
        return session_id 