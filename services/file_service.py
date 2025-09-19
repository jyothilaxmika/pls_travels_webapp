"""
File Service

Handles file upload management, document processing, photo handling,
and secure file operations across the application.
"""

from typing import Optional, Dict, Any, Tuple
import logging
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app
from .audit_service import AuditService

logger = logging.getLogger(__name__)

class FileService:
    """Service class for file management operations"""
    
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
    MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
    
    def __init__(self):
        self.audit_service = AuditService()
    
    def allowed_file(self, filename: str) -> bool:
        """Check if file extension is allowed."""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.ALLOWED_EXTENSIONS
    
    def save_uploaded_file(self, file, prefix: str, entity_id: int, 
                          subfolder: str = 'documents') -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Save an uploaded file with secure naming and organization.
        
        Args:
            file: Flask uploaded file object
            prefix: Filename prefix (e.g., 'driver', 'vehicle')
            entity_id: ID of related entity
            subfolder: Subfolder for organization
            
        Returns:
            tuple: (success: bool, filename: str, error_message: str)
        """
        try:
            if not file or not file.filename:
                return False, None, "No file provided"
            
            if not self.allowed_file(file.filename):
                return False, None, f"File type not allowed. Allowed types: {', '.join(self.ALLOWED_EXTENSIONS)}"
            
            # Check file size
            file.seek(0, 2)  # Seek to end
            file_size = file.tell()
            file.seek(0)  # Seek back to start
            
            if file_size > self.MAX_FILE_SIZE:
                return False, None, f"File too large. Maximum size: {self.MAX_FILE_SIZE // (1024*1024)}MB"
            
            # Generate secure filename
            original_filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{prefix}_{entity_id}_{timestamp}_{original_filename}"
            
            # Ensure upload directory exists
            upload_folder = os.path.join(current_app.root_path, 'uploads', subfolder)
            os.makedirs(upload_folder, exist_ok=True)
            
            # Save file
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)
            
            # Log file upload
            self.audit_service.log_action(
                action='file_upload',
                entity_type='file',
                details={
                    'filename': filename,
                    'original_filename': original_filename,
                    'file_size': file_size,
                    'subfolder': subfolder,
                    'entity_id': entity_id
                }
            )
            
            logger.info(f"File uploaded successfully: {filename}")
            return True, filename, None
            
        except Exception as e:
            logger.error(f"Error saving uploaded file: {str(e)}")
            return False, None, f"Upload failed: {str(e)}"
    
    def process_camera_capture(self, form_data: Dict, field_name: str, 
                              entity_id: int, purpose: str) -> Tuple[Optional[str], Optional[Dict]]:
        """
        Process camera capture data and save as file.
        
        Args:
            form_data: Form data containing camera capture
            field_name: Name of the field containing capture data
            entity_id: ID of related entity
            purpose: Purpose of capture (e.g., 'duty_start', 'profile_photo')
            
        Returns:
            tuple: (filename: str, metadata: dict)
        """
        try:
            import base64
            
            # Get capture data and metadata
            capture_data = form_data.get(f'{field_name}_data')
            capture_metadata = form_data.get(f'{field_name}_metadata')
            
            if not capture_data:
                return None, None
            
            # Decode base64 image data
            if capture_data.startswith('data:image/'):
                header, data = capture_data.split(',', 1)
                file_ext = 'jpg'  # Default to jpg for camera captures
                
                # Extract format from header if available
                if 'jpeg' in header:
                    file_ext = 'jpg'
                elif 'png' in header:
                    file_ext = 'png'
                
                # Decode image
                image_data = base64.b64decode(data)
                
                # Generate filename
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"capture_{purpose}_{entity_id}_{timestamp}.{file_ext}"
                
                # Save to uploads/photos directory
                upload_folder = os.path.join(current_app.root_path, 'uploads', 'photos')
                os.makedirs(upload_folder, exist_ok=True)
                
                file_path = os.path.join(upload_folder, filename)
                with open(file_path, 'wb') as f:
                    f.write(image_data)
                
                # Process metadata if available
                metadata = None
                if capture_metadata:
                    try:
                        import json
                        metadata = json.loads(capture_metadata)
                    except:
                        metadata = {'raw_metadata': capture_metadata}
                
                # Log camera capture
                self.audit_service.log_action(
                    action='camera_capture',
                    entity_type='photo',
                    details={
                        'filename': filename,
                        'purpose': purpose,
                        'entity_id': entity_id,
                        'has_metadata': metadata is not None
                    }
                )
                
                logger.info(f"Camera capture processed: {filename}")
                return filename, metadata
                
        except Exception as e:
            logger.error(f"Error processing camera capture: {str(e)}")
            
        return None, None
    
    def delete_file(self, filename: str, subfolder: str = 'documents') -> bool:
        """
        Delete a file securely.
        
        Args:
            filename: Name of file to delete
            subfolder: Subfolder where file is stored
            
        Returns:
            bool: True if deletion successful
        """
        try:
            file_path = os.path.join(current_app.root_path, 'uploads', subfolder, filename)
            
            if os.path.exists(file_path):
                os.remove(file_path)
                
                # Log file deletion
                self.audit_service.log_action(
                    action='file_delete',
                    entity_type='file',
                    details={
                        'filename': filename,
                        'subfolder': subfolder
                    }
                )
                
                logger.info(f"File deleted: {filename}")
                return True
            else:
                logger.warning(f"File not found for deletion: {filename}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting file {filename}: {str(e)}")
            return False
    
    def get_file_info(self, filename: str, subfolder: str = 'documents') -> Optional[Dict[str, Any]]:
        """
        Get information about a file.
        
        Args:
            filename: Name of file
            subfolder: Subfolder where file is stored
            
        Returns:
            dict: File information or None if not found
        """
        try:
            file_path = os.path.join(current_app.root_path, 'uploads', subfolder, filename)
            
            if os.path.exists(file_path):
                stat_info = os.stat(file_path)
                
                return {
                    'filename': filename,
                    'size': stat_info.st_size,
                    'modified': datetime.fromtimestamp(stat_info.st_mtime),
                    'path': file_path,
                    'subfolder': subfolder
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting file info for {filename}: {str(e)}")
            return None