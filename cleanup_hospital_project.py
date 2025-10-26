#!/usr/bin/env python3
"""
Hospital Management System - Project Cleanup Script
Removes irrelevant files and keeps only web_app.py related files
"""

import os
import shutil
from pathlib import Path

def cleanup_project():
    """Remove irrelevant files and keep only web_app.py dependencies"""
    
    # Files to keep (web_app.py dependencies)
    files_to_keep = {
        'web_app.py',
        'config.py',
        'requirements.txt',
        '.env',
        '.env.example',
        '.gitignore',
        'backup_manager.py',
        'audit_logger.py',
        'two_factor_auth.py',
        'notification_system.py',
        'data_export_import.py',  # Missing but needed
        'document_management.py',
        'advanced_security.py',
        'payment_gateway.py',
        'emergency_management.py',
        'inventory_management.py',
        'quality_management.py',
        'tenant_context.py',
        'tenant_routes.py',
        'subscription_plans.py',
        'api_routes.py',
        'hospital_web.db',  # Main database for web_app.py
        'cleanup_hospital_project.py'  # This script
    }
    
    # Directories to keep
    dirs_to_keep = {
        'templates',
        'static',
        'uploads',
        'logs',
        '.git',
        'venv',
        '__pycache__'
    }
    
    # Files to remove (irrelevant to web_app.py)
    files_to_remove = []
    dirs_to_remove = []
    
    # Scan current directory
    for item in os.listdir('.'):
        if os.path.isfile(item):
            if item not in files_to_keep:
                files_to_remove.append(item)
        elif os.path.isdir(item):
            if item not in dirs_to_keep:
                dirs_to_remove.append(item)
    
    print("🧹 Hospital Management System - Project Cleanup")
    print("=" * 50)
    print(f"Files to keep: {len(files_to_keep)}")
    print(f"Directories to keep: {len(dirs_to_keep)}")
    print(f"Files to remove: {len(files_to_remove)}")
    print(f"Directories to remove: {len(dirs_to_remove)}")
    print()
    
    if files_to_remove:
        print("📄 Files to be removed:")
        for file in sorted(files_to_remove):
            print(f"  - {file}")
        print()
    
    if dirs_to_remove:
        print("📁 Directories to be removed:")
        for dir in sorted(dirs_to_remove):
            print(f"  - {dir}/")
        print()
    
    # Ask for confirmation
    if files_to_remove or dirs_to_remove:
        response = input("Do you want to proceed with cleanup? (y/N): ").strip().lower()
        if response != 'y':
            print("❌ Cleanup cancelled.")
            return
        
        # Remove files
        removed_files = 0
        for file in files_to_remove:
            try:
                os.remove(file)
                print(f"✅ Removed file: {file}")
                removed_files += 1
            except Exception as e:
                print(f"❌ Error removing {file}: {e}")
        
        # Remove directories
        removed_dirs = 0
        for dir in dirs_to_remove:
            try:
                shutil.rmtree(dir)
                print(f"✅ Removed directory: {dir}/")
                removed_dirs += 1
            except Exception as e:
                print(f"❌ Error removing {dir}/: {e}")
        
        print()
        print("🎉 Cleanup completed!")
        print(f"✅ Removed {removed_files} files and {removed_dirs} directories")
        print()
        print("📋 Remaining files for web_app.py:")
        for file in sorted(files_to_keep):
            if os.path.exists(file):
                print(f"  ✓ {file}")
            else:
                print(f"  ⚠️  {file} (missing - may need to be created)")
    else:
        print("✨ Project is already clean! No files to remove.")

if __name__ == "__main__":
    cleanup_project()