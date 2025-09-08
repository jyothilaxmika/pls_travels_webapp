#!/usr/bin/env python3
"""
Storage Management Routes for PLS TRAVELS
Admin routes for managing the organized storage system
"""

from flask import Blueprint, render_template, request, jsonify, send_file
from flask_login import login_required, current_user
from admin_routes import admin_required
from storage_integration import StorageIntegration, app_storage
from pathlib import Path
import mimetypes

storage_bp = Blueprint('storage', __name__)

@storage_bp.route('/admin/storage', methods=['GET'])
@login_required
@admin_required
def storage_dashboard():
    """Storage management dashboard"""
    stats = StorageIntegration.get_storage_statistics()
    return render_template('admin/storage_dashboard.html', stats=stats)

@storage_bp.route('/admin/storage/stats', methods=['GET'])
@login_required
@admin_required
def get_storage_stats():
    """Get storage statistics as JSON"""
    return jsonify(StorageIntegration.get_storage_statistics())

@storage_bp.route('/admin/storage/cleanup', methods=['POST'])
@login_required
@admin_required  
def cleanup_storage():
    """Cleanup old temporary files"""
    hours = request.json.get('hours', 168)  # Default 1 week
    
    try:
        StorageIntegration.cleanup_old_files(hours)
        return jsonify({'success': True, 'message': f'Cleaned up files older than {hours} hours'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Cleanup failed: {str(e)}'})

@storage_bp.route('/admin/storage/migrate', methods=['POST'])
@login_required
@admin_required
def migrate_legacy_files():
    """Migrate files from old uploads directory"""
    try:
        StorageIntegration.migrate_legacy_uploads()
        return jsonify({'success': True, 'message': 'Legacy files migrated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Migration failed: {str(e)}'})

@storage_bp.route('/storage/file/<path:file_path>')
@login_required
def serve_stored_file(file_path):
    """Serve files from the organized storage system"""
    try:
        # Security check - ensure file is within storage directory
        full_path = app_storage.base_path / file_path
        
        if not full_path.exists() or not str(full_path).startswith(str(app_storage.base_path)):
            return jsonify({'error': 'File not found'}), 404
        
        # Check if user has permission to access this file
        # (Add your own access control logic here)
        
        # Determine MIME type
        mime_type = mimetypes.guess_type(str(full_path))[0] or 'application/octet-stream'
        
        return send_file(str(full_path), mimetype=mime_type)
        
    except Exception as e:
        return jsonify({'error': 'Failed to serve file'}), 500

@storage_bp.route('/api/storage/user/<int:user_id>/files')
@login_required
def get_user_files_api(user_id):
    """Get all files for a specific user via API"""
    try:
        # Check permissions - users can only access their own files, admins can access any
        if current_user.role.name != 'ADMIN' and current_user.id != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        file_type = request.args.get('type')
        files = StorageIntegration.get_user_documents(user_id, file_type)
        
        return jsonify({'files': files})
        
    except Exception as e:
        return jsonify({'error': f'Failed to retrieve files: {str(e)}'}), 500

@storage_bp.route('/api/storage/file/<filename>/metadata')
@login_required
def get_file_metadata_api(filename):
    """Get metadata for a specific file"""
    try:
        doc_type = request.args.get('type', 'photos')
        metadata = StorageIntegration.get_document_metadata(filename, doc_type)
        
        if not metadata:
            return jsonify({'error': 'File not found'}), 404
        
        # Check permissions
        if current_user.role.name != 'ADMIN' and metadata.get('user_id') != current_user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        return jsonify({'metadata': metadata})
        
    except Exception as e:
        return jsonify({'error': f'Failed to retrieve metadata: {str(e)}'}), 500

@storage_bp.route('/api/storage/file/<filename>', methods=['DELETE'])
@login_required
def delete_file_api(filename):
    """Delete a file via API"""
    try:
        doc_type = request.args.get('type', 'photos')
        
        # Get metadata to check permissions
        metadata = StorageIntegration.get_document_metadata(filename, doc_type)
        if not metadata:
            return jsonify({'error': 'File not found'}), 404
        
        # Check permissions
        if current_user.role.name != 'ADMIN' and metadata.get('user_id') != current_user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        success = StorageIntegration.delete_document(filename, doc_type)
        
        if success:
            return jsonify({'success': True, 'message': 'File deleted successfully'})
        else:
            return jsonify({'error': 'Failed to delete file'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to delete file: {str(e)}'}), 500