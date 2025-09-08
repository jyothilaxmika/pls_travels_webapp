#!/usr/bin/env python3
"""
Storage Integration Layer for PLS TRAVELS
Integrates the new organized storage system with existing Flask routes
"""

from flask import request, current_app
from werkzeug.datastructures import FileStorage
from typing import Optional, Dict, List
import json

from app_storage import app_storage
from utils_main import process_file_upload, process_camera_capture

class StorageIntegration:
    """Integration layer between Flask routes and the organized storage system"""
    
    @staticmethod
    def handle_document_upload(file: FileStorage, user_id: int, document_type: str, 
                             additional_metadata: Dict = None) -> Optional[str]:
        """
        Handle document upload through the new storage system
        
        Args:
            file: Flask FileStorage object
            user_id: ID of the user uploading
            document_type: Type of document (aadhar, license, profile, etc.)
            additional_metadata: Extra metadata to store
            
        Returns:
            Filename if successful, None if failed
        """
        metadata = additional_metadata or {}
        metadata.update({
            'upload_source': 'web_form',
            'ip_address': request.remote_addr if request else None,
            'user_agent': request.headers.get('User-Agent') if request else None
        })
        
        result = app_storage.save_uploaded_file(file, user_id, document_type, metadata)
        
        if result:
            return result['stored_filename']
        return None
    
    @staticmethod
    def handle_camera_capture(image_data: str, user_id: int, capture_type: str,
                            location_data: Dict = None) -> Optional[str]:
        """
        Handle camera capture through the new storage system
        
        Args:
            image_data: Base64 encoded image
            user_id: ID of the user capturing
            capture_type: Type of capture (camera_aadhar, camera_license, etc.)
            location_data: GPS/location metadata
            
        Returns:
            Filename if successful, None if failed
        """
        metadata = {
            'capture_source': 'mobile_camera',
            'ip_address': request.remote_addr if request else None,
            'user_agent': request.headers.get('User-Agent') if request else None
        }
        
        if location_data:
            metadata['location'] = location_data
            
        result = app_storage.save_camera_capture(image_data, user_id, capture_type, metadata)
        
        if result:
            return result['stored_filename']
        return None
    
    @staticmethod
    def get_user_documents(user_id: int, document_type: str = None) -> List[Dict]:
        """Get all documents for a user"""
        return app_storage.get_user_files(user_id, document_type)
    
    @staticmethod
    def delete_document(filename: str, document_type: str) -> bool:
        """Delete a document"""
        # Determine category from document type
        category = 'documents' if document_type in ['aadhar', 'license', 'bank'] else 'photos'
        if 'camera_' in document_type:
            category = 'captures'
            
        return app_storage.delete_file(filename, category)
    
    @staticmethod
    def get_document_metadata(filename: str, document_type: str) -> Optional[Dict]:
        """Get metadata for a specific document"""
        category = 'documents' if document_type in ['aadhar', 'license', 'bank'] else 'photos'
        if 'camera_' in document_type:
            category = 'captures'
            
        return app_storage.get_file_metadata(filename, category)
    
    @staticmethod
    def process_duty_photos(form_data, user_id: int, duty_type: str) -> Dict[str, Optional[str]]:
        """
        Process duty start/end photos from form data
        
        Args:
            form_data: Flask request.form
            user_id: User ID
            duty_type: 'start' or 'end'
            
        Returns:
            Dict with photo filenames or None values
        """
        results = {
            'uploaded_photo': None,
            'captured_photo': None
        }
        
        # Handle traditional file upload
        photo_field = f'{duty_type}_photo'
        if photo_field in request.files:
            file = request.files[photo_field]
            if file and file.filename:
                results['uploaded_photo'] = StorageIntegration.handle_document_upload(
                    file, user_id, f'duty_{duty_type}'
                )
        
        # Handle camera capture
        capture_data_field = f'{photo_field}_data'
        if capture_data_field in form_data:
            image_data = form_data[capture_data_field]
            if image_data:
                # Extract location metadata if available
                location_data = None
                location_field = f'{photo_field}_metadata'
                if location_field in form_data:
                    try:
                        location_data = json.loads(form_data[location_field])
                    except json.JSONDecodeError:
                        pass
                
                results['captured_photo'] = StorageIntegration.handle_camera_capture(
                    image_data, user_id, f'camera_duty_{duty_type}', location_data
                )
        
        return results
    
    @staticmethod
    def process_driver_documents(form_data, files_data, user_id: int) -> Dict[str, Optional[str]]:
        """
        Process driver document uploads (profile, registration, etc.)
        
        Args:
            form_data: Flask request.form
            files_data: Flask request.files
            user_id: User ID
            
        Returns:
            Dict with document filenames
        """
        results = {
            'aadhar_document': None,
            'license_document': None,
            'profile_photo': None
        }
        
        document_types = ['aadhar', 'license', 'profile']
        
        for doc_type in document_types:
            # Handle file upload
            if f'{doc_type}_photo' in files_data:
                file = files_data[f'{doc_type}_photo']
                if file and file.filename:
                    results[f'{doc_type}_document'] = StorageIntegration.handle_document_upload(
                        file, user_id, doc_type
                    )
            
            # Handle camera capture
            capture_field = f'{doc_type}_photo_data'
            if capture_field in form_data:
                image_data = form_data[capture_field]
                if image_data:
                    captured_filename = StorageIntegration.handle_camera_capture(
                        image_data, user_id, f'camera_{doc_type}'
                    )
                    if captured_filename:
                        results[f'{doc_type}_document'] = captured_filename
        
        return results
    
    @staticmethod
    def get_storage_statistics() -> Dict:
        """Get comprehensive storage statistics"""
        stats = app_storage.get_storage_stats()
        
        # Add human-readable sizes
        def format_bytes(bytes_size):
            for unit in ['B', 'KB', 'MB', 'GB']:
                if bytes_size < 1024.0:
                    return f"{bytes_size:.1f} {unit}"
                bytes_size /= 1024.0
            return f"{bytes_size:.1f} TB"
        
        stats['total_size_formatted'] = format_bytes(stats['total_size'])
        
        for category, category_stats in stats['categories'].items():
            category_stats['size_formatted'] = format_bytes(category_stats['size'])
            
            for subcategory, subcat_stats in category_stats['subcategories'].items():
                subcat_stats['size_formatted'] = format_bytes(subcat_stats['size'])
        
        return stats
    
    @staticmethod
    def cleanup_old_files(older_than_hours: int = 168):  # 1 week default
        """Cleanup temporary and old files"""
        app_storage.cleanup_temp_files(older_than_hours)
    
    @staticmethod
    def migrate_legacy_uploads():
        """Migrate files from old uploads directory"""
        from app_storage import migrate_existing_uploads
        migrate_existing_uploads()

# Helper functions for direct use in routes
def save_document(file: FileStorage, user_id: int, doc_type: str) -> Optional[str]:
    """Quick function to save a document"""
    return StorageIntegration.handle_document_upload(file, user_id, doc_type)

def save_capture(image_data: str, user_id: int, capture_type: str) -> Optional[str]:
    """Quick function to save a camera capture"""
    return StorageIntegration.handle_camera_capture(image_data, user_id, capture_type)

def get_user_files(user_id: int, file_type: str = None) -> List[Dict]:
    """Quick function to get user files"""
    return StorageIntegration.get_user_documents(user_id, file_type)

def delete_user_file(filename: str, file_type: str) -> bool:
    """Quick function to delete a user file"""
    return StorageIntegration.delete_document(filename, file_type)