#!/usr/bin/env python3
"""
Test script for the new cloud storage system
"""

import os
import sys
sys.path.append('.')

from utils import upload_to_cloud, download_from_cloud, delete_from_cloud, storage_manager
import base64

def test_cloud_storage():
    """Test cloud storage functionality"""
    print("🌩️  PLS TRAVELS - Cloud Storage Test")
    print("=" * 40)
    
    # Test 1: Upload text file
    print("\n📤 Test 1: Upload text file")
    test_content = "Hello from PLS TRAVELS fleet management system!"
    test_filename = "test_document.txt"
    
    cloud_url = upload_to_cloud(
        test_content.encode('utf-8'), 
        test_filename, 
        bucket_type='documents'
    )
    
    if cloud_url:
        print(f"✅ Upload successful: {cloud_url}")
    else:
        print("❌ Upload failed")
        return
    
    # Test 2: Download the file
    print("\n📥 Test 2: Download file")
    downloaded_data = download_from_cloud(cloud_url)
    
    if downloaded_data:
        downloaded_text = downloaded_data.decode('utf-8')
        print(f"✅ Download successful: {downloaded_text}")
        
        if downloaded_text == test_content:
            print("✅ Content matches original")
        else:
            print("❌ Content doesn't match")
    else:
        print("❌ Download failed")
    
    # Test 3: Upload base64 image
    print("\n📤 Test 3: Upload base64 image")
    
    # Create a simple base64 test image (1x1 pixel PNG)
    test_image_base64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    
    image_url = upload_to_cloud(
        test_image_base64, 
        "test_photo.png", 
        bucket_type='photos'
    )
    
    if image_url:
        print(f"✅ Image upload successful: {image_url}")
    else:
        print("❌ Image upload failed")
    
    # Test 4: List files
    print("\n📋 Test 4: List files in buckets")
    
    for bucket_type in ['documents', 'photos', 'duty_captures', 'vehicle_images', 'assets', 'reports']:
        files = storage_manager.list_files(bucket_type)
        print(f"📁 {bucket_type}: {len(files)} files")
        if files:
            print(f"   Sample: {files[0] if hasattr(files[0], 'name') else str(files[0])[:50]}")
    
    # Test 5: Clean up
    print("\n🗑️  Test 5: Cleanup test files")
    
    if cloud_url:
        if delete_from_cloud(cloud_url):
            print("✅ Text file deleted successfully")
        else:
            print("❌ Text file deletion failed")
    
    if image_url:
        if delete_from_cloud(image_url):
            print("✅ Image file deleted successfully")
        else:
            print("❌ Image file deletion failed")
    
    print("\n🎉 Cloud storage test completed!")

if __name__ == "__main__":
    test_cloud_storage()