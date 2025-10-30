"""
Multi-language support for Hospital Management System
"""

from flask import session

# Comprehensive Language Support
LANGUAGES = {
    'en': {
        # Navigation & Core
        'title': 'Hospital Management System',
        'welcome': 'Welcome to MediCare Pro',
        'login': 'Login',
        'logout': 'Logout',
        'dashboard': 'Dashboard',
        'home': 'Home',
        'profile': 'Profile',
        'settings': 'Settings',
        'language': 'Language',
        
        # Main Modules
        'patients': 'Patients',
        'appointments': 'Appointments',
        'enquiries': 'Enquiries',
        'attendance': 'Attendance',
        'telemedicine': 'Telemedicine',
        'clinical': 'Clinical',
        'pharmacy': 'Pharmacy',
        'billing': 'Billing',
        'administration': 'Administration',
        'reports': 'Reports',
        
        # Patient Management
        'all_patients': 'All Patients',
        'add_patient': 'Add Patient',
        'patient_details': 'Patient Details',
        'patient_id': 'Patient ID',
        'first_name': 'First Name',
        'last_name': 'Last Name',
        'email': 'Email',
        'phone': 'Phone',
        'date_of_birth': 'Date of Birth',
        'gender': 'Gender',
        'address': 'Address',
        'emergency_contact': 'Emergency Contact',
        'blood_group': 'Blood Group',
        'allergies': 'Allergies',
        'medical_history': 'Medical History',
        
        # Appointments
        'all_appointments': 'All Appointments',
        'schedule_new': 'Schedule New',
        'appointment_date': 'Appointment Date',
        'appointment_time': 'Appointment Time',
        'doctor': 'Doctor',
        'appointment_type': 'Appointment Type',
        'consultation': 'Consultation',
        'follow_up': 'Follow-up',
        'status': 'Status',
        'scheduled': 'Scheduled',
        'completed': 'Completed',
        'cancelled': 'Cancelled',
        'no_show': 'No Show',
        
        # Clinical
        'lab_orders': 'Lab Orders',
        'imaging_orders': 'Imaging Orders',
        'admissions': 'Admissions',
        'medical_records': 'Medical Records',
        'prescriptions': 'Prescriptions',
        'lab_results': 'Lab Results',
        'imaging_results': 'Imaging Results',
        
        # Pharmacy
        'medicines': 'Medicines',
        'pharmacy_orders': 'Pharmacy Orders',
        'dispense_medicine': 'Dispense Medicine',
        'stock_management': 'Stock Management',
        'low_stock_alert': 'Low Stock Alert',
        
        # Billing
        'all_bills': 'All Bills',
        'create_bill': 'Create Bill',
        'payments': 'Payments',
        'invoices': 'Invoices',
        'insurance_claims': 'Insurance Claims',
        'bill_number': 'Bill Number',
        'total_amount': 'Total Amount',
        'paid_amount': 'Paid Amount',
        'balance_amount': 'Balance Amount',
        'payment_status': 'Payment Status',
        'pending': 'Pending',
        'paid': 'Paid',
        'partial': 'Partial',
        
        # Administration
        'staff_management': 'Staff Management',
        'departments': 'Departments',
        'wards_beds': 'Wards & Beds',
        'services': 'Services',
        'user_roles': 'User Roles',
        
        # Common Actions
        'add': 'Add',
        'edit': 'Edit',
        'delete': 'Delete',
        'save': 'Save',
        'cancel': 'Cancel',
        'submit': 'Submit',
        'search': 'Search',
        'filter': 'Filter',
        'export': 'Export',
        'print': 'Print',
        'view': 'View',
        'update': 'Update',
        'create': 'Create',
        
        # Status & States
        'active': 'Active',
        'inactive': 'Inactive',
        'enabled': 'Enabled',
        'disabled': 'Disabled',
        'available': 'Available',
        'unavailable': 'Unavailable',
        'occupied': 'Occupied',
        'vacant': 'Vacant',
        
        # Time & Dates
        'today': 'Today',
        'yesterday': 'Yesterday',
        'tomorrow': 'Tomorrow',
        'this_week': 'This Week',
        'this_month': 'This Month',
        'date': 'Date',
        'time': 'Time',
        'duration': 'Duration',
        
        # Messages
        'success': 'Success',
        'error': 'Error',
        'warning': 'Warning',
        'info': 'Information',
        'loading': 'Loading...',
        'no_data': 'No data available',
        'confirm_delete': 'Are you sure you want to delete?',
        'operation_successful': 'Operation completed successfully',
        'operation_failed': 'Operation failed',
        'sync_data': 'Sync Data',
        'occupancy_rate': 'Occupancy Rate',
        
        # Forms
        'required_field': 'Required field',
        'optional': 'Optional',
        'select_option': 'Select an option',
        'choose_file': 'Choose file',
        'upload': 'Upload',
        'download': 'Download',
        
        # Statistics
        'total': 'Total',
        'count': 'Count',
        'percentage': 'Percentage',
        'average': 'Average',
        'minimum': 'Minimum',
        'maximum': 'Maximum',
        'statistics': 'Statistics',
        'analytics': 'Analytics'
    },
    'hi': {
        # Navigation & Core
        'title': 'अस्पताल प्रबंधन प्रणाली',
        'welcome': 'मेडिकेयर प्रो में आपका स्वागत है',
        'login': 'लॉगिन',
        'logout': 'लॉगआउट',
        'dashboard': 'डैशबोर्ड',
        'home': 'होम',
        'profile': 'प्रोफाइल',
        'settings': 'सेटिंग्स',
        'language': 'भाषा',
        
        # Main Modules
        'patients': 'मरीज़',
        'appointments': 'अपॉइंटमेंट',
        'enquiries': 'पूछताछ',
        'attendance': 'उपस्थिति',
        'telemedicine': 'टेलीमेडिसिन',
        'clinical': 'क्लिनिकल',
        'pharmacy': 'फार्मेसी',
        'billing': 'बिलिंग',
        'administration': 'प्रशासन',
        'reports': 'रिपोर्ट्स',
        
        # Patient Management
        'all_patients': 'सभी मरीज़',
        'add_patient': 'मरीज़ जोड़ें',
        'patient_details': 'मरीज़ विवरण',
        'patient_id': 'मरीज़ आईडी',
        'first_name': 'पहला नाम',
        'last_name': 'अंतिम नाम',
        'email': 'ईमेल',
        'phone': 'फोन',
        'date_of_birth': 'जन्म तिथि',
        'gender': 'लिंग',
        'address': 'पता',
        'emergency_contact': 'आपातकालीन संपर्क',
        'blood_group': 'रक्त समूह',
        'allergies': 'एलर्जी',
        'medical_history': 'चिकित्सा इतिहास',
        
        # Common Actions
        'add': 'जोड़ें',
        'edit': 'संपादित करें',
        'delete': 'हटाएं',
        'save': 'सेव करें',
        'cancel': 'रद्द करें',
        'submit': 'जमा करें',
        'search': 'खोजें',
        'filter': 'फिल्टर',
        'export': 'निर्यात',
        'print': 'प्रिंट',
        'view': 'देखें',
        'update': 'अपडेट',
        'create': 'बनाएं',
        
        # Messages
        'success': 'सफलता',
        'error': 'त्रुटि',
        'warning': 'चेतावनी',
        'info': 'जानकारी',
        'loading': 'लोड हो रहा है...',
        'no_data': 'कोई डेटा उपलब्ध नहीं',
        'operation_successful': 'ऑपरेशन सफलतापूर्वक पूरा हुआ',
        'operation_failed': 'ऑपरेशन असफल',

        # Clinical
        'lab_orders': 'प्रयोगशाला आदेश',
        'imaging_orders': 'इमेजिंग आदेश',
        'admissions': 'भर्ती',
        'medical_records': 'चिकित्सा रिकॉर्ड',
        'prescriptions': 'पर्चे',
        'lab_results': 'प्रयोगशाला परिणाम',
        'imaging_results': 'इमेजिंग परिणाम',

        # Pharmacy
        'medicines': 'दवाइयां',
        'pharmacy_orders': 'फार्मेसी आदेश',
        'dispense_medicine': 'दवा वितरित करें',
        'stock_management': 'स्टॉक प्रबंधन',
        'low_stock_alert': 'कम स्टॉक चेतावनी',

        # Billing
        'all_bills': 'सभी बिल',
        'create_bill': 'बिल बनाएं',
        'payments': 'भुगतान',
        'invoices': 'चालान',
        'insurance_claims': 'बीमा दावे',
        'bill_number': 'बिल नंबर',
        'total_amount': 'कुल राशि',
        'paid_amount': 'भुगतान की राशि',
        'balance_amount': 'बकाया राशि',
        'payment_status': 'भुगतान की स्थिति',
        'pending': 'लंबित',
        'paid': 'भुगतान किया गया',
        'partial': 'आंशिक',

        # Administration
        'staff_management': 'स्टाफ प्रबंधन',
        'departments': 'विभाग',
        'wards_beds': 'वार्ड और बिस्तर',
        'services': 'सेवाएं',
        'user_roles': 'उपयोगकर्ता भूमिकाएं',

        # Status & Dates
        'active': 'सक्रिय',
        'inactive': 'निष्क्रिय',
        'enabled': 'सक्रिय',
        'disabled': 'अक्षम',
        'available': 'उपलब्ध',
        'unavailable': 'अनुपलब्ध',
        'occupied': 'कब्जा किया',
        'vacant': 'खाली',

        # Time
        'today': 'आज',
        'yesterday': 'कल',
        'tomorrow': 'कल (आने वाला)',
        'this_week': 'इस सप्ताह',
        'this_month': 'इस महीने',
        'date': 'तारीख',
        'time': 'समय',
        'duration': 'अवधि',

        # Forms
        'required_field': 'अनिवार्य फ़ील्ड',
        'optional': 'वैकल्पिक',
        'select_option': 'एक विकल्प चुनें',
        'choose_file': 'फ़ाइल चुनें',
        'upload': 'अपलोड',
        'download': 'डाउनलोड',

        # Stats
        'total': 'कुल',
        'count': 'गिनती',
        'percentage': 'प्रतिशत',
        'average': 'औसत',
        'minimum': 'न्यूनतम',
        'maximum': 'अधिकतम',
        'statistics': 'आँकड़े',
        'analytics': 'विश्लेषण',
        'all_appointments': 'सभी अपॉइंटमेंट',
        'schedule_new': 'नया वेळापत्रक'
    }
    # Add more languages as needed...
}

def get_language():
    """Get current language from session"""
    return session.get('language', 'en')

def get_text(key):
    """Get translated text for current language"""
    lang = get_language()
    return LANGUAGES.get(lang, LANGUAGES['en']).get(key, key)
