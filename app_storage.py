#!/usr/bin/env python3
"""
PLS TRAVELS - Comprehensive App Storage System
Handles uploaded documents and captured photos with organized storage structure
"""

import os
import json
import uuid
import base64
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

class AppStorageManager:
    """
    Comprehensive storage manager for PLS TRAVELS application
    Handles both uploaded documents and captured photos with metadata
    """
    
    def __init__(self, base_path: str = "app_storage"):
        self.base_path = Path(base_path)
        self.setup_storage_structure()
        
        # Storage categories with their respective folders
        self.storage_categories = {
            'documents': {
                'aadhar': 'documents/identity/aadhar',
                'license': 'documents/identity/license', 
                'bank': 'documents/financial/bank',
                'insurance': 'documents/financial/insurance',
                'contracts': 'documents/legal/contracts'
            },
            'photos': {
                'profile': 'photos/profiles',
                'vehicle': 'photos/vehicles',
                'duty_start': 'photos/duty/start',
                'duty_end': 'photos/duty/end',
                'maintenance': 'photos/maintenance',
                'incident': 'photos/incidents'
            },
            'captures': {
                'camera_aadhar': 'captures/identity/aadhar',
                'camera_license': 'captures/identity/license',
                'camera_profile': 'captures/profiles',
                'camera_duty': 'captures/duty',
                'camera_vehicle': 'captures/vehicles'
            },
            'assets': {
                'logos': 'assets/logos',
                'templates': 'assets/templates',
                'reports': 'assets/reports',
                'exports': 'assets/exports'
            }
        }
        
        # Allowed file extensions by category
        self.allowed_extensions = {
            'documents': {'pdf', 'jpg', 'jpeg', 'png'},
            'photos': {'jpg', 'jpeg', 'png', 'webp'},
            'captures': {'jpg', 'jpeg', 'png', 'webp'},
            'assets': {'pdf', 'jpg', 'jpeg', 'png', 'csv', 'xlsx', 'docx'}
        }
    
    def setup_storage_structure(self):
        """Create the organized directory structure"""
        directories = [
            # Document storage
            'documents/identity/aadhar',
            'documents/identity/license',
            'documents/financial/bank',
            'documents/financial/insurance', 
            'documents/legal/contracts',
            
            # Photo storage
            'photos/profiles',
            'photos/vehicles',
            'photos/duty/start',
            'photos/duty/end',
            'photos/maintenance',
            'photos/incidents',
            
            # Camera captures
            'captures/identity/aadhar',
            'captures/identity/license',
            'captures/profiles',
            'captures/duty',
            'captures/vehicles',
            
            # Assets
            'assets/logos',
            'assets/templates',
            'assets/reports',
            'assets/exports',
            
            # Metadata storage
            'metadata/documents',
            'metadata/photos',
            'metadata/captures',
            
            # Temporary storage
            'temp/uploads',
            'temp/processing'
        ]
        
        for directory in directories:
            dir_path = self.base_path / directory
            dir_path.mkdir(parents=True, exist_ok=True)
            
            # Create .gitkeep file to ensure directory is tracked
            gitkeep_path = dir_path / '.gitkeep'
            if not gitkeep_path.exists():
                gitkeep_path.touch()
    
    def get_storage_path(self, category: str, subcategory: str) -> Path:
        """Get the storage path for a specific category and subcategory"""
        if category in self.storage_categories and subcategory in self.storage_categories[category]:
            return self.base_path / self.storage_categories[category][subcategory]
        return self.base_path / 'temp' / 'uploads'
    
    def is_allowed_file(self, filename: str, category: str) -> bool:
        """Check if file extension is allowed for the category"""
        if not filename or '.' not in filename:
            return False
        
        extension = filename.rsplit('.', 1)[1].lower()
        allowed = self.allowed_extensions.get(category, set())
        return extension in allowed
    
    def generate_secure_filename(self, original_filename: str, user_id: int, 
                                file_type: str, prefix: str = '') -> str:
        """Generate a secure, unique filename"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4().hex)[:8]
        
        # Extract file extension
        if '.' in original_filename:
            extension = original_filename.rsplit('.', 1)[1].lower()
        else:
            extension = 'jpg'  # Default for captures
        
        # Build filename components
        components = []
        if prefix:
            components.append(prefix)
        components.extend([file_type, str(user_id), timestamp, unique_id])
        
        base_name = '_'.join(components)
        return secure_filename(f"{base_name}.{extension}")
    
    def save_uploaded_file(self, file: FileStorage, user_id: int, 
                          file_type: str, metadata: Dict = None) -> Optional[Dict]:
        """
        Save an uploaded file with proper organization and metadata
        
        Args:
            file: Flask FileStorage object
            user_id: User ID for organization
            file_type: Type of file (aadhar, license, profile, etc.)
            metadata: Additional metadata to store
            
        Returns:
            Dict with file info or None if failed
        """
        try:
            if not file or not file.filename:
                return None
            
            # Determine category and subcategory
            category = 'documents' if file_type in ['aadhar', 'license', 'bank'] else 'photos'
            
            if not self.is_allowed_file(file.filename, category):
                return None
            
            # Generate secure filename and path
            filename = self.generate_secure_filename(file.filename, user_id, file_type)
            storage_path = self.get_storage_path(category, file_type)
            file_path = storage_path / filename
            
            # Save the file
            file.save(str(file_path))
            
            # Create metadata
            file_metadata = {
                'original_filename': file.filename,
                'stored_filename': filename,
                'file_type': file_type,
                'category': category,
                'user_id': user_id,
                'file_size': file_path.stat().st_size,
                'uploaded_at': datetime.now().isoformat(),
                'file_path': str(file_path.relative_to(self.base_path)),
                'content_type': file.content_type or 'application/octet-stream'
            }
            
            if metadata:
                file_metadata.update(metadata)
            
            # Save metadata
            self.save_metadata(filename, file_metadata, category)
            
            return file_metadata
            
        except Exception as e:
            print(f"Error saving uploaded file: {e}")
            return None
    
    def save_camera_capture(self, image_data: str, user_id: int, 
                           capture_type: str, metadata: Dict = None) -> Optional[Dict]:
        """
        Save camera capture with metadata
        
        Args:
            image_data: Base64 encoded image data
            user_id: User ID for organization
            capture_type: Type of capture (camera_aadhar, camera_license, etc.)
            metadata: Additional metadata (location, timestamp, etc.)
            
        Returns:
            Dict with file info or None if failed
        """
        try:
            if not image_data or not image_data.startswith('data:image/'):
                return None
            
            # Parse base64 data
            header, encoded = image_data.split(',', 1)
            
            # Determine file extension from header
            if 'jpeg' in header or 'jpg' in header:
                extension = 'jpg'
            elif 'png' in header:
                extension = 'png'
            elif 'webp' in header:
                extension = 'webp'
            else:
                extension = 'jpg'
            
            # Decode image
            image_bytes = base64.b64decode(encoded)
            
            # Generate filename and path
            filename = self.generate_secure_filename(f'capture.{extension}', 
                                                   user_id, capture_type, 'CAP')
            storage_path = self.get_storage_path('captures', capture_type)
            file_path = storage_path / filename
            
            # Save image file
            with open(file_path, 'wb') as f:
                f.write(image_bytes)
            
            # Create metadata
            capture_metadata = {
                'stored_filename': filename,
                'capture_type': capture_type,
                'category': 'captures',
                'user_id': user_id,
                'file_size': len(image_bytes),
                'captured_at': datetime.now().isoformat(),
                'file_path': str(file_path.relative_to(self.base_path)),
                'image_format': extension,
                'capture_method': 'camera'
            }
            
            if metadata:
                capture_metadata.update(metadata)
            
            # Save metadata
            self.save_metadata(filename, capture_metadata, 'captures')
            
            return capture_metadata
            
        except Exception as e:
            print(f"Error saving camera capture: {e}")
            return None
    
    def save_metadata(self, filename: str, metadata: Dict, category: str):
        """Save metadata for a file"""
        try:
            metadata_dir = self.base_path / 'metadata' / category
            metadata_file = metadata_dir / f"{filename}.json"
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
                
        except Exception as e:
            print(f"Error saving metadata: {e}")
    
    def get_file_metadata(self, filename: str, category: str) -> Optional[Dict]:
        """Retrieve metadata for a file"""
        try:
            metadata_file = self.base_path / 'metadata' / category / f"{filename}.json"
            
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    return json.load(f)
            return None
            
        except Exception as e:
            print(f"Error reading metadata: {e}")
            return None
    
    def get_user_files(self, user_id: int, file_type: str = None) -> List[Dict]:
        """Get all files for a specific user"""
        files = []
        
        for category in ['documents', 'photos', 'captures']:
            metadata_dir = self.base_path / 'metadata' / category
            
            if not metadata_dir.exists():
                continue
                
            for metadata_file in metadata_dir.glob('*.json'):
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    if metadata.get('user_id') == user_id:
                        if file_type is None or metadata.get('file_type') == file_type:
                            files.append(metadata)
                            
                except Exception as e:
                    print(f"Error reading metadata file {metadata_file}: {e}")
        
        return sorted(files, key=lambda x: x.get('uploaded_at', x.get('captured_at', '')), reverse=True)

    def get_files_by_category(self, category: str, user_filter: int = None, page: int = 1, per_page: int = 20) -> Dict:
        """Get files by category with pagination"""
        files = []
        
        metadata_dir = self.base_path / 'metadata' / category
        if not metadata_dir.exists():
            return {
                'files': [],
                'total': 0,
                'page': page,
                'per_page': per_page,
                'pages': 0
            }
        
        for metadata_file in metadata_dir.glob('*.json'):
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                # Apply user filter if specified
                if user_filter and metadata.get('user_id') != user_filter:
                    continue
                    
                files.append(metadata)
                
            except Exception as e:
                continue
        
        # Sort by upload date (newest first)
        files.sort(key=lambda x: x.get('uploaded_at', x.get('captured_at', '')), reverse=True)
        
        # Calculate pagination
        total = len(files)
        pages = (total + per_page - 1) // per_page
        start = (page - 1) * per_page
        end = start + per_page
        
        return {
            'files': files[start:end],
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': pages
        }
    
    def delete_file(self, filename: str, category: str) -> bool:
        """Delete a file and its metadata"""
        try:
            # Find and delete the actual file
            for subcategory_path in self.storage_categories.get(category, {}).values():
                file_path = self.base_path / subcategory_path / filename
                if file_path.exists():
                    file_path.unlink()
                    break
            
            # Delete metadata
            metadata_file = self.base_path / 'metadata' / category / f"{filename}.json"
            if metadata_file.exists():
                metadata_file.unlink()
            
            return True
            
        except Exception as e:
            print(f"Error deleting file {filename}: {e}")
            return False
    
    def get_storage_stats(self) -> Dict:
        """Get storage statistics"""
        stats = {
            'total_files': 0,
            'total_size': 0,
            'categories': {}
        }
        
        for category in ['documents', 'photos', 'captures', 'assets']:
            category_stats = {
                'files': 0,
                'size': 0,
                'subcategories': {}
            }
            
            if category in self.storage_categories:
                for subcategory, path in self.storage_categories[category].items():
                    subcat_path = self.base_path / path
                    if subcat_path.exists():
                        files = list(subcat_path.glob('*'))
                        file_count = len([f for f in files if f.is_file() and f.name != '.gitkeep'])
                        total_size = sum(f.stat().st_size for f in files if f.is_file() and f.name != '.gitkeep')
                        
                        category_stats['subcategories'][subcategory] = {
                            'files': file_count,
                            'size': total_size
                        }
                        category_stats['files'] += file_count
                        category_stats['size'] += total_size
            
            stats['categories'][category] = category_stats
            stats['total_files'] += category_stats['files']
            stats['total_size'] += category_stats['size']
        
        return stats
    
    def cleanup_temp_files(self, older_than_hours: int = 24):
        """Clean up temporary files older than specified hours"""
        temp_dir = self.base_path / 'temp'
        if not temp_dir.exists():
            return
        
        cutoff_time = datetime.now().timestamp() - (older_than_hours * 3600)
        
        for temp_file in temp_dir.rglob('*'):
            if temp_file.is_file() and temp_file.stat().st_mtime < cutoff_time:
                try:
                    temp_file.unlink()
                except Exception as e:
                    print(f"Error cleaning up temp file {temp_file}: {e}")

# Global storage manager instance
app_storage = AppStorageManager()

def setup_app_storage():
    """Initialize the app storage system"""
    return app_storage

def migrate_existing_uploads():
    """Migrate files from the old uploads/ directory to the new organized structure"""
    old_uploads_dir = Path('uploads')
    if not old_uploads_dir.exists():
        return
    
    migrated_count = 0
    
    for old_file in old_uploads_dir.glob('*'):
        if old_file.is_file() and old_file.name != '.gitkeep':
            try:
                # Parse filename to determine type
                filename_parts = old_file.name.split('_')
                if len(filename_parts) >= 2:
                    file_type = filename_parts[0]
                    user_id = filename_parts[1] if filename_parts[1].isdigit() else 1
                    
                    # Determine new location
                    if file_type in ['aadhar', 'license']:
                        new_path = app_storage.get_storage_path('documents', file_type)
                    elif file_type in ['profile', 'duty']:
                        new_path = app_storage.get_storage_path('photos', file_type) 
                    else:
                        new_path = app_storage.get_storage_path('assets', 'reports')
                    
                    # Copy file to new location
                    new_file_path = new_path / old_file.name
                    shutil.copy2(old_file, new_file_path)
                    
                    # Create metadata
                    metadata = {
                        'original_filename': old_file.name,
                        'stored_filename': old_file.name,
                        'file_type': file_type,
                        'user_id': int(user_id) if str(user_id).isdigit() else 1,
                        'file_size': old_file.stat().st_size,
                        'migrated_at': datetime.now().isoformat(),
                        'migrated_from': str(old_file),
                        'file_path': str(new_file_path.relative_to(app_storage.base_path))
                    }
                    
                    category = 'documents' if file_type in ['aadhar', 'license'] else 'photos'
                    app_storage.save_metadata(old_file.name, metadata, category)
                    
                    migrated_count += 1
                    
            except Exception as e:
                print(f"Error migrating file {old_file}: {e}")
    
    print(f"Migration completed. Migrated {migrated_count} files to organized storage.")

if __name__ == '__main__':
    # Setup storage and migrate existing files
    setup_app_storage()
    migrate_existing_uploads()
    
    # Display storage stats
    stats = app_storage.get_storage_stats()
    print(f"Storage initialized with {stats['total_files']} files ({stats['total_size']} bytes)")