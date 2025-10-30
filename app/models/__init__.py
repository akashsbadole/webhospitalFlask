"""
Database Models for Hospital Management System
"""

from .user import WebUser
from .patient import WebPatient
from .clinical import (
    MedicalRecord, Prescription, LabTest, LabOrder, LabResult,
    ImagingTest, ImagingOrder, ImagingResult
)
from .pharmacy import Medicine, PharmacyOrder, PharmacyOrderItem
from .billing import Bill, BillItem, Payment, InsuranceClaim
from .admin import (
    HospitalSetting, HospitalBranch, NotificationTemplate,
    PaymentGateway, InsuranceProvider as InsuranceProviderModel,
    DiscountPolicy, TaxRule, ConsentForm, UserRoleTemplate,
    AppointmentSlotTemplate, Department, Service, Ward, Bed
)
from .attendance import WebAttendance, WebEnquiry
from .admission import Admission

__all__ = [
    'WebUser', 'WebPatient', 'MedicalRecord', 'Prescription',
    'LabTest', 'LabOrder', 'LabResult', 'ImagingTest', 'ImagingOrder', 'ImagingResult',
    'Medicine', 'PharmacyOrder', 'PharmacyOrderItem', 'Bill', 'BillItem',
    'Payment', 'InsuranceClaim', 'HospitalSetting', 'HospitalBranch',
    'NotificationTemplate', 'PaymentGateway', 'InsuranceProviderModel',
    'DiscountPolicy', 'TaxRule', 'ConsentForm', 'UserRoleTemplate',
    'AppointmentSlotTemplate', 'Department', 'Service', 'Ward', 'Bed',
    'WebAttendance', 'WebEnquiry', 'Admission'
]
