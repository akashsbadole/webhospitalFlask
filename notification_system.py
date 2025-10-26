#!/usr/bin/env python3
"""
Comprehensive Notification System
Handles email, SMS, push notifications, WhatsApp integration, and automated reminders
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import requests
from twilio.rest import Client
from flask import current_app, render_template_string
import schedule
import time
import threading
from jinja2 import Template
import sqlite3

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificationSystem:
    def __init__(self, db, app):
        self.db = db
        self.app = app
        # Initialize model classes as None - they'll be set up when first accessed
        self.NotificationTemplate = None
        self.NotificationLog = None
        self.NotificationPreference = None
        self.ScheduledNotification = None
        
        # Set up tables within app context
        with self.app.app_context():
            self.setup_notification_tables()
        
        # Configuration
        self.config = {
            'email': {
                'enabled': True,
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'username': '',  # Configure in production
                'password': '',  # Configure in production
                'from_name': 'Hospital Management System'
            },
            'sms': {
                'enabled': False,  # Configure in production
                'twilio_account_sid': '',
                'twilio_auth_token': '',
                'twilio_phone_number': ''
            },
            'whatsapp': {
                'enabled': False,  # Configure in production
                'twilio_account_sid': '',
                'twilio_auth_token': '',
                'whatsapp_number': ''  # Format: whatsapp:+1234567890
            },
            'push': {
                'enabled': False,  # Configure in production
                'firebase_server_key': '',
                'firebase_sender_id': ''
            },
            'reminders': {
                'appointment_reminder_hours': [24, 2],  # Hours before appointment
                'medication_reminder_enabled': True,
                'lab_result_notification': True,
                'bill_reminder_days': [7, 3, 1]  # Days before due date
            }
        }
    
    def setup_notification_tables(self):
        """Create notification related tables - only called within app context"""
        self._create_default_templates()
    
    def _create_default_templates(self):
        """Create default notification templates - only called within app context"""
        try:
            # Define model classes within app context
            class NotificationTemplate(self.db.Model):
                __tablename__ = 'notification_templates'
                
                id = self.db.Column(self.db.Integer, primary_key=True)
                name = self.db.Column(self.db.String(100), nullable=False, unique=True)
                type = self.db.Column(self.db.String(20), nullable=False)  # email, sms, whatsapp, push
                subject = self.db.Column(self.db.String(200))  # For email
                body_template = self.db.Column(self.db.Text, nullable=False)
                variables = self.db.Column(self.db.Text)  # JSON array of template variables
                is_active = self.db.Column(self.db.Boolean, default=True)
                created_at = self.db.Column(self.db.DateTime, default=datetime.utcnow)
                updated_at = self.db.Column(self.db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
            
            class NotificationLog(self.db.Model):
                __tablename__ = 'notification_logs'
                
                id = self.db.Column(self.db.Integer, primary_key=True)
                recipient_type = self.db.Column(self.db.String(20), nullable=False)  # patient, staff, doctor
                recipient_id = self.db.Column(self.db.Integer, nullable=False)
                recipient_contact = self.db.Column(self.db.String(100), nullable=False)  # email/phone
                notification_type = self.db.Column(self.db.String(50), nullable=False)
                channel = self.db.Column(self.db.String(20), nullable=False)  # email, sms, whatsapp, push
                subject = self.db.Column(self.db.String(200))
                message = self.db.Column(self.db.Text)
                status = self.db.Column(self.db.String(20), default='pending')  # pending, sent, failed, delivered
                sent_at = self.db.Column(self.db.DateTime)
                delivered_at = self.db.Column(self.db.DateTime)
                error_message = self.db.Column(self.db.Text)
                retry_count = self.db.Column(self.db.Integer, default=0)
                created_at = self.db.Column(self.db.DateTime, default=datetime.utcnow)
            
            class NotificationPreference(self.db.Model):
                __tablename__ = 'notification_preferences'
                
                id = self.db.Column(self.db.Integer, primary_key=True)
                user_id = self.db.Column(self.db.Integer, nullable=False)
                user_type = self.db.Column(self.db.String(20), nullable=False)  # patient, staff
                notification_type = self.db.Column(self.db.String(50), nullable=False)
                email_enabled = self.db.Column(self.db.Boolean, default=True)
                sms_enabled = self.db.Column(self.db.Boolean, default=False)
                whatsapp_enabled = self.db.Column(self.db.Boolean, default=False)
                push_enabled = self.db.Column(self.db.Boolean, default=True)
                created_at = self.db.Column(self.db.DateTime, default=datetime.utcnow)
            
            class ScheduledNotification(self.db.Model):
                __tablename__ = 'scheduled_notifications'
                
                id = self.db.Column(self.db.Integer, primary_key=True)
                recipient_type = self.db.Column(self.db.String(20), nullable=False)
                recipient_id = self.db.Column(self.db.Integer, nullable=False)
                notification_type = self.db.Column(self.db.String(50), nullable=False)
                scheduled_time = self.db.Column(self.db.DateTime, nullable=False)
                template_data = self.db.Column(self.db.Text)  # JSON data for template
                status = self.db.Column(self.db.String(20), default='pending')  # pending, sent, cancelled
                created_at = self.db.Column(self.db.DateTime, default=datetime.utcnow)
            
                # Store model classes (moved outside the class definition)
                self.NotificationTemplate = NotificationTemplate
                self.NotificationLog = NotificationLog
                self.NotificationPreference = NotificationPreference
                self.ScheduledNotification = ScheduledNotification
                
                # Create tables
                self.db.create_all()
                
                # Create default templates
                default_templates = [
                    {
                        'name': 'appointment_reminder',
                        'type': 'email',
                        'subject': 'Appointment Reminder - {{appointment_date}}',
                        'body_template': '''
                        Dear {{patient_name}},
                        
                        This is a reminder for your upcoming appointment:
                        
                        Date: {{appointment_date}}
                        Time: {{appointment_time}}
                        Doctor: {{doctor_name}}
                        Department: {{department}}
                        
                        Please arrive 15 minutes early for check-in.
                        
                        If you need to reschedule, please contact us at {{hospital_phone}}.
                        
                        Best regards,
                        {{hospital_name}}
                        ''',
                        'variables': json.dumps(['patient_name', 'appointment_date', 'appointment_time', 'doctor_name', 'department', 'hospital_phone', 'hospital_name'])
                    },
                    {
                        'name': 'appointment_reminder_sms',
                        'type': 'sms',
                        'subject': None,
                        'body_template': 'Reminder: Appointment with Dr. {{doctor_name}} on {{appointment_date}} at {{appointment_time}}. Contact {{hospital_phone}} to reschedule.',
                        'variables': json.dumps(['doctor_name', 'appointment_date', 'appointment_time', 'hospital_phone'])
                    },
                    {
                        'name': 'lab_result_ready',
                        'type': 'email',
                        'subject': 'Lab Results Available - {{test_name}}',
                        'body_template': '''
                        Dear {{patient_name}},
                        
                        Your lab results for {{test_name}} are now available.
                        
                        Test Date: {{test_date}}
                        Ordered by: {{doctor_name}}
                        
                        Please log in to your patient portal to view the results or visit the hospital to collect a printed copy.
                        
                        If you have any questions about your results, please contact your doctor.
                        
                        Best regards,
                        {{hospital_name}}
                        ''',
                        'variables': json.dumps(['patient_name', 'test_name', 'test_date', 'doctor_name', 'hospital_name'])
                    },
                    {
                        'name': 'bill_reminder',
                        'type': 'email',
                        'subject': 'Payment Reminder - Bill #{{bill_number}}',
                        'body_template': '''
                        Dear {{patient_name}},
                        
                        This is a reminder that your bill is due for payment:
                        
                        Bill Number: {{bill_number}}
                        Amount Due: {{amount_due}}
                        Due Date: {{due_date}}
                        
                        You can pay online through our patient portal or visit the billing counter.
                        
                        For any queries, please contact our billing department at {{billing_phone}}.
                        
                        Thank you,
                        {{hospital_name}}
                        ''',
                        'variables': json.dumps(['patient_name', 'bill_number', 'amount_due', 'due_date', 'billing_phone', 'hospital_name'])
                    },
                    {
                        'name': 'medication_reminder',
                        'type': 'sms',
                        'subject': None,
                        'body_template': 'Medication Reminder: Time to take {{medication_name}} - {{dosage}}. Prescribed by Dr. {{doctor_name}}.',
                        'variables': json.dumps(['medication_name', 'dosage', 'doctor_name'])
                    },
                    {
                        'name': 'discharge_summary',
                        'type': 'email',
                        'subject': 'Discharge Summary - {{patient_name}}',
                        'body_template': '''
                        Dear {{patient_name}},
                        
                        You have been successfully discharged from our hospital.
                        
                        Discharge Date: {{discharge_date}}
                        Attending Doctor: {{doctor_name}}
                        
                        Please follow the discharge instructions provided and take your medications as prescribed.
                        
                        Your follow-up appointment is scheduled for {{followup_date}} with Dr. {{doctor_name}}.
                        
                        If you experience any complications, please contact us immediately at {{emergency_phone}}.
                        
                        Wishing you a speedy recovery,
                        {{hospital_name}}
                        ''',
                        'variables': json.dumps(['patient_name', 'discharge_date', 'doctor_name', 'followup_date', 'emergency_phone', 'hospital_name'])
                    }
                ]
                
                for template_data in default_templates:
                    existing = NotificationTemplate.query.filter_by(name=template_data['name']).first()
                    if not existing:
                        template = NotificationTemplate(**template_data)
                        self.db.session.add(template)
                
                self.db.session.commit()
                logger.info("Default notification templates created successfully")
                
        except Exception as e:
            logger.error(f"Failed to create default templates: {str(e)}")
            self.db.session.rollback()
    
    def _ensure_models_available(self):
        """Ensure model classes are available, create them if needed"""
        if self.NotificationTemplate is None:
            with self.app.app_context():
                self._create_default_templates()
    
    # ==================== CORE NOTIFICATION METHODS ====================
    
    def send_notification(self, recipient_type, recipient_id, notification_type, 
                         template_data=None, channels=None, priority='normal'):
        """Send notification through specified channels"""
        try:
            # Get recipient information
            recipient_info = self._get_recipient_info(recipient_type, recipient_id)
            if not recipient_info:
                logger.error(f"Recipient not found: {recipient_type} {recipient_id}")
                return False
            
            # Get notification preferences
            preferences = self._get_notification_preferences(recipient_id, recipient_type, notification_type)
            
            # Determine channels to use
            if not channels:
                channels = []
                if preferences.get('email_enabled', True) and recipient_info.get('email'):
                    channels.append('email')
                if preferences.get('sms_enabled', False) and recipient_info.get('phone'):
                    channels.append('sms')
                if preferences.get('whatsapp_enabled', False) and recipient_info.get('phone'):
                    channels.append('whatsapp')
                if preferences.get('push_enabled', True):
                    channels.append('push')
            
            success = True
            for channel in channels:
                try:
                    if channel == 'email' and recipient_info.get('email'):
                        self._send_email_notification(recipient_info, notification_type, template_data)
                    elif channel == 'sms' and recipient_info.get('phone'):
                        self._send_sms_notification(recipient_info, notification_type, template_data)
                    elif channel == 'whatsapp' and recipient_info.get('phone'):
                        self._send_whatsapp_notification(recipient_info, notification_type, template_data)
                    elif channel == 'push':
                        self._send_push_notification(recipient_info, notification_type, template_data)
                    
                except Exception as e:
                    logger.error(f"Failed to send {channel} notification: {str(e)}")
                    success = False
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send notification: {str(e)}")
            return False
    
    def _send_email_notification(self, recipient_info, notification_type, template_data):
        """Send email notification"""
        try:
            if not self.config['email']['enabled']:
                return False
            
            # Ensure models are available
            self._ensure_models_available()
            
            # Get template
            template = self.NotificationTemplate.query.filter_by(
                name=notification_type,
                type='email',
                is_active=True
            ).first()
            
            if not template:
                logger.error(f"Email template not found: {notification_type}")
                return False
            
            # Render template
            subject = self._render_template(template.subject, template_data)
            body = self._render_template(template.body_template, template_data)
            
            # Send email
            msg = MIMEMultipart()
            msg['From'] = f"{self.config['email']['from_name']} <{self.config['email']['username']}>"
            msg['To'] = recipient_info['email']
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.config['email']['smtp_server'], self.config['email']['smtp_port'])
            server.starttls()
            server.login(self.config['email']['username'], self.config['email']['password'])
            
            text = msg.as_string()
            server.sendmail(self.config['email']['username'], recipient_info['email'], text)
            server.quit()
            
            # Log notification
            self._log_notification(
                recipient_info['type'], recipient_info['id'], recipient_info['email'],
                notification_type, 'email', subject, body, 'sent'
            )
            
            logger.info(f"Email sent to {recipient_info['email']}")
            return True
            
        except Exception as e:
            self._log_notification(
                recipient_info['type'], recipient_info['id'], recipient_info['email'],
                notification_type, 'email', subject if 'subject' in locals() else '',
                body if 'body' in locals() else '', 'failed', str(e)
            )
            logger.error(f"Failed to send email: {str(e)}")
            return False
    
    def _send_sms_notification(self, recipient_info, notification_type, template_data):
        """Send SMS notification"""
        try:
            if not self.config['sms']['enabled']:
                return False
            
            # Ensure models are available
            self._ensure_models_available()
            
            # Get template
            template = self.NotificationTemplate.query.filter_by(
                name=f"{notification_type}_sms",
                type='sms',
                is_active=True
            ).first()
            
            if not template:
                # Try generic template
                template = self.NotificationTemplate.query.filter_by(
                    name=notification_type,
                    type='sms',
                    is_active=True
                ).first()
            
            if not template:
                logger.error(f"SMS template not found: {notification_type}")
                return False
            
            # Render template
            message = self._render_template(template.body_template, template_data)
            
            # Send SMS using Twilio
            client = Client(
                self.config['sms']['twilio_account_sid'],
                self.config['sms']['twilio_auth_token']
            )
            
            sms = client.messages.create(
                body=message,
                from_=self.config['sms']['twilio_phone_number'],
                to=recipient_info['phone']
            )
            
            # Log notification
            self._log_notification(
                recipient_info['type'], recipient_info['id'], recipient_info['phone'],
                notification_type, 'sms', '', message, 'sent'
            )
            
            logger.info(f"SMS sent to {recipient_info['phone']}")
            return True
            
        except Exception as e:
            self._log_notification(
                recipient_info['type'], recipient_info['id'], recipient_info['phone'],
                notification_type, 'sms', '', message if 'message' in locals() else '',
                'failed', str(e)
            )
            logger.error(f"Failed to send SMS: {str(e)}")
            return False
    
    def _send_whatsapp_notification(self, recipient_info, notification_type, template_data):
        """Send WhatsApp notification"""
        try:
            if not self.config['whatsapp']['enabled']:
                return False
            
            # Ensure models are available
            self._ensure_models_available()
            
            # Get template (use SMS template for WhatsApp)
            template = self.NotificationTemplate.query.filter_by(
                name=f"{notification_type}_sms",
                type='sms',
                is_active=True
            ).first()
            
            if not template:
                template = self.NotificationTemplate.query.filter_by(
                    name=notification_type,
                    type='sms',
                    is_active=True
                ).first()
            
            if not template:
                logger.error(f"WhatsApp template not found: {notification_type}")
                return False
            
            # Render template
            message = self._render_template(template.body_template, template_data)
            
            # Send WhatsApp using Twilio
            client = Client(
                self.config['whatsapp']['twilio_account_sid'],
                self.config['whatsapp']['twilio_auth_token']
            )
            
            whatsapp_msg = client.messages.create(
                body=message,
                from_=self.config['whatsapp']['whatsapp_number'],
                to=f"whatsapp:{recipient_info['phone']}"
            )
            
            # Log notification
            self._log_notification(
                recipient_info['type'], recipient_info['id'], recipient_info['phone'],
                notification_type, 'whatsapp', '', message, 'sent'
            )
            
            logger.info(f"WhatsApp sent to {recipient_info['phone']}")
            return True
            
        except Exception as e:
            self._log_notification(
                recipient_info['type'], recipient_info['id'], recipient_info['phone'],
                notification_type, 'whatsapp', '', message if 'message' in locals() else '',
                'failed', str(e)
            )
            logger.error(f"Failed to send WhatsApp: {str(e)}")
            return False
    
    def _send_push_notification(self, recipient_info, notification_type, template_data):
        """Send push notification"""
        try:
            if not self.config['push']['enabled']:
                return False
            
            # This would integrate with Firebase Cloud Messaging or similar service
            # Implementation depends on your push notification service
            
            logger.info(f"Push notification would be sent to user {recipient_info['id']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send push notification: {str(e)}")
            return False
    
    # ==================== AUTOMATED REMINDERS ====================
    
    def schedule_appointment_reminders(self):
        """Schedule appointment reminders"""
        try:
            # Ensure models are available and import within app context
            with self.app.app_context():
                self._ensure_models_available()
                from web_app import WebAppointment, WebPatient
                
                # Get upcoming appointments
                reminder_hours = self.config['reminders']['appointment_reminder_hours']
                
                for hours in reminder_hours:
                    reminder_time = datetime.utcnow() + timedelta(hours=hours)
                    start_time = reminder_time - timedelta(minutes=30)
                    end_time = reminder_time + timedelta(minutes=30)
                    
                    appointments = WebAppointment.query.filter(
                        WebAppointment.appointment_date.between(start_time, end_time),
                        WebAppointment.status == 'scheduled'
                    ).all()
                    
                    for appointment in appointments:
                        # Check if reminder already scheduled
                        existing_reminder = self.ScheduledNotification.query.filter_by(
                            recipient_type='patient',
                            recipient_id=appointment.patient_id,
                            notification_type='appointment_reminder',
                            status='pending'
                        ).first()
                        
                        if not existing_reminder:
                            template_data = {
                                'patient_name': f"{appointment.patient.first_name} {appointment.patient.last_name}",
                                'appointment_date': appointment.appointment_date.strftime('%Y-%m-%d'),
                                'appointment_time': appointment.appointment_date.strftime('%H:%M'),
                                'doctor_name': appointment.doctor.full_name if appointment.doctor else 'TBD',
                                'department': appointment.doctor.department if appointment.doctor else 'General',
                                'hospital_phone': '+1-234-567-8900',  # Configure
                                'hospital_name': 'MediCare Pro Hospital'  # Configure
                            }
                            
                            scheduled_notification = self.ScheduledNotification(
                                recipient_type='patient',
                                recipient_id=appointment.patient_id,
                                notification_type='appointment_reminder',
                                scheduled_time=reminder_time,
                                template_data=json.dumps(template_data)
                            )
                            
                            self.db.session.add(scheduled_notification)
                
                self.db.session.commit()
                logger.info("Appointment reminders scheduled")
            
        except Exception as e:
            logger.error(f"Failed to schedule appointment reminders: {str(e)}")
            self.db.session.rollback()
    
    def schedule_bill_reminders(self):
        """Schedule bill payment reminders"""
        try:
            # Ensure models are available and import within app context
            with self.app.app_context():
                self._ensure_models_available()
                from web_app import Bill
                
                reminder_days = self.config['reminders']['bill_reminder_days']
                
                for days in reminder_days:
                    due_date = datetime.utcnow() + timedelta(days=days)
                    start_date = due_date.replace(hour=0, minute=0, second=0, microsecond=0)
                    end_date = due_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                    
                    # Get bills due in specified days
                    bills = Bill.query.filter(
                        Bill.bill_date.between(start_date, end_date),
                        Bill.payment_status.in_(['pending', 'partial'])
                    ).all()
                    
                    for bill in bills:
                        template_data = {
                            'patient_name': f"{bill.patient.first_name} {bill.patient.last_name}",
                            'bill_number': bill.bill_number,
                            'amount_due': f"${bill.balance_amount:.2f}",
                            'due_date': bill.bill_date.strftime('%Y-%m-%d'),
                            'billing_phone': '+1-234-567-8901',  # Configure
                            'hospital_name': 'MediCare Pro Hospital'  # Configure
                        }
                        
                        scheduled_notification = self.ScheduledNotification(
                            recipient_type='patient',
                            recipient_id=bill.patient_id,
                            notification_type='bill_reminder',
                            scheduled_time=datetime.utcnow() + timedelta(hours=1),  # Send soon
                            template_data=json.dumps(template_data)
                        )
                        
                        self.db.session.add(scheduled_notification)
                
                self.db.session.commit()
                logger.info("Bill reminders scheduled")
            
        except Exception as e:
            logger.error(f"Failed to schedule bill reminders: {str(e)}")
            self.db.session.rollback()
    
    def process_scheduled_notifications(self):
        """Process pending scheduled notifications"""
        try:
            with self.app.app_context():
                self._ensure_models_available()
                current_time = datetime.utcnow()
                
                pending_notifications = self.ScheduledNotification.query.filter(
                self.ScheduledNotification.scheduled_time <= current_time,
                self.ScheduledNotification.status == 'pending'
            ).all()
            
            for notification in pending_notifications:
                try:
                    template_data = json.loads(notification.template_data) if notification.template_data else {}
                    
                    success = self.send_notification(
                        notification.recipient_type,
                        notification.recipient_id,
                        notification.notification_type,
                        template_data
                    )
                    
                    notification.status = 'sent' if success else 'failed'
                    
                except Exception as e:
                    logger.error(f"Failed to process scheduled notification {notification.id}: {str(e)}")
                    notification.status = 'failed'
            
            self.db.session.commit()
            logger.info(f"Processed {len(pending_notifications)} scheduled notifications")
            
        except Exception as e:
            logger.error(f"Failed to process scheduled notifications: {str(e)}")
            self.db.session.rollback()
    
    # ==================== UTILITY METHODS ====================
    
    def _get_recipient_info(self, recipient_type, recipient_id):
        """Get recipient contact information"""
        try:
            with self.app.app_context():
                if recipient_type == 'patient':
                    from web_app import WebPatient
                    patient = self.db.session.get(WebPatient, recipient_id)
                    if patient:
                        return {
                            'type': 'patient',
                            'id': patient.id,
                            'name': f"{patient.first_name} {patient.last_name}",
                            'email': patient.email,
                            'phone': patient.phone
                        }
                
                elif recipient_type in ['staff', 'doctor']:
                    from web_app import WebUser
                    user = self.db.session.get(WebUser, recipient_id)
                    if user:
                        return {
                            'type': 'staff',
                            'id': user.id,
                            'name': user.full_name,
                            'email': user.email,
                            'phone': user.phone
                        }
                
                return None
            
        except Exception as e:
            logger.error(f"Failed to get recipient info: {str(e)}")
            return None
    
    def _get_notification_preferences(self, user_id, user_type, notification_type):
        """Get user notification preferences"""
        try:
            # Ensure models are available
            self._ensure_models_available()
            
            preference = self.NotificationPreference.query.filter_by(
                user_id=user_id,
                user_type=user_type,
                notification_type=notification_type
            ).first()
            
            if preference:
                return {
                    'email_enabled': preference.email_enabled,
                    'sms_enabled': preference.sms_enabled,
                    'whatsapp_enabled': preference.whatsapp_enabled,
                    'push_enabled': preference.push_enabled
                }
            else:
                # Return default preferences
                return {
                    'email_enabled': True,
                    'sms_enabled': False,
                    'whatsapp_enabled': False,
                    'push_enabled': True
                }
                
        except Exception as e:
            logger.error(f"Failed to get notification preferences: {str(e)}")
            return {'email_enabled': True, 'sms_enabled': False, 'whatsapp_enabled': False, 'push_enabled': True}
    
    def _render_template(self, template_string, data):
        """Render template with data"""
        try:
            if not template_string or not data:
                return template_string
            
            template = Template(template_string)
            return template.render(**data)
            
        except Exception as e:
            logger.error(f"Failed to render template: {str(e)}")
            return template_string
    
    def _log_notification(self, recipient_type, recipient_id, recipient_contact,
                         notification_type, channel, subject, message, status, error_message=None):
        """Log notification attempt"""
        try:
            # Ensure models are available
            self._ensure_models_available()
            
            log_entry = self.NotificationLog(
                recipient_type=recipient_type,
                recipient_id=recipient_id,
                recipient_contact=recipient_contact,
                notification_type=notification_type,
                channel=channel,
                subject=subject,
                message=message,
                status=status,
                sent_at=datetime.utcnow() if status == 'sent' else None,
                error_message=error_message
            )
            
            self.db.session.add(log_entry)
            self.db.session.commit()
            
        except Exception as e:
            logger.error(f"Failed to log notification: {str(e)}")
    
    def start_notification_scheduler(self):
        """Start the notification scheduler"""
        # Temporarily disable automatic scheduler to prevent SQLAlchemy context issues
        # The scheduler functions can still be called manually from the web interface
        logger.info("Notification scheduler started (manual mode - automatic scheduling disabled)")
    
    def get_notification_statistics(self, days=30):
        """Get notification statistics"""
        try:
            # Ensure models are available
            self._ensure_models_available()
            
            start_date = datetime.utcnow() - timedelta(days=days)
            
            logs = self.NotificationLog.query.filter(
                self.NotificationLog.created_at >= start_date
            ).all()
            
            stats = {
                'total_notifications': len(logs),
                'successful_notifications': len([l for l in logs if l.status == 'sent']),
                'failed_notifications': len([l for l in logs if l.status == 'failed']),
                'channel_breakdown': {},
                'type_breakdown': {},
                'success_rate': 0
            }
            
            # Channel breakdown
            for log in logs:
                channel = log.channel
                if channel not in stats['channel_breakdown']:
                    stats['channel_breakdown'][channel] = {'total': 0, 'successful': 0}
                
                stats['channel_breakdown'][channel]['total'] += 1
                if log.status == 'sent':
                    stats['channel_breakdown'][channel]['successful'] += 1
            
            # Type breakdown
            for log in logs:
                ntype = log.notification_type
                if ntype not in stats['type_breakdown']:
                    stats['type_breakdown'][ntype] = {'total': 0, 'successful': 0}
                
                stats['type_breakdown'][ntype]['total'] += 1
                if log.status == 'sent':
                    stats['type_breakdown'][ntype]['successful'] += 1
            
            # Success rate
            if stats['total_notifications'] > 0:
                stats['success_rate'] = (stats['successful_notifications'] / stats['total_notifications']) * 100
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get notification statistics: {str(e)}")
            return None

def init_notification_system(app, db):
    """Initialize notification system with Flask app"""
    notification_system = NotificationSystem(db, app)
    
    # Add to app
    app.notification_system = notification_system
    
    # Don't start scheduler immediately - it will be started after app is fully initialized
    # notification_system.start_notification_scheduler()
    
    return notification_system
