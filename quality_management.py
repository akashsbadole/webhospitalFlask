#!/usr/bin/env python3
"""
Quality Management & Accreditation System
Handles incident reporting, patient feedback, complaints, clinical protocols, and quality metrics
"""

import json
import logging
from datetime import datetime, timedelta, date
from flask import current_app, request
from flask_login import current_user
from enum import Enum
import statistics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IncidentSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ComplaintStatus(Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"

class QualityMetricType(Enum):
    PATIENT_SATISFACTION = "patient_satisfaction"
    INFECTION_RATE = "infection_rate"
    READMISSION_RATE = "readmission_rate"
    MORTALITY_RATE = "mortality_rate"
    WAIT_TIME = "wait_time"
    LENGTH_OF_STAY = "length_of_stay"

class QualityManagement:
    def __init__(self, db, app):
        self.db = db
        self.app = app
        self.setup_quality_tables()
        
        # Configuration
        self.config = {
            'incident_auto_escalation': True,
            'feedback_anonymous_allowed': True,
            'complaint_sla_hours': 48,
            'quality_review_frequency_days': 30,
            'accreditation_standards': ['NABH', 'JCI', 'ISO'],
            'patient_satisfaction_target': 4.0,  # Out of 5
            'infection_rate_target': 2.0,  # Percentage
            'readmission_rate_target': 10.0  # Percentage
        }
    
    def setup_quality_tables(self):
        """Create quality management tables"""
        
        class IncidentReport(self.db.Model):
            __tablename__ = 'incident_reports'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            incident_number = self.db.Column(self.db.String(50), unique=True, nullable=False)
            
            # Incident details
            title = self.db.Column(self.db.String(200), nullable=False)
            description = self.db.Column(self.db.Text, nullable=False)
            incident_type = self.db.Column(self.db.String(50))  # medication_error, fall, infection, etc.
            severity = self.db.Column(self.db.String(20), nullable=False)
            
            # Location and time
            location = self.db.Column(self.db.String(100))
            department = self.db.Column(self.db.String(50))
            incident_date = self.db.Column(self.db.DateTime, nullable=False)
            
            # People involved
            patient_id = self.db.Column(self.db.Integer, self.db.ForeignKey('web_patient.id'))
            staff_involved = self.db.Column(self.db.Text)  # JSON array of staff IDs
            witnesses = self.db.Column(self.db.Text)  # JSON array of witness info
            
            # Reporting
            reported_by = self.db.Column(self.db.Integer, self.db.ForeignKey('web_user.id'), nullable=False)
            reported_date = self.db.Column(self.db.DateTime, default=datetime.utcnow)
            
            # Investigation
            assigned_investigator = self.db.Column(self.db.Integer, self.db.ForeignKey('web_user.id'))
            investigation_notes = self.db.Column(self.db.Text)
            root_cause = self.db.Column(self.db.Text)
            corrective_actions = self.db.Column(self.db.Text)
            
            # Status tracking
            status = self.db.Column(self.db.String(20), default='open')  # open, investigating, resolved, closed
            resolution_date = self.db.Column(self.db.DateTime)
            
            # Follow-up
            follow_up_required = self.db.Column(self.db.Boolean, default=False)
            follow_up_date = self.db.Column(self.db.Date)
            follow_up_notes = self.db.Column(self.db.Text)
            
            # Relationships
            patient = self.db.relationship('WebPatient', backref='incident_reports')
            reporter = self.db.relationship('WebUser', foreign_keys=[reported_by])
            investigator = self.db.relationship('WebUser', foreign_keys=[assigned_investigator])
        
        class PatientFeedback(self.db.Model):
            __tablename__ = 'patient_feedback'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            feedback_id = self.db.Column(self.db.String(50), unique=True, nullable=False)
            
            # Patient information
            patient_id = self.db.Column(self.db.Integer, self.db.ForeignKey('web_patient.id'))
            is_anonymous = self.db.Column(self.db.Boolean, default=False)
            
            # Feedback details
            feedback_type = self.db.Column(self.db.String(20), default='general')  # general, complaint, compliment, suggestion
            service_area = self.db.Column(self.db.String(50))  # emergency, opd, ipd, pharmacy, etc.
            
            # Ratings (1-5 scale)
            overall_rating = self.db.Column(self.db.Integer)
            staff_behavior_rating = self.db.Column(self.db.Integer)
            facility_rating = self.db.Column(self.db.Integer)
            wait_time_rating = self.db.Column(self.db.Integer)
            treatment_quality_rating = self.db.Column(self.db.Integer)
            
            # Comments
            comments = self.db.Column(self.db.Text)
            suggestions = self.db.Column(self.db.Text)
            
            # Response
            response_required = self.db.Column(self.db.Boolean, default=False)
            response_text = self.db.Column(self.db.Text)
            responded_by = self.db.Column(self.db.Integer, self.db.ForeignKey('web_user.id'))
            responded_at = self.db.Column(self.db.DateTime)
            
            # Audit
            submitted_at = self.db.Column(self.db.DateTime, default=datetime.utcnow)
            ip_address = self.db.Column(self.db.String(45))
            
            # Relationships
            patient = self.db.relationship('WebPatient', backref='feedback')
            responder = self.db.relationship('WebUser', backref='feedback_responses')
        
        class ComplaintManagement(self.db.Model):
            __tablename__ = 'complaint_management'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            complaint_number = self.db.Column(self.db.String(50), unique=True, nullable=False)
            
            # Complainant details
            complainant_name = self.db.Column(self.db.String(100), nullable=False)
            complainant_phone = self.db.Column(self.db.String(20))
            complainant_email = self.db.Column(self.db.String(120))
            relationship_to_patient = self.db.Column(self.db.String(50))  # self, family, friend, etc.
            
            # Patient information
            patient_id = self.db.Column(self.db.Integer, self.db.ForeignKey('web_patient.id'))
            
            # Complaint details
            complaint_category = self.db.Column(self.db.String(50))  # medical_care, billing, staff_behavior, facility
            subject = self.db.Column(self.db.String(200), nullable=False)
            description = self.db.Column(self.db.Text, nullable=False)
            incident_date = self.db.Column(self.db.Date)
            department_involved = self.db.Column(self.db.String(50))
            
            # Priority and status
            priority = self.db.Column(self.db.String(20), default='medium')  # low, medium, high, urgent
            status = self.db.Column(self.db.String(20), default=ComplaintStatus.OPEN.value)
            
            # Assignment
            assigned_to = self.db.Column(self.db.Integer, self.db.ForeignKey('web_user.id'))
            escalated_to = self.db.Column(self.db.Integer, self.db.ForeignKey('web_user.id'))
            
            # Timeline
            received_date = self.db.Column(self.db.DateTime, default=datetime.utcnow)
            acknowledged_date = self.db.Column(self.db.DateTime)
            target_resolution_date = self.db.Column(self.db.DateTime)
            actual_resolution_date = self.db.Column(self.db.DateTime)
            
            # Investigation and resolution
            investigation_notes = self.db.Column(self.db.Text)
            resolution_summary = self.db.Column(self.db.Text)
            corrective_actions = self.db.Column(self.db.Text)
            
            # Satisfaction
            complainant_satisfied = self.db.Column(self.db.Boolean)
            satisfaction_rating = self.db.Column(self.db.Integer)  # 1-5
            satisfaction_comments = self.db.Column(self.db.Text)
            
            # Relationships
            patient = self.db.relationship('WebPatient', backref='complaints')
            assigned_staff = self.db.relationship('WebUser', foreign_keys=[assigned_to])
            escalated_staff = self.db.relationship('WebUser', foreign_keys=[escalated_to])
        
        class ClinicalProtocol(self.db.Model):
            __tablename__ = 'clinical_protocols'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            protocol_id = self.db.Column(self.db.String(50), unique=True, nullable=False)
            
            # Protocol details
            title = self.db.Column(self.db.String(200), nullable=False)
            description = self.db.Column(self.db.Text)
            category = self.db.Column(self.db.String(50))  # emergency, surgery, medication, infection_control
            department = self.db.Column(self.db.String(50))
            
            # Content
            protocol_steps = self.db.Column(self.db.Text)  # JSON array of steps
            guidelines = self.db.Column(self.db.Text)
            contraindications = self.db.Column(self.db.Text)
            equipment_required = self.db.Column(self.db.Text)  # JSON array
            
            # Version control
            version = self.db.Column(self.db.String(10), default='1.0')
            previous_version_id = self.db.Column(self.db.Integer, self.db.ForeignKey('clinical_protocols.id'))
            
            # Approval and review
            created_by = self.db.Column(self.db.Integer, self.db.ForeignKey('web_user.id'))
            approved_by = self.db.Column(self.db.Integer, self.db.ForeignKey('web_user.id'))
            reviewed_by = self.db.Column(self.db.Integer, self.db.ForeignKey('web_user.id'))
            
            # Dates
            created_date = self.db.Column(self.db.DateTime, default=datetime.utcnow)
            approved_date = self.db.Column(self.db.DateTime)
            effective_date = self.db.Column(self.db.Date)
            review_date = self.db.Column(self.db.Date)
            expiry_date = self.db.Column(self.db.Date)
            
            # Status
            status = self.db.Column(self.db.String(20), default='draft')  # draft, approved, active, expired, superseded
            is_mandatory = self.db.Column(self.db.Boolean, default=False)
            
            # Relationships
            creator = self.db.relationship('WebUser', foreign_keys=[created_by])
            approver = self.db.relationship('WebUser', foreign_keys=[approved_by])
            reviewer = self.db.relationship('WebUser', foreign_keys=[reviewed_by])
            previous_version = self.db.relationship('ClinicalProtocol', remote_side=[id])
        
        class QualityMetric(self.db.Model):
            __tablename__ = 'quality_metrics'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            
            # Metric identification
            metric_type = self.db.Column(self.db.String(50), nullable=False)
            metric_name = self.db.Column(self.db.String(100), nullable=False)
            department = self.db.Column(self.db.String(50))
            
            # Time period
            measurement_date = self.db.Column(self.db.Date, nullable=False)
            period_type = self.db.Column(self.db.String(20), default='monthly')  # daily, weekly, monthly, quarterly
            
            # Values
            target_value = self.db.Column(self.db.Float)
            actual_value = self.db.Column(self.db.Float, nullable=False)
            numerator = self.db.Column(self.db.Float)  # For rate calculations
            denominator = self.db.Column(self.db.Float)  # For rate calculations
            
            # Analysis
            variance = self.db.Column(self.db.Float)  # Actual - Target
            variance_percentage = self.db.Column(self.db.Float)
            trend = self.db.Column(self.db.String(20))  # improving, declining, stable
            
            # Notes and actions
            notes = self.db.Column(self.db.Text)
            action_required = self.db.Column(self.db.Boolean, default=False)
            action_plan = self.db.Column(self.db.Text)
            
            # Audit
            recorded_by = self.db.Column(self.db.Integer, self.db.ForeignKey('web_user.id'))
            recorded_at = self.db.Column(self.db.DateTime, default=datetime.utcnow)
            
            # Relationships
            recorder = self.db.relationship('WebUser', backref='recorded_metrics')
        
        class AccreditationStandard(self.db.Model):
            __tablename__ = 'accreditation_standards'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            
            # Standard identification
            standard_code = self.db.Column(self.db.String(50), unique=True, nullable=False)
            accreditation_body = self.db.Column(self.db.String(50), nullable=False)  # NABH, JCI, ISO
            category = self.db.Column(self.db.String(100))
            
            # Standard details
            title = self.db.Column(self.db.String(200), nullable=False)
            description = self.db.Column(self.db.Text)
            requirements = self.db.Column(self.db.Text)  # JSON array of requirements
            
            # Compliance
            compliance_status = self.db.Column(self.db.String(20), default='not_assessed')  # compliant, non_compliant, partial, not_assessed
            compliance_percentage = self.db.Column(self.db.Float, default=0)
            
            # Assessment
            last_assessment_date = self.db.Column(self.db.Date)
            next_assessment_date = self.db.Column(self.db.Date)
            assessed_by = self.db.Column(self.db.Integer, self.db.ForeignKey('web_user.id'))
            
            # Evidence and documentation
            evidence_documents = self.db.Column(self.db.Text)  # JSON array of document references
            gaps_identified = self.db.Column(self.db.Text)
            improvement_plan = self.db.Column(self.db.Text)
            
            # Priority
            priority = self.db.Column(self.db.String(20), default='medium')
            
            # Relationships
            assessor = self.db.relationship('WebUser', backref='assessed_standards')
        
        # Store model classes
        self.IncidentReport = IncidentReport
        self.PatientFeedback = PatientFeedback
        self.ComplaintManagement = ComplaintManagement
        self.ClinicalProtocol = ClinicalProtocol
        self.QualityMetric = QualityMetric
        self.AccreditationStandard = AccreditationStandard
        
        # Create tables
        self.db.create_all()
        self._create_default_protocols()
        self._create_default_standards()
    
    def _create_default_protocols(self):
        """Create default clinical protocols"""
        default_protocols = [
            {
                'protocol_id': 'EMRG001',
                'title': 'Cardiac Arrest Response Protocol',
                'category': 'emergency',
                'department': 'Emergency',
                'protocol_steps': json.dumps([
                    'Check responsiveness and breathing',
                    'Call for help and activate emergency response',
                    'Begin CPR if no pulse',
                    'Attach AED/defibrillator',
                    'Follow ACLS guidelines',
                    'Continue until ROSC or termination criteria met'
                ]),
                'equipment_required': json.dumps([
                    'AED/Defibrillator', 'Bag-mask ventilation', 'Emergency medications',
                    'IV access supplies', 'Airway management tools'
                ]),
                'is_mandatory': True
            },
            {
                'protocol_id': 'INFCT001',
                'title': 'Hand Hygiene Protocol',
                'category': 'infection_control',
                'protocol_steps': json.dumps([
                    'Remove jewelry and roll up sleeves',
                    'Wet hands with clean water',
                    'Apply soap and lather for 20 seconds',
                    'Rinse thoroughly with clean water',
                    'Dry with clean towel or air dry',
                    'Use alcohol-based sanitizer if soap unavailable'
                ]),
                'is_mandatory': True
            }
        ]
        
        for protocol_data in default_protocols:
            existing = self.ClinicalProtocol.query.filter_by(protocol_id=protocol_data['protocol_id']).first()
            if not existing:
                protocol = self.ClinicalProtocol(**protocol_data)
                protocol.status = 'active'
                protocol.effective_date = date.today()
                self.db.session.add(protocol)
        
        try:
            self.db.session.commit()
        except Exception as e:
            logger.error(f"Failed to create default protocols: {str(e)}")
            self.db.session.rollback()
    
    def _create_default_standards(self):
        """Create default accreditation standards"""
        default_standards = [
            {
                'standard_code': 'NABH.PCC.1',
                'accreditation_body': 'NABH',
                'category': 'Patient Care and Safety',
                'title': 'Patient Identification',
                'description': 'Patients are correctly identified before any procedure or treatment',
                'requirements': json.dumps([
                    'Use at least two patient identifiers',
                    'Verify patient identity before procedures',
                    'Use standardized identification protocols',
                    'Train staff on identification procedures'
                ])
            },
            {
                'standard_code': 'JCI.PFR.1',
                'accreditation_body': 'JCI',
                'category': 'Patient and Family Rights',
                'title': 'Patient Rights and Responsibilities',
                'description': 'Patients and families are informed of their rights and responsibilities',
                'requirements': json.dumps([
                    'Provide written information about patient rights',
                    'Ensure patients understand their rights',
                    'Respect patient privacy and confidentiality',
                    'Obtain informed consent for treatment'
                ])
            }
        ]
        
        for standard_data in default_standards:
            existing = self.AccreditationStandard.query.filter_by(standard_code=standard_data['standard_code']).first()
            if not existing:
                standard = self.AccreditationStandard(**standard_data)
                self.db.session.add(standard)
        
        try:
            self.db.session.commit()
        except Exception as e:
            logger.error(f"Failed to create default standards: {str(e)}")
            self.db.session.rollback()
    
    # ==================== INCIDENT REPORTING ====================
    
    def create_incident_report(self, incident_data):
        """Create new incident report"""
        try:
            # Generate incident number
            incident_number = self._generate_incident_number()
            
            # Create incident report
            incident = self.IncidentReport(
                incident_number=incident_number,
                title=incident_data['title'],
                description=incident_data['description'],
                incident_type=incident_data.get('incident_type'),
                severity=incident_data['severity'],
                location=incident_data.get('location'),
                department=incident_data.get('department'),
                incident_date=incident_data['incident_date'],
                patient_id=incident_data.get('patient_id'),
                staff_involved=json.dumps(incident_data.get('staff_involved', [])),
                witnesses=json.dumps(incident_data.get('witnesses', [])),
                reported_by=current_user.id if current_user.is_authenticated else None
            )
            
            # Auto-assign investigator based on severity
            if self.config['incident_auto_escalation']:
                incident.assigned_investigator = self._assign_investigator(incident.severity, incident.department)
            
            self.db.session.add(incident)
            self.db.session.commit()
            
            # Send notifications for high severity incidents
            if incident.severity in ['high', 'critical']:
                self._notify_incident_team(incident)
            
            logger.info(f"Incident report created: {incident_number}")
            return incident
            
        except Exception as e:
            logger.error(f"Failed to create incident report: {str(e)}")
            self.db.session.rollback()
            raise
    
    def update_incident_investigation(self, incident_id, investigation_data):
        """Update incident investigation"""
        try:
            incident = self.db.session.get(self.IncidentReport, incident_id)
            if not incident:
                raise ValueError("Incident not found")
            
            # Update investigation fields
            if 'investigation_notes' in investigation_data:
                incident.investigation_notes = investigation_data['investigation_notes']
            
            if 'root_cause' in investigation_data:
                incident.root_cause = investigation_data['root_cause']
            
            if 'corrective_actions' in investigation_data:
                incident.corrective_actions = investigation_data['corrective_actions']
            
            if 'status' in investigation_data:
                incident.status = investigation_data['status']
                
                if investigation_data['status'] == 'resolved':
                    incident.resolution_date = datetime.utcnow()
            
            if 'follow_up_required' in investigation_data:
                incident.follow_up_required = investigation_data['follow_up_required']
                incident.follow_up_date = investigation_data.get('follow_up_date')
            
            self.db.session.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update incident investigation: {str(e)}")
            return False
    
    # ==================== PATIENT FEEDBACK ====================
    
    def submit_patient_feedback(self, feedback_data):
        """Submit patient feedback"""
        try:
            # Generate feedback ID
            feedback_id = self._generate_feedback_id()
            
            # Create feedback record
            feedback = self.PatientFeedback(
                feedback_id=feedback_id,
                patient_id=feedback_data.get('patient_id'),
                is_anonymous=feedback_data.get('is_anonymous', False),
                feedback_type=feedback_data.get('feedback_type', 'general'),
                service_area=feedback_data.get('service_area'),
                overall_rating=feedback_data.get('overall_rating'),
                staff_behavior_rating=feedback_data.get('staff_behavior_rating'),
                facility_rating=feedback_data.get('facility_rating'),
                wait_time_rating=feedback_data.get('wait_time_rating'),
                treatment_quality_rating=feedback_data.get('treatment_quality_rating'),
                comments=feedback_data.get('comments'),
                suggestions=feedback_data.get('suggestions'),
                response_required=feedback_data.get('response_required', False),
                ip_address=self._get_client_ip()
            )
            
            self.db.session.add(feedback)
            self.db.session.commit()
            
            # Convert to complaint if negative feedback
            if feedback.overall_rating and feedback.overall_rating <= 2:
                self._escalate_feedback_to_complaint(feedback)
            
            logger.info(f"Patient feedback submitted: {feedback_id}")
            return feedback
            
        except Exception as e:
            logger.error(f"Failed to submit patient feedback: {str(e)}")
            self.db.session.rollback()
            raise
    
    def respond_to_feedback(self, feedback_id, response_text):
        """Respond to patient feedback"""
        try:
            feedback = self.PatientFeedback.query.filter_by(feedback_id=feedback_id).first()
            if not feedback:
                raise ValueError("Feedback not found")
            
            feedback.response_text = response_text
            feedback.responded_by = current_user.id if current_user.is_authenticated else None
            feedback.responded_at = datetime.utcnow()
            
            self.db.session.commit()
            
            # Send notification to patient if not anonymous
            if not feedback.is_anonymous and feedback.patient:
                self._notify_feedback_response(feedback)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to respond to feedback: {str(e)}")
            return False
    
    # ==================== COMPLAINT MANAGEMENT ====================
    
    def create_complaint(self, complaint_data):
        """Create new complaint"""
        try:
            # Generate complaint number
            complaint_number = self._generate_complaint_number()
            
            # Calculate target resolution date based on SLA
            target_date = datetime.utcnow() + timedelta(hours=self.config['complaint_sla_hours'])
            
            # Create complaint
            complaint = self.ComplaintManagement(
                complaint_number=complaint_number,
                complainant_name=complaint_data['complainant_name'],
                complainant_phone=complaint_data.get('complainant_phone'),
                complainant_email=complaint_data.get('complainant_email'),
                relationship_to_patient=complaint_data.get('relationship_to_patient'),
                patient_id=complaint_data.get('patient_id'),
                complaint_category=complaint_data.get('complaint_category'),
                subject=complaint_data['subject'],
                description=complaint_data['description'],
                incident_date=complaint_data.get('incident_date'),
                department_involved=complaint_data.get('department_involved'),
                priority=complaint_data.get('priority', 'medium'),
                target_resolution_date=target_date
            )
            
            # Auto-assign based on category and department
            complaint.assigned_to = self._assign_complaint_handler(
                complaint.complaint_category, 
                complaint.department_involved
            )
            
            self.db.session.add(complaint)
            self.db.session.commit()
            
            # Send acknowledgment
            self._send_complaint_acknowledgment(complaint)
            
            logger.info(f"Complaint created: {complaint_number}")
            return complaint
            
        except Exception as e:
            logger.error(f"Failed to create complaint: {str(e)}")
            self.db.session.rollback()
            raise
    
    def update_complaint_status(self, complaint_id, status_data):
        """Update complaint status and resolution"""
        try:
            complaint = self.ComplaintManagement.query.get(complaint_id)
            if not complaint:
                raise ValueError("Complaint not found")
            
            # Update status
            if 'status' in status_data:
                complaint.status = status_data['status']
                
                if status_data['status'] == ComplaintStatus.RESOLVED.value:
                    complaint.actual_resolution_date = datetime.utcnow()
                    complaint.resolution_summary = status_data.get('resolution_summary')
                    complaint.corrective_actions = status_data.get('corrective_actions')
            
            # Update investigation notes
            if 'investigation_notes' in status_data:
                complaint.investigation_notes = status_data['investigation_notes']
            
            # Handle escalation
            if 'escalate_to' in status_data:
                complaint.escalated_to = status_data['escalate_to']
            
            self.db.session.commit()
            
            # Notify complainant of resolution
            if complaint.status == ComplaintStatus.RESOLVED.value:
                self._notify_complaint_resolution(complaint)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update complaint status: {str(e)}")
            return False
    
    # ==================== QUALITY METRICS ====================
    
    def record_quality_metric(self, metric_data):
        """Record quality metric"""
        try:
            # Calculate variance if target is provided
            variance = None
            variance_percentage = None
            
            if metric_data.get('target_value'):
                variance = metric_data['actual_value'] - metric_data['target_value']
                variance_percentage = (variance / metric_data['target_value']) * 100
            
            # Determine trend (requires historical data)
            trend = self._calculate_metric_trend(
                metric_data['metric_type'],
                metric_data['department'],
                metric_data['actual_value']
            )
            
            # Create metric record
            metric = self.QualityMetric(
                metric_type=metric_data['metric_type'],
                metric_name=metric_data['metric_name'],
                department=metric_data.get('department'),
                measurement_date=metric_data['measurement_date'],
                period_type=metric_data.get('period_type', 'monthly'),
                target_value=metric_data.get('target_value'),
                actual_value=metric_data['actual_value'],
                numerator=metric_data.get('numerator'),
                denominator=metric_data.get('denominator'),
                variance=variance,
                variance_percentage=variance_percentage,
                trend=trend,
                notes=metric_data.get('notes'),
                action_required=metric_data.get('action_required', False),
                action_plan=metric_data.get('action_plan'),
                recorded_by=current_user.id if current_user.is_authenticated else None
            )
            
            self.db.session.add(metric)
            self.db.session.commit()
            
            logger.info(f"Quality metric recorded: {metric_data['metric_name']}")
            return metric
            
        except Exception as e:
            logger.error(f"Failed to record quality metric: {str(e)}")
            self.db.session.rollback()
            raise
    
    def calculate_patient_satisfaction_score(self, period_start, period_end, department=None):
        """Calculate patient satisfaction score for a period"""
        try:
            query = self.PatientFeedback.query.filter(
                self.PatientFeedback.submitted_at.between(period_start, period_end),
                self.PatientFeedback.overall_rating.isnot(None)
            )
            
            if department:
                query = query.filter(self.PatientFeedback.service_area == department)
            
            feedback_records = query.all()
            
            if not feedback_records:
                return None
            
            # Calculate average rating
            ratings = [f.overall_rating for f in feedback_records]
            avg_rating = statistics.mean(ratings)
            
            # Record as quality metric
            self.record_quality_metric({
                'metric_type': QualityMetricType.PATIENT_SATISFACTION.value,
                'metric_name': f'Patient Satisfaction - {department or "Overall"}',
                'department': department,
                'measurement_date': period_end.date(),
                'target_value': self.config['patient_satisfaction_target'],
                'actual_value': avg_rating,
                'numerator': sum(ratings),
                'denominator': len(ratings)
            })
            
            return avg_rating
            
        except Exception as e:
            logger.error(f"Failed to calculate patient satisfaction: {str(e)}")
            return None
    
    # ==================== UTILITY METHODS ====================
    
    def _generate_incident_number(self):
        """Generate unique incident number"""
        date_str = datetime.now().strftime('%Y%m%d')
        
        # Get count of incidents today
        today_count = self.IncidentReport.query.filter(
            self.IncidentReport.incident_number.like(f'INC{date_str}%')
        ).count()
        
        return f"INC{date_str}{today_count + 1:03d}"
    
    def _generate_feedback_id(self):
        """Generate unique feedback ID"""
        date_str = datetime.now().strftime('%Y%m%d')
        
        # Get count of feedback today
        today_count = self.PatientFeedback.query.filter(
            self.PatientFeedback.feedback_id.like(f'FB{date_str}%')
        ).count()
        
        return f"FB{date_str}{today_count + 1:03d}"
    
    def _generate_complaint_number(self):
        """Generate unique complaint number"""
        date_str = datetime.now().strftime('%Y%m%d')
        
        # Get count of complaints today
        today_count = self.ComplaintManagement.query.filter(
            self.ComplaintManagement.complaint_number.like(f'COMP{date_str}%')
        ).count()
        
        return f"COMP{date_str}{today_count + 1:03d}"
    
    def _assign_investigator(self, severity, department):
        """Auto-assign investigator based on severity and department"""
        try:
            from web_app import WebUser
            
            # For critical incidents, assign to department head or quality manager
            if severity == 'critical':
                investigator = WebUser.query.filter(
                    WebUser.role.in_(['admin', 'quality_manager']),
                    WebUser.is_active == True
                ).first()
            else:
                # Assign to department supervisor or quality staff
                investigator = WebUser.query.filter(
                    WebUser.department == department,
                    WebUser.role.in_(['supervisor', 'quality_staff']),
                    WebUser.is_active == True
                ).first()
            
            return investigator.id if investigator else None
            
        except Exception as e:
            logger.error(f"Failed to assign investigator: {str(e)}")
            return None
    
    def _assign_complaint_handler(self, category, department):
        """Auto-assign complaint handler"""
        try:
            from web_app import WebUser
            
            # Assign based on complaint category
            if category == 'billing':
                handler = WebUser.query.filter(
                    WebUser.department == 'Billing',
                    WebUser.is_active == True
                ).first()
            elif category == 'medical_care':
                handler = WebUser.query.filter(
                    WebUser.department == department,
                    WebUser.role.in_(['doctor', 'supervisor']),
                    WebUser.is_active == True
                ).first()
            else:
                # Default to customer service or admin
                handler = WebUser.query.filter(
                    WebUser.role.in_(['customer_service', 'admin']),
                    WebUser.is_active == True
                ).first()
            
            return handler.id if handler else None
            
        except Exception as e:
            logger.error(f"Failed to assign complaint handler: {str(e)}")
            return None
    
    def _calculate_metric_trend(self, metric_type, department, current_value):
        """Calculate trend based on historical data"""
        try:
            # Get last 3 measurements
            historical_metrics = self.QualityMetric.query.filter(
                self.QualityMetric.metric_type == metric_type,
                self.QualityMetric.department == department
            ).order_by(self.QualityMetric.measurement_date.desc()).limit(3).all()
            
            if len(historical_metrics) < 2:
                return 'stable'
            
            # Calculate trend
            values = [m.actual_value for m in reversed(historical_metrics)] + [current_value]
            
            if len(values) >= 3:
                recent_trend = values[-1] - values[-2]
                previous_trend = values[-2] - values[-3]
                
                if recent_trend > 0 and previous_trend > 0:
                    return 'improving'
                elif recent_trend < 0 and previous_trend < 0:
                    return 'declining'
                else:
                    return 'stable'
            
            return 'stable'
            
        except Exception as e:
            logger.error(f"Failed to calculate trend: {str(e)}")
            return 'stable'
    
    def _escalate_feedback_to_complaint(self, feedback):
        """Escalate negative feedback to complaint"""
        try:
            if feedback.patient:
                complaint_data = {
                    'complainant_name': f"{feedback.patient.first_name} {feedback.patient.last_name}",
                    'complainant_phone': feedback.patient.phone,
                    'complainant_email': feedback.patient.email,
                    'relationship_to_patient': 'self',
                    'patient_id': feedback.patient_id,
                    'complaint_category': 'service_quality',
                    'subject': f'Poor service experience - Feedback ID: {feedback.feedback_id}',
                    'description': f"Auto-escalated from patient feedback.\n\nComments: {feedback.comments or 'No comments'}\n\nRatings:\n- Overall: {feedback.overall_rating}/5\n- Staff Behavior: {feedback.staff_behavior_rating}/5\n- Facility: {feedback.facility_rating}/5",
                    'department_involved': feedback.service_area,
                    'priority': 'high'
                }
                
                self.create_complaint(complaint_data)
                
        except Exception as e:
            logger.error(f"Failed to escalate feedback to complaint: {str(e)}")
    
    def _get_client_ip(self):
        """Get client IP address"""
        if not request:
            return 'unknown'
        
        if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
            return request.environ.get('REMOTE_ADDR', 'unknown')
        else:
            return request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0].strip()
    
    def _notify_incident_team(self, incident):
        """Notify incident response team"""
        # This would integrate with your notification system
        logger.info(f"Notifying incident team of {incident.severity} incident: {incident.incident_number}")
    
    def _notify_feedback_response(self, feedback):
        """Notify patient of feedback response"""
        # This would integrate with your notification system
        logger.info(f"Notifying patient of feedback response: {feedback.feedback_id}")
    
    def _send_complaint_acknowledgment(self, complaint):
        """Send complaint acknowledgment"""
        # This would integrate with your notification system
        logger.info(f"Sending complaint acknowledgment: {complaint.complaint_number}")
    
    def _notify_complaint_resolution(self, complaint):
        """Notify complainant of resolution"""
        # This would integrate with your notification system
        logger.info(f"Notifying complainant of resolution: {complaint.complaint_number}")
    
    def get_quality_dashboard_data(self):
        """Get data for quality dashboard"""
        try:
            # Recent incidents
            recent_incidents = self.IncidentReport.query.filter(
                self.IncidentReport.reported_date >= datetime.utcnow() - timedelta(days=30)
            ).count()
            
            # Open complaints
            open_complaints = self.ComplaintManagement.query.filter(
                self.ComplaintManagement.status.in_(['open', 'investigating'])
            ).count()
            
            # Average patient satisfaction (last 30 days)
            recent_feedback = self.PatientFeedback.query.filter(
                self.PatientFeedback.submitted_at >= datetime.utcnow() - timedelta(days=30),
                self.PatientFeedback.overall_rating.isnot(None)
            ).all()
            
            avg_satisfaction = None
            if recent_feedback:
                ratings = [f.overall_rating for f in recent_feedback]
                avg_satisfaction = statistics.mean(ratings)
            
            # Quality metrics summary
            recent_metrics = self.QualityMetric.query.filter(
                self.QualityMetric.recorded_at >= datetime.utcnow() - timedelta(days=30)
            ).all()
            
            metrics_summary = {}
            for metric in recent_metrics:
                if metric.metric_type not in metrics_summary:
                    metrics_summary[metric.metric_type] = []
                metrics_summary[metric.metric_type].append({
                    'value': metric.actual_value,
                    'target': metric.target_value,
                    'date': metric.measurement_date.isoformat()
                })
            
            return {
                'recent_incidents': recent_incidents,
                'open_complaints': open_complaints,
                'avg_patient_satisfaction': avg_satisfaction,
                'total_feedback_responses': len(recent_feedback),
                'metrics_summary': metrics_summary
            }
            
        except Exception as e:
            logger.error(f"Failed to get quality dashboard data: {str(e)}")
            return {}

def init_quality_management(app, db):
    """Initialize quality management system"""
    return QualityManagement(db, app)