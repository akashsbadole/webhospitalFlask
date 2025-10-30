#!/usr/bin/env python3
"""
Emergency Management System
Handles emergency triage, code alerts, emergency contacts, trauma registry, and ambulance tracking
"""

import json
import logging
from datetime import datetime, timedelta
from flask import current_app, request, session
from flask_login import current_user
import threading
import time
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmergencyLevel(Enum):
    GREEN = "green"      # Non-urgent
    YELLOW = "yellow"    # Less urgent
    ORANGE = "orange"    # Urgent
    RED = "red"          # Very urgent
    BLACK = "black"      # Deceased/Expectant

class CodeType(Enum):
    BLUE = "blue"        # Cardiac arrest
    RED = "red"          # Fire
    GRAY = "gray"        # Combative person
    SILVER = "silver"    # Weapon/hostage
    WHITE = "white"      # Pediatric emergency
    YELLOW = "yellow"    # Bomb threat
    GREEN = "green"      # Emergency activation
    BROWN = "brown"      # Hazardous material

class EmergencyManagement:
    def __init__(self, db, app):
        self.db = db
        self.app = app
        self.setup_emergency_tables()
        
        # Active alerts and notifications
        self.active_alerts = {}
        self.notification_subscribers = []
        
        # Configuration
        self.config = {
            'triage_auto_assign': True,
            'alert_timeout_minutes': 60,
            'ambulance_tracking_enabled': True,
            'auto_notify_contacts': True,
            'trauma_registry_enabled': True
        }
    
    def setup_emergency_tables(self):
        """Create emergency management tables"""
        
        class EmergencyCase(self.db.Model):
            __tablename__ = 'emergency_cases'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            case_number = self.db.Column(self.db.String(50), unique=True, nullable=False)
            patient_id = self.db.Column(self.db.Integer, self.db.ForeignKey('web_patient.id'))
            
            # Triage information
            triage_level = self.db.Column(self.db.String(10), nullable=False)  # green, yellow, orange, red, black
            chief_complaint = self.db.Column(self.db.Text)
            vital_signs = self.db.Column(self.db.Text)  # JSON
            triage_notes = self.db.Column(self.db.Text)
            
            # Assignment
            assigned_doctor = self.db.Column(self.db.Integer, self.db.ForeignKey('web_user.id'))
            assigned_nurse = self.db.Column(self.db.Integer, self.db.ForeignKey('web_user.id'))
            bed_assignment = self.db.Column(self.db.String(20))
            
            # Status tracking
            status = self.db.Column(self.db.String(20), default='active')  # active, treating, discharged, admitted, deceased
            arrival_method = self.db.Column(self.db.String(20))  # ambulance, walk-in, helicopter, transfer
            
            # Timestamps
            arrival_time = self.db.Column(self.db.DateTime, default=datetime.utcnow)
            triage_time = self.db.Column(self.db.DateTime)
            treatment_start_time = self.db.Column(self.db.DateTime)
            disposition_time = self.db.Column(self.db.DateTime)
            
            # Trauma registry fields
            is_trauma = self.db.Column(self.db.Boolean, default=False)
            injury_mechanism = self.db.Column(self.db.String(100))
            injury_severity_score = self.db.Column(self.db.Integer)
            
            # Relationships
            patient = self.db.relationship('WebPatient', foreign_keys=[patient_id], backref='emergency_cases')
            doctor = self.db.relationship('WebUser', foreign_keys=[assigned_doctor])
            nurse = self.db.relationship('WebUser', foreign_keys=[assigned_nurse])
        
        class CodeAlert(self.db.Model):
            __tablename__ = 'code_alerts'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            alert_id = self.db.Column(self.db.String(50), unique=True, nullable=False)
            code_type = self.db.Column(self.db.String(20), nullable=False)
            location = self.db.Column(self.db.String(100), nullable=False)
            
            # Alert details
            description = self.db.Column(self.db.Text)
            severity = self.db.Column(self.db.String(20), default='high')
            
            # Status
            status = self.db.Column(self.db.String(20), default='active')  # active, responding, resolved, cancelled
            
            # Personnel
            initiated_by = self.db.Column(self.db.Integer, self.db.ForeignKey('web_user.id'))
            response_team = self.db.Column(self.db.Text)  # JSON array of user IDs
            
            # Timestamps
            created_at = self.db.Column(self.db.DateTime, default=datetime.utcnow)
            response_time = self.db.Column(self.db.DateTime)
            resolved_time = self.db.Column(self.db.DateTime)
            
            # Relationships
            initiator = self.db.relationship('WebUser', backref='initiated_alerts')
        
        class EmergencyContact(self.db.Model):
            __tablename__ = 'emergency_contacts'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            patient_id = self.db.Column(self.db.Integer, self.db.ForeignKey('web_patient.id'), nullable=False)
            
            # Contact information
            name = self.db.Column(self.db.String(100), nullable=False)
            relationship = self.db.Column(self.db.String(50))
            phone_primary = self.db.Column(self.db.String(20), nullable=False)
            phone_secondary = self.db.Column(self.db.String(20))
            email = self.db.Column(self.db.String(120))
            address = self.db.Column(self.db.Text)
            
            # Preferences
            is_primary = self.db.Column(self.db.Boolean, default=False)
            notification_preference = self.db.Column(self.db.String(20), default='phone')  # phone, sms, email
            
            # Relationships
            patient = self.db.relationship('WebPatient', backref='emergency_contacts')
        
        class AmbulanceUnit(self.db.Model):
            __tablename__ = 'ambulance_units'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            unit_number = self.db.Column(self.db.String(20), unique=True, nullable=False)
            vehicle_type = self.db.Column(self.db.String(20))  # basic, advanced, critical_care
            
            # Equipment and capabilities
            equipment_list = self.db.Column(self.db.Text)  # JSON
            medical_capabilities = self.db.Column(self.db.Text)  # JSON
            
            # Status
            status = self.db.Column(self.db.String(20), default='available')  # available, dispatched, en_route, at_scene, returning, maintenance
            current_location = self.db.Column(self.db.String(200))
            
            # Crew
            crew_members = self.db.Column(self.db.Text)  # JSON array of staff IDs
            
            # Tracking
            gps_coordinates = self.db.Column(self.db.String(50))  # lat,lng
            last_update = self.db.Column(self.db.DateTime, default=datetime.utcnow)
            
            # Maintenance
            last_maintenance = self.db.Column(self.db.Date)
            next_maintenance = self.db.Column(self.db.Date)
            is_active = self.db.Column(self.db.Boolean, default=True)
        
        class AmbulanceDispatch(self.db.Model):
            __tablename__ = 'ambulance_dispatches'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            dispatch_id = self.db.Column(self.db.String(50), unique=True, nullable=False)
            ambulance_id = self.db.Column(self.db.Integer, self.db.ForeignKey('ambulance_units.id'), nullable=False)
            
            # Incident details
            incident_location = self.db.Column(self.db.String(200), nullable=False)
            incident_type = self.db.Column(self.db.String(100))
            priority = self.db.Column(self.db.String(20), default='normal')  # low, normal, high, critical
            
            # Patient information (if known)
            patient_id = self.db.Column(self.db.Integer, self.db.ForeignKey('web_patient.id'))
            patient_condition = self.db.Column(self.db.Text)
            
            # Status tracking
            status = self.db.Column(self.db.String(20), default='dispatched')  # dispatched, en_route, at_scene, transporting, completed, cancelled
            
            # Timestamps
            dispatch_time = self.db.Column(self.db.DateTime, default=datetime.utcnow)
            arrival_time = self.db.Column(self.db.DateTime)
            departure_time = self.db.Column(self.db.DateTime)
            hospital_arrival_time = self.db.Column(self.db.DateTime)
            
            # Dispatcher
            dispatched_by = self.db.Column(self.db.Integer, self.db.ForeignKey('web_user.id'))
            
            # Relationships
            ambulance = self.db.relationship('AmbulanceUnit', backref='dispatches')
            patient = self.db.relationship('WebPatient', backref='ambulance_calls')
            dispatcher = self.db.relationship('WebUser', backref='dispatched_ambulances')
        
        class TraumaRegistry(self.db.Model):
            __tablename__ = 'trauma_registry'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            emergency_case_id = self.db.Column(self.db.Integer, self.db.ForeignKey('emergency_cases.id'), nullable=False)
            
            # Injury details
            mechanism_of_injury = self.db.Column(self.db.String(100))
            injury_location = self.db.Column(self.db.String(200))
            injury_time = self.db.Column(self.db.DateTime)
            
            # Severity scores
            glasgow_coma_scale = self.db.Column(self.db.Integer)
            injury_severity_score = self.db.Column(self.db.Integer)
            revised_trauma_score = self.db.Column(self.db.Float)
            
            # Interventions
            interventions_performed = self.db.Column(self.db.Text)  # JSON
            blood_products_used = self.db.Column(self.db.Text)  # JSON
            
            # Outcome
            disposition = self.db.Column(self.db.String(50))  # discharged, admitted, transferred, deceased
            length_of_stay = self.db.Column(self.db.Integer)  # hours
            complications = self.db.Column(self.db.Text)
            
            # Relationships
            emergency_case = self.db.relationship('EmergencyCase', backref='trauma_registry')
        
        # Store model classes
        self.EmergencyCase = EmergencyCase
        self.CodeAlert = CodeAlert
        self.EmergencyContact = EmergencyContact
        self.AmbulanceUnit = AmbulanceUnit
        self.AmbulanceDispatch = AmbulanceDispatch
        self.TraumaRegistry = TraumaRegistry
        
        # Create tables
        self.db.create_all()
        self._create_default_ambulances()
    
    def _create_default_ambulances(self):
        """Create default ambulance units"""
        default_ambulances = [
            {
                'unit_number': 'AMB001',
                'vehicle_type': 'advanced',
                'equipment_list': json.dumps([
                    'Defibrillator', 'Ventilator', 'Cardiac Monitor', 'IV Pumps',
                    'Oxygen', 'Stretcher', 'Immobilization Equipment'
                ]),
                'medical_capabilities': json.dumps([
                    'Advanced Life Support', 'Cardiac Care', 'Trauma Care'
                ])
            },
            {
                'unit_number': 'AMB002',
                'vehicle_type': 'basic',
                'equipment_list': json.dumps([
                    'Basic Monitoring', 'Oxygen', 'Stretcher', 'First Aid Kit'
                ]),
                'medical_capabilities': json.dumps([
                    'Basic Life Support', 'Patient Transport'
                ])
            }
        ]
        
        for amb_data in default_ambulances:
            existing = self.AmbulanceUnit.query.filter_by(unit_number=amb_data['unit_number']).first()
            if not existing:
                ambulance = self.AmbulanceUnit(**amb_data)
                self.db.session.add(ambulance)
        
        try:
            self.db.session.commit()
        except Exception as e:
            logger.error(f"Failed to create default ambulances: {str(e)}")
            self.db.session.rollback()
    
    # ==================== EMERGENCY TRIAGE ====================
    
    def create_emergency_case(self, patient_id, chief_complaint, vital_signs=None, 
                            arrival_method='walk-in', is_trauma=False):
        """Create new emergency case"""
        try:
            # Generate case number
            case_number = self._generate_case_number()
            
            # Perform initial triage assessment
            triage_level = self._assess_triage_level(chief_complaint, vital_signs)
            
            # Create emergency case
            emergency_case = self.EmergencyCase(
                case_number=case_number,
                patient_id=patient_id,
                triage_level=triage_level.value,
                chief_complaint=chief_complaint,
                vital_signs=json.dumps(vital_signs) if vital_signs else None,
                arrival_method=arrival_method,
                is_trauma=is_trauma,
                triage_time=datetime.utcnow()
            )
            
            # Auto-assign if enabled
            if self.config['triage_auto_assign']:
                self._auto_assign_staff(emergency_case)
            
            self.db.session.add(emergency_case)
            self.db.session.commit()
            
            # Notify emergency team if high priority
            if triage_level in [EmergencyLevel.RED, EmergencyLevel.ORANGE]:
                self._notify_emergency_team(emergency_case)
            
            # Create trauma registry entry if trauma case
            if is_trauma:
                self._create_trauma_registry_entry(emergency_case.id)
            
            logger.info(f"Emergency case created: {case_number} - {triage_level.value}")
            return emergency_case
            
        except Exception as e:
            logger.error(f"Failed to create emergency case: {str(e)}")
            raise
    
    def _assess_triage_level(self, chief_complaint, vital_signs):
        """Assess triage level based on complaint and vitals"""
        # This is a simplified triage algorithm
        # In production, this would be more sophisticated
        
        high_priority_keywords = [
            'chest pain', 'difficulty breathing', 'unconscious', 'severe bleeding',
            'cardiac arrest', 'stroke', 'severe trauma', 'overdose'
        ]
        
        medium_priority_keywords = [
            'abdominal pain', 'fever', 'vomiting', 'headache', 'injury'
        ]
        
        complaint_lower = chief_complaint.lower()
        
        # Check for high priority conditions
        for keyword in high_priority_keywords:
            if keyword in complaint_lower:
                return EmergencyLevel.RED
        
        # Check vital signs if available
        if vital_signs:
            systolic_bp = vital_signs.get('systolic_bp', 0)
            heart_rate = vital_signs.get('heart_rate', 0)
            respiratory_rate = vital_signs.get('respiratory_rate', 0)
            temperature = vital_signs.get('temperature', 98.6)
            
            # Critical vital signs
            if (systolic_bp < 90 or systolic_bp > 180 or
                heart_rate < 50 or heart_rate > 120 or
                respiratory_rate < 10 or respiratory_rate > 30 or
                temperature > 103):
                return EmergencyLevel.ORANGE
        
        # Check for medium priority conditions
        for keyword in medium_priority_keywords:
            if keyword in complaint_lower:
                return EmergencyLevel.YELLOW
        
        # Default to low priority
        return EmergencyLevel.GREEN
    
    def _auto_assign_staff(self, emergency_case):
        """Auto-assign available staff based on triage level"""
        try:
            from web_app import WebUser
            
            # Find available emergency doctors
            available_doctors = WebUser.query.filter(
                WebUser.role == 'doctor',
                WebUser.department == 'Emergency',
                WebUser.is_active == True
            ).all()
            
            # Find available nurses
            available_nurses = WebUser.query.filter(
                WebUser.role == 'nurse',
                WebUser.department == 'Emergency',
                WebUser.is_active == True
            ).all()
            
            # Simple assignment logic - assign first available
            if available_doctors:
                emergency_case.assigned_doctor = available_doctors[0].id
            
            if available_nurses:
                emergency_case.assigned_nurse = available_nurses[0].id
            
        except Exception as e:
            logger.error(f"Failed to auto-assign staff: {str(e)}")
    
    def update_triage_level(self, case_id, new_level, notes=None):
        """Update triage level for existing case"""
        try:
            emergency_case = self.db.session.get(self.EmergencyCase, case_id)
            if not emergency_case:
                raise ValueError("Emergency case not found")
            
            old_level = emergency_case.triage_level
            emergency_case.triage_level = new_level
            
            if notes:
                current_notes = emergency_case.triage_notes or ""
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                emergency_case.triage_notes = f"{current_notes}\n[{timestamp}] Triage updated from {old_level} to {new_level}: {notes}"
            
            self.db.session.commit()
            
            # Notify if escalated to high priority
            if new_level in ['red', 'orange'] and old_level not in ['red', 'orange']:
                self._notify_emergency_team(emergency_case)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update triage level: {str(e)}")
            return False
    
    # ==================== CODE ALERTS ====================
    
    def activate_code_alert(self, code_type, location, description=None):
        """Activate emergency code alert"""
        try:
            # Generate alert ID
            alert_id = self._generate_alert_id()
            
            # Create code alert
            code_alert = self.CodeAlert(
                alert_id=alert_id,
                code_type=code_type,
                location=location,
                description=description,
                initiated_by=current_user.id if current_user.is_authenticated else None
            )
            
            self.db.session.add(code_alert)
            self.db.session.commit()
            
            # Store in active alerts
            self.active_alerts[alert_id] = {
                'code_type': code_type,
                'location': location,
                'description': description,
                'created_at': datetime.utcnow(),
                'status': 'active'
            }
            
            # Broadcast alert to all connected clients
            self._broadcast_code_alert(code_alert)
            
            # Auto-resolve after timeout
            self._schedule_alert_timeout(alert_id)
            
            logger.warning(f"Code {code_type.upper()} activated at {location}")
            return alert_id
            
        except Exception as e:
            logger.error(f"Failed to activate code alert: {str(e)}")
            raise
    
    def resolve_code_alert(self, alert_id, resolution_notes=None):
        """Resolve active code alert"""
        try:
            code_alert = self.CodeAlert.query.filter_by(alert_id=alert_id).first()
            if not code_alert:
                raise ValueError("Alert not found")
            
            code_alert.status = 'resolved'
            code_alert.resolved_time = datetime.utcnow()
            
            if resolution_notes:
                code_alert.description = f"{code_alert.description}\n\nResolution: {resolution_notes}"
            
            self.db.session.commit()
            
            # Remove from active alerts
            if alert_id in self.active_alerts:
                del self.active_alerts[alert_id]
            
            # Broadcast resolution
            self._broadcast_alert_resolution(alert_id)
            
            logger.info(f"Code alert {alert_id} resolved")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resolve code alert: {str(e)}")
            return False
    
    def _broadcast_code_alert(self, code_alert):
        """Broadcast code alert to all subscribers"""
        alert_data = {
            'type': 'code_alert',
            'alert_id': code_alert.alert_id,
            'code_type': code_alert.code_type,
            'location': code_alert.location,
            'description': code_alert.description,
            'timestamp': code_alert.created_at.isoformat()
        }
        
        # In a real implementation, this would use WebSockets or similar
        # For now, we'll just log and store for polling
        logger.info(f"Broadcasting alert: {json.dumps(alert_data)}")
    
    def _schedule_alert_timeout(self, alert_id):
        """Schedule automatic alert resolution after timeout"""
        def timeout_alert():
            time.sleep(self.config['alert_timeout_minutes'] * 60)
            if alert_id in self.active_alerts:
                self.resolve_code_alert(alert_id, "Auto-resolved after timeout")
        
        timeout_thread = threading.Thread(target=timeout_alert, daemon=True)
        timeout_thread.start()
    
    # ==================== AMBULANCE MANAGEMENT ====================
    
    def dispatch_ambulance(self, incident_location, incident_type, priority='normal', 
                          patient_id=None, patient_condition=None):
        """Dispatch ambulance to incident"""
        try:
            # Find available ambulance
            available_ambulance = self.AmbulanceUnit.query.filter_by(
                status='available',
                is_active=True
            ).first()
            
            if not available_ambulance:
                raise ValueError("No ambulances available")
            
            # Generate dispatch ID
            dispatch_id = self._generate_dispatch_id()
            
            # Create dispatch record
            dispatch = self.AmbulanceDispatch(
                dispatch_id=dispatch_id,
                ambulance_id=available_ambulance.id,
                incident_location=incident_location,
                incident_type=incident_type,
                priority=priority,
                patient_id=patient_id,
                patient_condition=patient_condition,
                dispatched_by=current_user.id if current_user.is_authenticated else None
            )
            
            # Update ambulance status
            available_ambulance.status = 'dispatched'
            
            self.db.session.add(dispatch)
            self.db.session.commit()
            
            # Notify ambulance crew
            self._notify_ambulance_crew(available_ambulance, dispatch)
            
            logger.info(f"Ambulance {available_ambulance.unit_number} dispatched to {incident_location}")
            return dispatch_id
            
        except Exception as e:
            logger.error(f"Failed to dispatch ambulance: {str(e)}")
            raise
    
    def update_ambulance_status(self, unit_number, status, location=None, gps_coordinates=None):
        """Update ambulance status and location"""
        try:
            ambulance = self.AmbulanceUnit.query.filter_by(unit_number=unit_number).first()
            if not ambulance:
                raise ValueError("Ambulance not found")
            
            ambulance.status = status
            ambulance.last_update = datetime.utcnow()
            
            if location:
                ambulance.current_location = location
            
            if gps_coordinates:
                ambulance.gps_coordinates = gps_coordinates
            
            # Update dispatch status if applicable
            if status in ['at_scene', 'transporting', 'returning']:
                active_dispatch = self.AmbulanceDispatch.query.filter_by(
                    ambulance_id=ambulance.id,
                    status__in=['dispatched', 'en_route', 'at_scene']
                ).first()
                
                if active_dispatch:
                    if status == 'at_scene' and not active_dispatch.arrival_time:
                        active_dispatch.arrival_time = datetime.utcnow()
                        active_dispatch.status = 'at_scene'
                    elif status == 'transporting':
                        active_dispatch.departure_time = datetime.utcnow()
                        active_dispatch.status = 'transporting'
                    elif status == 'returning':
                        active_dispatch.hospital_arrival_time = datetime.utcnow()
                        active_dispatch.status = 'completed'
                        ambulance.status = 'available'  # Make available again
            
            self.db.session.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update ambulance status: {str(e)}")
            return False
    
    # ==================== EMERGENCY CONTACTS ====================
    
    def notify_emergency_contacts(self, patient_id, message, notification_type='emergency'):
        """Notify patient's emergency contacts"""
        try:
            contacts = self.EmergencyContact.query.filter_by(
                patient_id=patient_id
            ).order_by(self.EmergencyContact.is_primary.desc()).all()
            
            notifications_sent = 0
            
            for contact in contacts:
                try:
                    if contact.notification_preference == 'phone':
                        # This would integrate with your phone system
                        logger.info(f"Would call {contact.phone_primary} for {contact.name}")
                        notifications_sent += 1
                    
                    elif contact.notification_preference == 'sms':
                        # This would integrate with SMS service
                        logger.info(f"Would send SMS to {contact.phone_primary} for {contact.name}")
                        notifications_sent += 1
                    
                    elif contact.notification_preference == 'email' and contact.email:
                        # This would integrate with email service
                        logger.info(f"Would send email to {contact.email} for {contact.name}")
                        notifications_sent += 1
                
                except Exception as e:
                    logger.error(f"Failed to notify contact {contact.name}: {str(e)}")
            
            return notifications_sent
            
        except Exception as e:
            logger.error(f"Failed to notify emergency contacts: {str(e)}")
            return 0
    
    # ==================== UTILITY METHODS ====================
    
    def _generate_case_number(self):
        """Generate unique emergency case number"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return f"EM{timestamp}"
    
    def _generate_alert_id(self):
        """Generate unique alert ID"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return f"ALERT{timestamp}"
    
    def _generate_dispatch_id(self):
        """Generate unique dispatch ID"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return f"DISP{timestamp}"
    
    def _notify_emergency_team(self, emergency_case):
        """Notify emergency team of high-priority case"""
        # This would integrate with your notification system
        logger.info(f"Notifying emergency team of {emergency_case.triage_level} case: {emergency_case.case_number}")
    
    def _notify_ambulance_crew(self, ambulance, dispatch):
        """Notify ambulance crew of dispatch"""
        # This would integrate with mobile devices/radios
        logger.info(f"Notifying crew of {ambulance.unit_number} of dispatch to {dispatch.incident_location}")
    
    def _create_trauma_registry_entry(self, emergency_case_id):
        """Create trauma registry entry"""
        try:
            trauma_entry = self.TraumaRegistry(
                emergency_case_id=emergency_case_id
            )
            
            self.db.session.add(trauma_entry)
            self.db.session.commit()
            
        except Exception as e:
            logger.error(f"Failed to create trauma registry entry: {str(e)}")
    
    def get_emergency_dashboard_data(self):
        """Get data for emergency dashboard"""
        try:
            # Active emergency cases
            active_cases = self.EmergencyCase.query.filter_by(status='active').all()
            
            # Cases by triage level
            triage_counts = {}
            for level in EmergencyLevel:
                count = self.EmergencyCase.query.filter_by(
                    triage_level=level.value,
                    status='active'
                ).count()
                triage_counts[level.value] = count
            
            # Active code alerts
            active_alerts_list = list(self.active_alerts.values())
            
            # Ambulance status
            ambulances = self.AmbulanceUnit.query.filter_by(is_active=True).all()
            ambulance_status = {}
            for ambulance in ambulances:
                ambulance_status[ambulance.status] = ambulance_status.get(ambulance.status, 0) + 1
            
            # Recent dispatches
            recent_dispatches = self.AmbulanceDispatch.query.filter(
                self.AmbulanceDispatch.dispatch_time >= datetime.utcnow() - timedelta(hours=24)
            ).order_by(self.AmbulanceDispatch.dispatch_time.desc()).limit(10).all()
            
            return {
                'active_cases_count': len(active_cases),
                'triage_counts': triage_counts,
                'active_alerts': active_alerts_list,
                'ambulance_status': ambulance_status,
                'recent_dispatches': [
                    {
                        'dispatch_id': d.dispatch_id,
                        'location': d.incident_location,
                        'priority': d.priority,
                        'status': d.status,
                        'dispatch_time': d.dispatch_time.isoformat()
                    }
                    for d in recent_dispatches
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get emergency dashboard data: {str(e)}")
            return {}

def init_emergency_management(app, db):
    """Initialize emergency management system"""
    return EmergencyManagement(db, app)