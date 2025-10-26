#!/usr/bin/env python3
"""
Data Export/Import Module for Hospital Management System
Handles CSV, Excel, PDF, and FHIR data export/import functionality
"""

import os
import csv
import json
from datetime import datetime
from pathlib import Path
from flask import send_file, make_response
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

class DataExportImport:
    def __init__(self, db, app):
        self.db = db
        self.app = app
        self.export_dir = Path("exports")
        self.import_dir = Path("imports")
        
        # Create directories if they don't exist
        self.export_dir.mkdir(exist_ok=True)
        self.import_dir.mkdir(exist_ok=True)
    
    def export_patients_csv(self, patient_ids, include_sensitive=False):
        """Export patients to CSV format"""
        from web_app import WebPatient
        
        filename = f"patients_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = self.export_dir / filename
        
        # Get patients
        patients = self.db.session.query(WebPatient).filter(WebPatient.id.in_(patient_ids)).all()
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['patient_id', 'first_name', 'last_name', 'email', 'phone', 
                         'date_of_birth', 'gender', 'blood_group']
            
            if include_sensitive:
                fieldnames.extend(['address', 'medical_history', 'allergies'])
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for patient in patients:
                row = {
                    'patient_id': patient.patient_id,
                    'first_name': patient.first_name,
                    'last_name': patient.last_name,
                    'email': patient.email,
                    'phone': patient.phone,
                    'date_of_birth': patient.date_of_birth.strftime('%Y-%m-%d') if patient.date_of_birth else '',
                    'gender': patient.gender,
                    'blood_group': patient.blood_group
                }
                
                if include_sensitive:
                    row.update({
                        'address': patient.address,
                        'medical_history': patient.medical_history,
                        'allergies': patient.allergies
                    })
                
                writer.writerow(row)
        
        return str(filepath)
    
    def export_patients_excel(self, patient_ids, include_medical=False):
        """Export patients to Excel format"""
        from web_app import WebPatient
        
        filename = f"patients_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath = self.export_dir / filename
        
        # Get patients
        patients = self.db.session.query(WebPatient).filter(WebPatient.id.in_(patient_ids)).all()
        
        # Prepare data
        data = []
        for patient in patients:
            row = {
                'Patient ID': patient.patient_id,
                'First Name': patient.first_name,
                'Last Name': patient.last_name,
                'Email': patient.email,
                'Phone': patient.phone,
                'Date of Birth': patient.date_of_birth.strftime('%Y-%m-%d') if patient.date_of_birth else '',
                'Gender': patient.gender,
                'Blood Group': patient.blood_group,
                'City': patient.city,
                'Emergency Contact': patient.emergency_contact,
                'Emergency Phone': patient.emergency_phone
            }
            
            if include_medical:
                row.update({
                    'Medical History': patient.medical_history,
                    'Allergies': patient.allergies,
                    'Insurance Provider': patient.insurance_provider,
                    'Insurance Number': patient.insurance_number
                })
            
            data.append(row)
        
        # Create Excel file
        df = pd.DataFrame(data)
        df.to_excel(filepath, index=False, engine='openpyxl')
        
        return str(filepath)
    
    def export_patients_pdf(self, patient_ids):
        """Export patients to PDF format"""
        from web_app import WebPatient
        
        filename = f"patients_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = self.export_dir / filename
        
        # Get patients
        patients = self.db.session.query(WebPatient).filter(WebPatient.id.in_(patient_ids)).all()
        
        # Create PDF
        doc = SimpleDocTemplate(str(filepath), pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title = Paragraph("Patient Export Report", styles['Title'])
        elements.append(title)
        
        # Table data
        data = [['Patient ID', 'Name', 'Phone', 'Email', 'Blood Group']]
        
        for patient in patients:
            data.append([
                patient.patient_id,
                f"{patient.first_name} {patient.last_name}",
                patient.phone,
                patient.email or '',
                patient.blood_group or ''
            ])
        
        # Create table
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        doc.build(elements)
        
        return str(filepath)
    
    def export_hl7_fhir(self, patient_ids):
        """Export patients to HL7 FHIR JSON format"""
        from web_app import WebPatient
        
        filename = f"patients_fhir_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.export_dir / filename
        
        # Get patients
        patients = self.db.session.query(WebPatient).filter(WebPatient.id.in_(patient_ids)).all()
        
        # Create FHIR Bundle
        bundle = {
            "resourceType": "Bundle",
            "id": f"patient-export-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "type": "collection",
            "timestamp": datetime.now().isoformat(),
            "entry": []
        }
        
        for patient in patients:
            patient_resource = {
                "resource": {
                    "resourceType": "Patient",
                    "id": patient.patient_id,
                    "identifier": [
                        {
                            "use": "usual",
                            "value": patient.patient_id
                        }
                    ],
                    "name": [
                        {
                            "use": "official",
                            "family": patient.last_name,
                            "given": [patient.first_name]
                        }
                    ],
                    "telecom": [
                        {
                            "system": "phone",
                            "value": patient.phone,
                            "use": "mobile"
                        }
                    ],
                    "gender": patient.gender.lower() if patient.gender else "unknown",
                    "birthDate": patient.date_of_birth.strftime('%Y-%m-%d') if patient.date_of_birth else None
                }
            }
            
            if patient.email:
                patient_resource["resource"]["telecom"].append({
                    "system": "email",
                    "value": patient.email
                })
            
            if patient.address:
                patient_resource["resource"]["address"] = [
                    {
                        "use": "home",
                        "text": patient.address,
                        "city": patient.city,
                        "state": patient.state,
                        "postalCode": patient.zip_code,
                        "country": patient.country
                    }
                ]
            
            bundle["entry"].append(patient_resource)
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(bundle, f, indent=2, ensure_ascii=False)
        
        return str(filepath)
    
    def generate_comprehensive_report(self, report_type, start_date, end_date):
        """Generate comprehensive reports"""
        filename = f"{report_type}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = self.export_dir / filename
        
        # Create PDF
        doc = SimpleDocTemplate(str(filepath), pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title = Paragraph(f"{report_type.title()} Report", styles['Title'])
        elements.append(title)
        
        # Date range
        date_range = Paragraph(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}", styles['Normal'])
        elements.append(date_range)
        
        # Placeholder content
        content = Paragraph("Report content will be generated based on the selected type and date range.", styles['Normal'])
        elements.append(content)
        
        doc.build(elements)
        return str(filepath)
    
    def import_patients_csv(self, file_path, validate_only=False):
        """Import patients from CSV file"""
        results = {
            'success': 0,
            'errors': 0,
            'warnings': [],
            'imported_patients': []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                
                for row_num, row in enumerate(reader, start=2):
                    try:
                        # Validate required fields
                        if not row.get('first_name') or not row.get('last_name'):
                            results['warnings'].append(f"Row {row_num}: Missing required name fields")
                            results['errors'] += 1
                            continue
                        
                        if not validate_only:
                            # Create patient record (simplified)
                            patient_data = {
                                'first_name': row.get('first_name'),
                                'last_name': row.get('last_name'),
                                'email': row.get('email'),
                                'phone': row.get('phone'),
                                'gender': row.get('gender'),
                                'blood_group': row.get('blood_group')
                            }
                            results['imported_patients'].append(patient_data)
                        
                        results['success'] += 1
                        
                    except Exception as e:
                        results['warnings'].append(f"Row {row_num}: {str(e)}")
                        results['errors'] += 1
        
        except Exception as e:
            results['warnings'].append(f"File error: {str(e)}")
            results['errors'] += 1
        
        return results
    
    def import_hl7_fhir(self, file_path, validate_only=False):
        """Import patients from HL7 FHIR JSON file"""
        results = {
            'success': 0,
            'errors': 0,
            'warnings': [],
            'imported_patients': []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if data.get('resourceType') != 'Bundle':
                results['warnings'].append("Invalid FHIR Bundle format")
                results['errors'] += 1
                return results
            
            for entry in data.get('entry', []):
                resource = entry.get('resource', {})
                
                if resource.get('resourceType') == 'Patient':
                    try:
                        # Extract patient data
                        name = resource.get('name', [{}])[0]
                        telecom = resource.get('telecom', [])
                        
                        patient_data = {
                            'first_name': name.get('given', [''])[0],
                            'last_name': name.get('family', ''),
                            'gender': resource.get('gender', ''),
                            'date_of_birth': resource.get('birthDate', '')
                        }
                        
                        # Extract contact info
                        for contact in telecom:
                            if contact.get('system') == 'phone':
                                patient_data['phone'] = contact.get('value')
                            elif contact.get('system') == 'email':
                                patient_data['email'] = contact.get('value')
                        
                        if not validate_only:
                            results['imported_patients'].append(patient_data)
                        
                        results['success'] += 1
                        
                    except Exception as e:
                        results['warnings'].append(f"Patient resource error: {str(e)}")
                        results['errors'] += 1
        
        except Exception as e:
            results['warnings'].append(f"File error: {str(e)}")
            results['errors'] += 1
        
        return results

def create_download_response(file_path, filename=None):
    """Create a download response for exported files"""
    if not filename:
        filename = os.path.basename(file_path)
    
    return send_file(
        file_path,
        as_attachment=True,
        download_name=filename,
        mimetype='application/octet-stream'
    )#!/usr/bin/env python3
"""
Data Export/Import System
Handles patient data export, bulk import, report generation, and interoperability standards
"""

import pandas as pd
import json
import csv
import xml.etree.ElementTree as ET
from datetime import datetime, date
from pathlib import Path
import zipfile
import io
from flask import make_response, jsonify
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils.dataframe import dataframe_to_rows
import sqlite3
from sqlalchemy import text
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataExportImport:
    def __init__(self, db, app):
        self.db = db
        self.app = app
        self.export_dir = Path('exports')
        self.import_dir = Path('imports')
        self.export_dir.mkdir(exist_ok=True)
        self.import_dir.mkdir(exist_ok=True)
    
    # ==================== EXPORT FUNCTIONS ====================
    
    def export_patients_csv(self, patient_ids=None, include_sensitive=False):
        """Export patient data to CSV format"""
        try:
            # Import models here to avoid circular imports
            from web_app import WebPatient
            
            query = WebPatient.query
            if patient_ids:
                query = query.filter(WebPatient.id.in_(patient_ids))
            
            patients = query.all()
            
            # Define columns based on sensitivity level
            if include_sensitive:
                columns = [
                    'patient_id', 'first_name', 'last_name', 'email', 'phone',
                    'date_of_birth', 'gender', 'address', 'city', 'state', 'zip_code',
                    'emergency_contact', 'emergency_phone', 'blood_group', 'allergies',
                    'medical_history', 'insurance_provider', 'insurance_number',
                    'id_proof_type', 'id_proof_number', 'created_at'
                ]
            else:
                columns = [
                    'patient_id', 'first_name', 'last_name', 'gender', 'age',
                    'blood_group', 'city', 'state', 'created_at'
                ]
            
            # Prepare data
            data = []
            for patient in patients:
                row = {}
                for col in columns:
                    if col == 'age' and patient.date_of_birth:
                        age = (date.today() - patient.date_of_birth).days // 365
                        row[col] = age
                    else:
                        value = getattr(patient, col, '')
                        if isinstance(value, (date, datetime)):
                            row[col] = value.strftime('%Y-%m-%d')
                        else:
                            row[col] = value or ''
                data.append(row)
            
            # Create DataFrame and export
            df = pd.DataFrame(data)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"patients_export_{timestamp}.csv"
            filepath = self.export_dir / filename
            
            df.to_csv(filepath, index=False)
            
            logger.info(f"Exported {len(patients)} patients to {filename}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to export patients CSV: {str(e)}")
            raise
    
    def export_patients_excel(self, patient_ids=None, include_medical_records=False):
        """Export patient data to Excel format with multiple sheets"""
        try:
            from web_app import WebPatient, MedicalRecord, Prescription
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"patients_export_{timestamp}.xlsx"
            filepath = self.export_dir / filename
            
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # Patient basic info
                query = WebPatient.query
                if patient_ids:
                    query = query.filter(WebPatient.id.in_(patient_ids))
                
                patients = query.all()
                
                # Prepare patient data
                patient_data = []
                for patient in patients:
                    age = None
                    if patient.date_of_birth:
                        age = (date.today() - patient.date_of_birth).days // 365
                    
                    patient_data.append({
                        'Patient ID': patient.patient_id,
                        'Name': f"{patient.first_name} {patient.last_name}",
                        'Email': patient.email,
                        'Phone': patient.phone,
                        'Date of Birth': patient.date_of_birth.strftime('%Y-%m-%d') if patient.date_of_birth else '',
                        'Age': age,
                        'Gender': patient.gender,
                        'Blood Group': patient.blood_group,
                        'Address': patient.address,
                        'City': patient.city,
                        'State': patient.state,
                        'Emergency Contact': patient.emergency_contact,
                        'Emergency Phone': patient.emergency_phone,
                        'Insurance Provider': patient.insurance_provider,
                        'Created At': patient.created_at.strftime('%Y-%m-%d %H:%M:%S')
                    })
                
                df_patients = pd.DataFrame(patient_data)
                df_patients.to_excel(writer, sheet_name='Patients', index=False)
                
                # Medical records if requested
                if include_medical_records:
                    medical_records = []
                    for patient in patients:
                        for record in patient.medical_records:
                            medical_records.append({
                                'Patient ID': patient.patient_id,
                                'Patient Name': f"{patient.first_name} {patient.last_name}",
                                'Visit Date': record.visit_date.strftime('%Y-%m-%d %H:%M:%S'),
                                'Chief Complaint': record.chief_complaint,
                                'Diagnosis': record.diagnosis,
                                'Treatment Plan': record.treatment_plan,
                                'Doctor': record.doctor.full_name if record.doctor else '',
                                'Created At': record.created_at.strftime('%Y-%m-%d %H:%M:%S')
                            })
                    
                    if medical_records:
                        df_records = pd.DataFrame(medical_records)
                        df_records.to_excel(writer, sheet_name='Medical Records', index=False)
                
                # Format the Excel file
                workbook = writer.book
                
                # Style the headers
                header_font = Font(bold=True, color='FFFFFF')
                header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
                
                for sheet_name in workbook.sheetnames:
                    worksheet = workbook[sheet_name]
                    
                    # Apply header styling
                    for cell in worksheet[1]:
                        cell.font = header_font
                        cell.fill = header_fill
                        cell.alignment = Alignment(horizontal='center')
                    
                    # Auto-adjust column widths
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width
            
            logger.info(f"Exported {len(patients)} patients to Excel: {filename}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to export patients Excel: {str(e)}")
            raise
    
    def export_patients_pdf(self, patient_ids=None):
        """Export patient data to PDF format"""
        try:
            from web_app import WebPatient
            
            query = WebPatient.query
            if patient_ids:
                query = query.filter(WebPatient.id.in_(patient_ids))
            
            patients = query.all()
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"patients_export_{timestamp}.pdf"
            filepath = self.export_dir / filename
            
            # Create PDF document
            doc = SimpleDocTemplate(str(filepath), pagesize=A4)
            styles = getSampleStyleSheet()
            story = []
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=30,
                alignment=1  # Center alignment
            )
            
            story.append(Paragraph("Patient Export Report", title_style))
            story.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
            story.append(Paragraph(f"Total Patients: {len(patients)}", styles['Normal']))
            story.append(Spacer(1, 20))
            
            # Patient data table
            data = [['Patient ID', 'Name', 'Gender', 'Age', 'Blood Group', 'Phone', 'City']]
            
            for patient in patients:
                age = ''
                if patient.date_of_birth:
                    age = str((date.today() - patient.date_of_birth).days // 365)
                
                data.append([
                    patient.patient_id or '',
                    f"{patient.first_name} {patient.last_name}",
                    patient.gender or '',
                    age,
                    patient.blood_group or '',
                    patient.phone or '',
                    patient.city or ''
                ])
            
            # Create table
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(table)
            
            # Build PDF
            doc.build(story)
            
            logger.info(f"Exported {len(patients)} patients to PDF: {filename}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to export patients PDF: {str(e)}")
            raise
    
    def export_hl7_fhir(self, patient_ids=None):
        """Export patient data in HL7 FHIR format"""
        try:
            from web_app import WebPatient, MedicalRecord
            
            query = WebPatient.query
            if patient_ids:
                query = query.filter(WebPatient.id.in_(patient_ids))
            
            patients = query.all()
            
            # Create FHIR Bundle
            bundle = {
                "resourceType": "Bundle",
                "id": f"patient-export-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "type": "collection",
                "timestamp": datetime.now().isoformat(),
                "total": len(patients),
                "entry": []
            }
            
            for patient in patients:
                # Patient resource
                patient_resource = {
                    "resource": {
                        "resourceType": "Patient",
                        "id": patient.patient_id,
                        "identifier": [
                            {
                                "use": "usual",
                                "system": "http://hospital.local/patient-id",
                                "value": patient.patient_id
                            }
                        ],
                        "name": [
                            {
                                "use": "official",
                                "family": patient.last_name,
                                "given": [patient.first_name]
                            }
                        ],
                        "telecom": [],
                        "gender": patient.gender.lower() if patient.gender else "unknown",
                        "birthDate": patient.date_of_birth.strftime('%Y-%m-%d') if patient.date_of_birth else None,
                        "address": []
                    }
                }
                
                # Add contact information
                if patient.phone:
                    patient_resource["resource"]["telecom"].append({
                        "system": "phone",
                        "value": patient.phone,
                        "use": "mobile"
                    })
                
                if patient.email:
                    patient_resource["resource"]["telecom"].append({
                        "system": "email",
                        "value": patient.email
                    })
                
                # Add address
                if patient.address:
                    patient_resource["resource"]["address"].append({
                        "use": "home",
                        "line": [patient.address],
                        "city": patient.city,
                        "state": patient.state,
                        "postalCode": patient.zip_code,
                        "country": patient.country
                    })
                
                bundle["entry"].append(patient_resource)
                
                # Add medical records as Observation resources
                for record in patient.medical_records:
                    observation = {
                        "resource": {
                            "resourceType": "Observation",
                            "id": f"observation-{record.id}",
                            "status": "final",
                            "subject": {
                                "reference": f"Patient/{patient.patient_id}"
                            },
                            "effectiveDateTime": record.visit_date.isoformat(),
                            "valueString": record.diagnosis,
                            "note": [
                                {
                                    "text": record.notes or ""
                                }
                            ]
                        }
                    }
                    bundle["entry"].append(observation)
            
            # Save to file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"fhir_export_{timestamp}.json"
            filepath = self.export_dir / filename
            
            with open(filepath, 'w') as f:
                json.dump(bundle, f, indent=2)
            
            logger.info(f"Exported {len(patients)} patients to FHIR format: {filename}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to export FHIR: {str(e)}")
            raise
    
    # ==================== IMPORT FUNCTIONS ====================
    
    def import_patients_csv(self, file_path, validate_only=False):
        """Import patients from CSV file"""
        try:
            from web_app import WebPatient
            
            df = pd.read_csv(file_path)
            
            results = {
                'total_rows': len(df),
                'successful_imports': 0,
                'failed_imports': 0,
                'errors': [],
                'warnings': []
            }
            
            for index, row in df.iterrows():
                try:
                    # Validate required fields
                    if pd.isna(row.get('first_name')) or pd.isna(row.get('last_name')):
                        results['errors'].append(f"Row {index + 1}: Missing required fields (first_name, last_name)")
                        results['failed_imports'] += 1
                        continue
                    
                    # Check if patient already exists
                    existing_patient = None
                    if not pd.isna(row.get('patient_id')):
                        existing_patient = WebPatient.query.filter_by(patient_id=row['patient_id']).first()
                    
                    if existing_patient:
                        results['warnings'].append(f"Row {index + 1}: Patient {row['patient_id']} already exists")
                        continue
                    
                    if not validate_only:
                        # Create new patient
                        patient = WebPatient()
                        
                        # Map CSV columns to patient attributes
                        patient.first_name = str(row['first_name']).strip()
                        patient.last_name = str(row['last_name']).strip()
                        patient.email = str(row.get('email', '')).strip() if not pd.isna(row.get('email')) else None
                        patient.phone = str(row.get('phone', '')).strip() if not pd.isna(row.get('phone')) else None
                        patient.gender = str(row.get('gender', '')).strip() if not pd.isna(row.get('gender')) else None
                        patient.address = str(row.get('address', '')).strip() if not pd.isna(row.get('address')) else None
                        patient.city = str(row.get('city', '')).strip() if not pd.isna(row.get('city')) else None
                        patient.state = str(row.get('state', '')).strip() if not pd.isna(row.get('state')) else None
                        patient.zip_code = str(row.get('zip_code', '')).strip() if not pd.isna(row.get('zip_code')) else None
                        patient.blood_group = str(row.get('blood_group', '')).strip() if not pd.isna(row.get('blood_group')) else None
                        
                        # Handle date of birth
                        if not pd.isna(row.get('date_of_birth')):
                            try:
                                patient.date_of_birth = pd.to_datetime(row['date_of_birth']).date()
                            except:
                                results['warnings'].append(f"Row {index + 1}: Invalid date format for date_of_birth")
                        
                        # Generate patient ID if not provided
                        if pd.isna(row.get('patient_id')):
                            patient.patient_id = f"P{datetime.now().strftime('%Y%m%d')}{str(index + 1).zfill(4)}"
                        else:
                            patient.patient_id = str(row['patient_id']).strip()
                        
                        self.db.session.add(patient)
                        results['successful_imports'] += 1
                    
                except Exception as e:
                    results['errors'].append(f"Row {index + 1}: {str(e)}")
                    results['failed_imports'] += 1
            
            if not validate_only and results['successful_imports'] > 0:
                self.db.session.commit()
            
            logger.info(f"Import completed: {results['successful_imports']} successful, {results['failed_imports']} failed")
            return results
            
        except Exception as e:
            logger.error(f"Failed to import patients CSV: {str(e)}")
            raise
    
    def import_hl7_fhir(self, file_path, validate_only=False):
        """Import patient data from HL7 FHIR format"""
        try:
            from web_app import WebPatient
            
            with open(file_path, 'r') as f:
                fhir_data = json.load(f)
            
            results = {
                'total_resources': 0,
                'successful_imports': 0,
                'failed_imports': 0,
                'errors': [],
                'warnings': []
            }
            
            if fhir_data.get('resourceType') != 'Bundle':
                raise ValueError("Invalid FHIR format: Expected Bundle resource type")
            
            patient_resources = [
                entry['resource'] for entry in fhir_data.get('entry', [])
                if entry.get('resource', {}).get('resourceType') == 'Patient'
            ]
            
            results['total_resources'] = len(patient_resources)
            
            for resource in patient_resources:
                try:
                    # Extract patient data from FHIR resource
                    patient_id = resource.get('id')
                    
                    # Check if patient already exists
                    existing_patient = WebPatient.query.filter_by(patient_id=patient_id).first()
                    if existing_patient:
                        results['warnings'].append(f"Patient {patient_id} already exists")
                        continue
                    
                    if not validate_only:
                        patient = WebPatient()
                        patient.patient_id = patient_id
                        
                        # Extract name
                        names = resource.get('name', [])
                        if names:
                            name = names[0]
                            patient.first_name = ' '.join(name.get('given', []))
                            patient.last_name = name.get('family', '')
                        
                        # Extract gender and birth date
                        patient.gender = resource.get('gender', '').capitalize()
                        
                        birth_date = resource.get('birthDate')
                        if birth_date:
                            patient.date_of_birth = datetime.strptime(birth_date, '%Y-%m-%d').date()
                        
                        # Extract contact information
                        telecoms = resource.get('telecom', [])
                        for telecom in telecoms:
                            if telecom.get('system') == 'phone':
                                patient.phone = telecom.get('value')
                            elif telecom.get('system') == 'email':
                                patient.email = telecom.get('value')
                        
                        # Extract address
                        addresses = resource.get('address', [])
                        if addresses:
                            address = addresses[0]
                            patient.address = ' '.join(address.get('line', []))
                            patient.city = address.get('city')
                            patient.state = address.get('state')
                            patient.zip_code = address.get('postalCode')
                            patient.country = address.get('country')
                        
                        self.db.session.add(patient)
                        results['successful_imports'] += 1
                    
                except Exception as e:
                    results['errors'].append(f"Patient {patient_id}: {str(e)}")
                    results['failed_imports'] += 1
            
            if not validate_only and results['successful_imports'] > 0:
                self.db.session.commit()
            
            logger.info(f"FHIR import completed: {results['successful_imports']} successful, {results['failed_imports']} failed")
            return results
            
        except Exception as e:
            logger.error(f"Failed to import FHIR: {str(e)}")
            raise
    
    # ==================== REPORT GENERATION ====================
    
    def generate_comprehensive_report(self, report_type='monthly', start_date=None, end_date=None):
        """Generate comprehensive hospital reports"""
        try:
            if not start_date:
                start_date = datetime.now().replace(day=1)  # First day of current month
            if not end_date:
                end_date = datetime.now()
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"hospital_report_{report_type}_{timestamp}.xlsx"
            filepath = self.export_dir / filename
            
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # Patient statistics
                self._generate_patient_statistics_sheet(writer, start_date, end_date)
                
                # Appointment statistics
                self._generate_appointment_statistics_sheet(writer, start_date, end_date)
                
                # Financial summary
                self._generate_financial_summary_sheet(writer, start_date, end_date)
                
                # Department performance
                self._generate_department_performance_sheet(writer, start_date, end_date)
                
                # Inventory status
                self._generate_inventory_status_sheet(writer)
            
            logger.info(f"Generated comprehensive report: {filename}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to generate comprehensive report: {str(e)}")
            raise
    
    def _generate_patient_statistics_sheet(self, writer, start_date, end_date):
        """Generate patient statistics sheet"""
        from web_app import WebPatient, Admission
        
        # New patients in period
        new_patients = WebPatient.query.filter(
            WebPatient.created_at.between(start_date, end_date)
        ).all()
        
        # Admissions in period
        admissions = Admission.query.filter(
            Admission.admission_date.between(start_date, end_date)
        ).all()
        
        # Patient demographics
        total_patients = WebPatient.query.count()
        
        # Age distribution
        age_groups = {'0-18': 0, '19-35': 0, '36-50': 0, '51-65': 0, '65+': 0}
        gender_dist = {'Male': 0, 'Female': 0, 'Other': 0}
        
        for patient in WebPatient.query.all():
            if patient.date_of_birth:
                age = (date.today() - patient.date_of_birth).days // 365
                if age <= 18:
                    age_groups['0-18'] += 1
                elif age <= 35:
                    age_groups['19-35'] += 1
                elif age <= 50:
                    age_groups['36-50'] += 1
                elif age <= 65:
                    age_groups['51-65'] += 1
                else:
                    age_groups['65+'] += 1
            
            if patient.gender:
                gender_dist[patient.gender] = gender_dist.get(patient.gender, 0) + 1
        
        # Create summary data
        summary_data = [
            ['Metric', 'Value'],
            ['Total Patients', total_patients],
            ['New Patients (Period)', len(new_patients)],
            ['Total Admissions (Period)', len(admissions)],
            ['', ''],
            ['Age Distribution', ''],
            ['0-18 years', age_groups['0-18']],
            ['19-35 years', age_groups['19-35']],
            ['36-50 years', age_groups['36-50']],
            ['51-65 years', age_groups['51-65']],
            ['65+ years', age_groups['65+']],
            ['', ''],
            ['Gender Distribution', ''],
            ['Male', gender_dist['Male']],
            ['Female', gender_dist['Female']],
            ['Other', gender_dist['Other']]
        ]
        
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(writer, sheet_name='Patient Statistics', index=False, header=False)
    
    def _generate_appointment_statistics_sheet(self, writer, start_date, end_date):
        """Generate appointment statistics sheet"""
        from web_app import WebAppointment
        
        appointments = WebAppointment.query.filter(
            WebAppointment.appointment_date.between(start_date, end_date)
        ).all()
        
        # Status breakdown
        status_counts = {}
        type_counts = {}
        
        for appointment in appointments:
            status_counts[appointment.status] = status_counts.get(appointment.status, 0) + 1
            type_counts[appointment.appointment_type] = type_counts.get(appointment.appointment_type, 0) + 1
        
        # Create appointment data
        appointment_data = []
        for appointment in appointments:
            appointment_data.append({
                'Date': appointment.appointment_date.strftime('%Y-%m-%d'),
                'Patient': f"{appointment.patient.first_name} {appointment.patient.last_name}",
                'Doctor': appointment.doctor.full_name if appointment.doctor else '',
                'Type': appointment.appointment_type,
                'Status': appointment.status
            })
        
        df_appointments = pd.DataFrame(appointment_data)
        df_appointments.to_excel(writer, sheet_name='Appointments', index=False)
    
    def _generate_financial_summary_sheet(self, writer, start_date, end_date):
        """Generate financial summary sheet"""
        from web_app import Bill, Payment
        
        bills = Bill.query.filter(
            Bill.bill_date.between(start_date, end_date)
        ).all()
        
        payments = Payment.query.filter(
            Payment.payment_date.between(start_date, end_date)
        ).all()
        
        # Financial metrics
        total_billed = sum(bill.total_amount for bill in bills)
        total_collected = sum(payment.amount for payment in payments)
        outstanding = total_billed - total_collected
        
        financial_data = [
            ['Metric', 'Amount'],
            ['Total Billed', total_billed],
            ['Total Collected', total_collected],
            ['Outstanding', outstanding],
            ['Collection Rate (%)', (total_collected / total_billed * 100) if total_billed > 0 else 0]
        ]
        
        df_financial = pd.DataFrame(financial_data)
        df_financial.to_excel(writer, sheet_name='Financial Summary', index=False, header=False)
    
    def _generate_department_performance_sheet(self, writer, start_date, end_date):
        """Generate department performance sheet"""
        from web_app import Department, WebAppointment
        
        departments = Department.query.filter_by(is_active=True).all()
        
        dept_data = []
        for dept in departments:
            # Count appointments for this department's doctors
            dept_appointments = WebAppointment.query.join(
                WebAppointment.doctor
            ).filter(
                WebAppointment.appointment_date.between(start_date, end_date)
            ).count()
            
            dept_data.append({
                'Department': dept.name,
                'Code': dept.code,
                'Appointments': dept_appointments,
                'Head of Department': dept.hod.full_name if dept.hod else 'Not Assigned'
            })
        
        df_departments = pd.DataFrame(dept_data)
        df_departments.to_excel(writer, sheet_name='Department Performance', index=False)
    
    def _generate_inventory_status_sheet(self, writer):
        """Generate inventory status sheet"""
        from web_app import Medicine
        
        medicines = Medicine.query.filter_by(is_active=True).all()
        
        inventory_data = []
        for medicine in medicines:
            status = 'Normal'
            if medicine.stock_quantity <= medicine.min_stock_level:
                status = 'Low Stock'
            if medicine.stock_quantity == 0:
                status = 'Out of Stock'
            
            inventory_data.append({
                'Medicine Name': medicine.name,
                'Generic Name': medicine.generic_name,
                'Category': medicine.category,
                'Current Stock': medicine.stock_quantity,
                'Min Stock Level': medicine.min_stock_level,
                'Status': status,
                'Expiry Date': medicine.expiry_date.strftime('%Y-%m-%d') if medicine.expiry_date else '',
                'Purchase Price': medicine.purchase_price,
                'Selling Price': medicine.selling_price
            })
        
        df_inventory = pd.DataFrame(inventory_data)
        df_inventory.to_excel(writer, sheet_name='Inventory Status', index=False)
    
    # ==================== UTILITY FUNCTIONS ====================
    
    def create_export_package(self, export_files, package_name=None):
        """Create a ZIP package of multiple export files"""
        try:
            if not package_name:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                package_name = f"hospital_export_package_{timestamp}.zip"
            
            package_path = self.export_dir / package_name
            
            with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in export_files:
                    file_path = Path(file_path)
                    if file_path.exists():
                        zipf.write(file_path, file_path.name)
            
            logger.info(f"Created export package: {package_name}")
            return str(package_path)
            
        except Exception as e:
            logger.error(f"Failed to create export package: {str(e)}")
            raise
    
    def cleanup_old_exports(self, days_to_keep=7):
        """Clean up old export files"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            for file_path in self.export_dir.iterdir():
                if file_path.is_file():
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < cutoff_date:
                        file_path.unlink()
                        logger.info(f"Deleted old export file: {file_path.name}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old exports: {str(e)}")

# Flask route helpers
def create_download_response(file_path, filename=None):
    """Create Flask response for file download"""
    file_path = Path(file_path)
    
    if not filename:
        filename = file_path.name
    
    def generate():
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(4096)
                if not data:
                    break
                yield data
    
    response = make_response(generate())
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # Set appropriate content type
    if file_path.suffix == '.csv':
        response.headers['Content-Type'] = 'text/csv'
    elif file_path.suffix == '.xlsx':
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    elif file_path.suffix == '.pdf':
        response.headers['Content-Type'] = 'application/pdf'
    elif file_path.suffix == '.json':
        response.headers['Content-Type'] = 'application/json'
    elif file_path.suffix == '.zip':
        response.headers['Content-Type'] = 'application/zip'
    
    return response