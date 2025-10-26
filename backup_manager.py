#!/usr/bin/env python3
"""
Backup & Disaster Recovery Manager
Handles automated database backups, monitoring, and restore functionality
"""

import os
import sqlite3
import shutil
import schedule
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
import zipfile
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from threading import Thread

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backup.log'),
        logging.StreamHandler()
    ]
)

class BackupManager:
    def __init__(self, db_path='instance/hospital_web.db', backup_dir='backups'):
        self.db_path = db_path
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        
        # Backup configuration
        self.config = {
            'retention_days': 30,
            'max_backups': 50,
            'compression': True,
            'email_notifications': True,
            'email_config': {
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'username': '',  # Configure in production
                'password': '',  # Configure in production
                'recipients': []  # Configure in production
            }
        }
        
    def create_backup(self, backup_type='manual'):
        """Create a database backup"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"hospital_backup_{backup_type}_{timestamp}.db"
            backup_path = self.backup_dir / backup_filename
            
            # Create backup
            shutil.copy2(self.db_path, backup_path)
            
            # Compress if enabled
            if self.config['compression']:
                compressed_path = backup_path.with_suffix('.zip')
                with zipfile.ZipFile(compressed_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    zipf.write(backup_path, backup_filename)
                os.remove(backup_path)
                backup_path = compressed_path
            
            # Create metadata
            metadata = {
                'backup_type': backup_type,
                'timestamp': timestamp,
                'file_size': os.path.getsize(backup_path),
                'db_path': str(self.db_path),
                'compressed': self.config['compression']
            }
            
            metadata_path = backup_path.with_suffix('.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logging.info(f"Backup created successfully: {backup_path}")
            
            # Clean old backups
            self._cleanup_old_backups()
            
            # Send notification
            if self.config['email_notifications']:
                self._send_backup_notification(backup_path, metadata)
            
            return str(backup_path)
            
        except Exception as e:
            logging.error(f"Backup failed: {str(e)}")
            if self.config['email_notifications']:
                self._send_error_notification(str(e))
            raise
    
    def restore_backup(self, backup_path):
        """Restore database from backup"""
        try:
            backup_path = Path(backup_path)
            
            if not backup_path.exists():
                raise FileNotFoundError(f"Backup file not found: {backup_path}")
            
            # Create current backup before restore
            current_backup = self.create_backup('pre_restore')
            logging.info(f"Current database backed up to: {current_backup}")
            
            # Stop any active connections (in production, you'd want to handle this more gracefully)
            
            if backup_path.suffix == '.zip':
                # Extract compressed backup
                with zipfile.ZipFile(backup_path, 'r') as zipf:
                    extracted_files = zipf.namelist()
                    db_file = next((f for f in extracted_files if f.endswith('.db')), None)
                    if not db_file:
                        raise ValueError("No database file found in backup archive")
                    
                    temp_dir = self.backup_dir / 'temp_restore'
                    temp_dir.mkdir(exist_ok=True)
                    zipf.extract(db_file, temp_dir)
                    
                    # Replace current database
                    shutil.copy2(temp_dir / db_file, self.db_path)
                    shutil.rmtree(temp_dir)
            else:
                # Direct database file
                shutil.copy2(backup_path, self.db_path)
            
            logging.info(f"Database restored successfully from: {backup_path}")
            return True
            
        except Exception as e:
            logging.error(f"Restore failed: {str(e)}")
            raise
    
    def list_backups(self):
        """List all available backups"""
        backups = []
        
        for backup_file in self.backup_dir.glob('hospital_backup_*.db*'):
            metadata_file = backup_file.with_suffix('.json')
            
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
            else:
                # Create basic metadata for files without it
                metadata = {
                    'backup_type': 'unknown',
                    'timestamp': datetime.fromtimestamp(backup_file.stat().st_mtime).strftime('%Y%m%d_%H%M%S'),
                    'file_size': backup_file.stat().st_size,
                    'compressed': backup_file.suffix == '.zip'
                }
            
            metadata['file_path'] = str(backup_file)
            metadata['file_name'] = backup_file.name
            backups.append(metadata)
        
        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x['timestamp'], reverse=True)
        return backups
    
    def _cleanup_old_backups(self):
        """Remove old backups based on retention policy"""
        try:
            backups = self.list_backups()
            
            # Remove backups older than retention period
            cutoff_date = datetime.now() - timedelta(days=self.config['retention_days'])
            
            for backup in backups:
                backup_date = datetime.strptime(backup['timestamp'], '%Y%m%d_%H%M%S')
                if backup_date < cutoff_date:
                    backup_path = Path(backup['file_path'])
                    metadata_path = backup_path.with_suffix('.json')
                    
                    if backup_path.exists():
                        os.remove(backup_path)
                    if metadata_path.exists():
                        os.remove(metadata_path)
                    
                    logging.info(f"Removed old backup: {backup_path}")
            
            # Keep only max_backups most recent
            if len(backups) > self.config['max_backups']:
                for backup in backups[self.config['max_backups']:]:
                    backup_path = Path(backup['file_path'])
                    metadata_path = backup_path.with_suffix('.json')
                    
                    if backup_path.exists():
                        os.remove(backup_path)
                    if metadata_path.exists():
                        os.remove(metadata_path)
                    
                    logging.info(f"Removed excess backup: {backup_path}")
                    
        except Exception as e:
            logging.error(f"Cleanup failed: {str(e)}")
    
    def _send_backup_notification(self, backup_path, metadata):
        """Send email notification about successful backup"""
        try:
            if not self.config['email_config']['recipients']:
                return
            
            subject = f"Hospital DB Backup Successful - {metadata['timestamp']}"
            body = f"""
            Database backup completed successfully.
            
            Details:
            - Backup Type: {metadata['backup_type']}
            - Timestamp: {metadata['timestamp']}
            - File Size: {metadata['file_size']} bytes
            - File Path: {backup_path}
            - Compressed: {metadata['compressed']}
            
            This is an automated notification from the Hospital Management System.
            """
            
            self._send_email(subject, body)
            
        except Exception as e:
            logging.error(f"Failed to send backup notification: {str(e)}")
    
    def _send_error_notification(self, error_message):
        """Send email notification about backup failure"""
        try:
            if not self.config['email_config']['recipients']:
                return
            
            subject = "Hospital DB Backup FAILED - Immediate Attention Required"
            body = f"""
            ALERT: Database backup has failed!
            
            Error Details:
            {error_message}
            
            Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            
            Please investigate immediately to ensure data protection.
            
            This is an automated alert from the Hospital Management System.
            """
            
            self._send_email(subject, body)
            
        except Exception as e:
            logging.error(f"Failed to send error notification: {str(e)}")
    
    def _send_email(self, subject, body):
        """Send email notification"""
        try:
            config = self.config['email_config']
            
            if not config['username'] or not config['recipients']:
                return
            
            msg = MimeMultipart()
            msg['From'] = config['username']
            msg['To'] = ', '.join(config['recipients'])
            msg['Subject'] = subject
            
            msg.attach(MimeText(body, 'plain'))
            
            server = smtplib.SMTP(config['smtp_server'], config['smtp_port'])
            server.starttls()
            server.login(config['username'], config['password'])
            
            text = msg.as_string()
            server.sendmail(config['username'], config['recipients'], text)
            server.quit()
            
            logging.info("Email notification sent successfully")
            
        except Exception as e:
            logging.error(f"Failed to send email: {str(e)}")
    
    def schedule_backups(self):
        """Schedule automated backups"""
        # Daily backup at 2 AM
        schedule.every().day.at("02:00").do(self.create_backup, 'daily')
        
        # Hourly backup during business hours (9 AM to 6 PM)
        for hour in range(9, 18):
            schedule.every().day.at(f"{hour:02d}:00").do(self.create_backup, 'hourly')
        
        # Weekly backup on Sunday at 1 AM
        schedule.every().sunday.at("01:00").do(self.create_backup, 'weekly')
        
        logging.info("Backup schedule configured")
    
    def run_scheduler(self):
        """Run the backup scheduler"""
        logging.info("Starting backup scheduler...")
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def start_scheduler_thread(self):
        """Start backup scheduler in background thread"""
        scheduler_thread = Thread(target=self.run_scheduler, daemon=True)
        scheduler_thread.start()
        logging.info("Backup scheduler started in background")
    
    def verify_backup_integrity(self, backup_path):
        """Verify backup file integrity"""
        try:
            backup_path = Path(backup_path)
            
            if backup_path.suffix == '.zip':
                # Verify ZIP file
                with zipfile.ZipFile(backup_path, 'r') as zipf:
                    bad_files = zipf.testzip()
                    if bad_files:
                        return False, f"Corrupted files in archive: {bad_files}"
                
                # Extract and test database
                with zipfile.ZipFile(backup_path, 'r') as zipf:
                    db_files = [f for f in zipf.namelist() if f.endswith('.db')]
                    if not db_files:
                        return False, "No database file found in archive"
                    
                    temp_dir = self.backup_dir / 'temp_verify'
                    temp_dir.mkdir(exist_ok=True)
                    
                    try:
                        zipf.extract(db_files[0], temp_dir)
                        db_path = temp_dir / db_files[0]
                        
                        # Test database connection
                        conn = sqlite3.connect(db_path)
                        cursor = conn.cursor()
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                        tables = cursor.fetchall()
                        conn.close()
                        
                        if not tables:
                            return False, "Database appears to be empty or corrupted"
                        
                        return True, f"Backup verified successfully. Found {len(tables)} tables."
                        
                    finally:
                        shutil.rmtree(temp_dir, ignore_errors=True)
            else:
                # Direct database file
                conn = sqlite3.connect(backup_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                conn.close()
                
                if not tables:
                    return False, "Database appears to be empty or corrupted"
                
                return True, f"Backup verified successfully. Found {len(tables)} tables."
                
        except Exception as e:
            return False, f"Verification failed: {str(e)}"

# CLI interface for backup management
if __name__ == "__main__":
    import sys
    
    backup_manager = BackupManager()
    
    if len(sys.argv) < 2:
        print("Usage: python backup_manager.py [create|restore|list|verify|schedule]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "create":
        backup_type = sys.argv[2] if len(sys.argv) > 2 else "manual"
        backup_path = backup_manager.create_backup(backup_type)
        print(f"Backup created: {backup_path}")
    
    elif command == "restore":
        if len(sys.argv) < 3:
            print("Usage: python backup_manager.py restore <backup_path>")
            sys.exit(1)
        
        backup_path = sys.argv[2]
        backup_manager.restore_backup(backup_path)
        print(f"Database restored from: {backup_path}")
    
    elif command == "list":
        backups = backup_manager.list_backups()
        print(f"Found {len(backups)} backups:")
        for backup in backups:
            print(f"  {backup['file_name']} - {backup['timestamp']} ({backup['backup_type']})")
    
    elif command == "verify":
        if len(sys.argv) < 3:
            print("Usage: python backup_manager.py verify <backup_path>")
            sys.exit(1)
        
        backup_path = sys.argv[2]
        is_valid, message = backup_manager.verify_backup_integrity(backup_path)
        print(f"Verification result: {message}")
        sys.exit(0 if is_valid else 1)
    
    elif command == "schedule":
        backup_manager.schedule_backups()
        backup_manager.run_scheduler()
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)