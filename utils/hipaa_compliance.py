import logging
from datetime import datetime
import json
import os
from typing import Dict, Any, Optional
from jose import jwt
import secrets
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HipaaCompliance:
    def __init__(self, log_dir: str = "audit_logs"):
        """
        Initialize HIPAA compliance handler
        Args:
            log_dir: Directory for storing audit logs
        """
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # Define secure headers manually
        self.secure_headers = {
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'X-Frame-Options': 'SAMEORIGIN',
            'X-Content-Type-Options': 'nosniff',
            'X-XSS-Protection': '1; mode=block',
            'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';",
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
            'Pragma': 'no-cache'
        }
        
        # Session management
        self._sessions: Dict[str, Dict[str, Any]] = {}
        
        # Ensure session key file is secure
        self._initialize_session_key()
    
    def _initialize_session_key(self):
        """Initialize session key with proper permissions"""
        key_file = ".session.key"
        if not os.path.exists(key_file):
            key = secrets.token_hex(32)
            try:
                # Write key with restricted permissions
                with open(key_file, 'w') as f:
                    f.write(key)
                # Set file permissions to 600 (user read/write only)
                os.chmod(key_file, 0o600)
            except Exception as e:
                logger.error(f"Error creating session key: {str(e)}")
                raise
        
    def create_session(self, user_email: str) -> str:
        """
        Create a new session for a user
        Args:
            user_email: User's email address
        Returns:
            Session token
        """
        try:
            session_id = secrets.token_urlsafe(32)
            session_data = {
                'user_email': user_email,
                'created_at': datetime.utcnow().isoformat(),
                'last_activity': datetime.utcnow().isoformat(),
                'session_id': session_id
            }
            
            # Create signed session token
            session_token = jwt.encode(
                session_data,
                self._get_session_key(),
                algorithm='HS256'
            )
            
            self._sessions[session_id] = session_data
            return session_token
        except Exception as e:
            logger.error(f"Error creating session: {str(e)}")
            raise
    
    def validate_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """
        Validate a session token
        Args:
            session_token: Session token to validate
        Returns:
            Session data if valid, None otherwise
        """
        try:
            session_data = jwt.decode(
                session_token,
                self._get_session_key(),
                algorithms=['HS256']
            )
            
            # Check if session exists and is not expired (24 hours)
            session_id = session_data.get('session_id')
            if session_id in self._sessions:
                created_at = datetime.fromisoformat(session_data['created_at'])
                if (datetime.utcnow() - created_at).total_seconds() < 86400:  # 24 hours
                    return session_data
            
            return None
        except Exception as e:
            logger.error(f"Error validating session: {str(e)}")
            return None
    
    def log_activity(self, user_email: str, activity: str, details: Dict[str, Any]):
        """
        Log an activity for HIPAA compliance
        Args:
            user_email: User performing the activity
            activity: Type of activity
            details: Activity details
        """
        try:
            log_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'user_email': user_email,
                'activity': activity,
                'details': details
            }
            
            # Create daily log file
            log_file = os.path.join(
                self.log_dir,
                f"audit_log_{datetime.utcnow().strftime('%Y-%m-%d')}.json"
            )
            
            logs = []
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r') as f:
                        logs = json.load(f)
                except json.JSONDecodeError:
                    logger.warning(f"Corrupted log file {log_file}, starting new log")
            
            logs.append(log_entry)
            
            # Write with proper file permissions
            with open(log_file, 'w') as f:
                json.dump(logs, f, indent=2)
            
            # Set secure file permissions
            os.chmod(log_file, 0o600)
                
        except Exception as e:
            logger.error(f"Error writing to audit log: {str(e)}")
            # Continue execution even if logging fails
    
    def verify_data_integrity(self, data: bytes) -> str:
        """
        Verify data integrity using SHA-256
        Args:
            data: Data to verify
        Returns:
            SHA-256 hash of the data
        """
        try:
            return hashlib.sha256(data).hexdigest()
        except Exception as e:
            logger.error(f"Error calculating hash: {str(e)}")
            raise
    
    def _get_session_key(self) -> str:
        """Get or create session signing key"""
        try:
            key_file = ".session.key"
            if os.path.exists(key_file):
                with open(key_file, 'r') as f:
                    return f.read().strip()
            else:
                key = secrets.token_hex(32)
                with open(key_file, 'w') as f:
                    f.write(key)
                os.chmod(key_file, 0o600)
                return key
        except Exception as e:
            logger.error(f"Error accessing session key: {str(e)}")
            raise
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions (older than 24 hours)"""
        try:
            current_time = datetime.utcnow()
            expired_sessions = []
            
            for session_id, session_data in self._sessions.items():
                created_at = datetime.fromisoformat(session_data['created_at'])
                if (current_time - created_at).total_seconds() >= 86400:  # 24 hours
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                del self._sessions[session_id]
                
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {str(e)}")
            # Continue execution even if cleanup fails 