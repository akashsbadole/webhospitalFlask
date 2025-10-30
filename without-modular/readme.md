# 🏥 MediCare Pro - Hospital Management System

A comprehensive, multi-tenant Hospital Management System built with Flask, featuring modern web interface, advanced security, and complete healthcare workflow management.

## Screenshot

![medicare](medicare-pro.jpeg "medicare-pro")
![medicare login](medicare-pro-login.jpeg "medicare-pro-login")

## 🌟 Features

### 🔐 Multi-Tenant SaaS Architecture

- **Tenant Management**: Complete multi-tenant support with isolated data
- **Subscription Plans**: Basic, Professional, and Enterprise tiers
- **Custom Domains**: Support for custom domains and subdomains
- **Tenant-specific Settings**: Customizable branding and configurations

### 👥 User Management & Security

- **Role-based Access Control**: Admin, Doctor, Nurse, Receptionist, Lab Tech, Patient roles
- **Two-Factor Authentication (2FA)**: Enhanced security with TOTP support
- **Advanced Security Features**: Login attempt monitoring, IP tracking, session management
- **Audit Logging**: Comprehensive activity tracking and security event logging

### 🏥 Core Hospital Management

- **Patient Management**: Complete patient registration, medical history, demographics
- **Appointment Scheduling**: Advanced booking system with telemedicine support
- **Electronic Health Records (EHR)**: Digital medical records with version control
- **Staff Management**: Employee profiles, attendance tracking, shift management

### 🧪 Clinical Operations

- **Laboratory Management**: Test orders, sample tracking, result management
- **Radiology/Imaging**: Imaging orders, DICOM support, radiologist reporting
- **Pharmacy Management**: Medicine inventory, prescription management, dispensing
- **Prescription System**: Digital prescriptions with drug interaction checking

### 🏨 Inpatient Management

- **Ward Management**: Bed allocation, occupancy tracking
- **Admission/Discharge**: Complete inpatient workflow
- **Nursing Care**: Patient monitoring, vital signs tracking

### 💰 Financial Management

- **Billing System**: Comprehensive billing with multiple service types
- **Payment Processing**: Multiple payment methods, installment support
- **Insurance Claims**: Insurance provider integration and claim processing
- **Financial Reporting**: Revenue tracking, outstanding payments

### 📊 Reporting & Analytics

- **Dashboard Analytics**: Real-time KPIs and metrics
- **Custom Reports**: Patient reports, financial summaries, operational metrics
- **Data Export/Import**: Excel, CSV, PDF export capabilities
- **Quality Management**: Performance indicators and quality metrics

### 🔧 System Features

- **Backup Management**: Automated database backups with scheduling
- **Notification System**: Email, SMS, WhatsApp notifications
- **Document Management**: File upload, storage, and retrieval
- **Emergency Management**: Emergency protocols and incident reporting
- **Inventory Management**: Medical supplies and equipment tracking

### 🌐 Modern Web Interface

- **Responsive Design**: Mobile-friendly interface
- **Real-time Updates**: WebSocket support for live data
- **Progressive Web App**: Offline capability and app-like experience
- **Multilingual Support**: Multiple language support
- **Accessibility**: WCAG compliant interface

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- pip (Python package manager)
- SQLite (included with Python)
- Redis (optional, for caching)

### Installation

1. **Clone the Repository**

   ```bash
   git clone <repository-url>
   cd webhms
   ```

2. **Create Virtual Environment**

   ```bash
   python -m venv venv

   # Windows
   venv\Scripts\activate

   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install Dependencies**

   ```bash
   pip install -r requirements_web_app.txt
   ```

4. **Initialize Database**

   ```bash
   python create_all_tables.py
   ```

5. **Create User Accounts**

   ```bash
   python create_accounts.py
   ```

6. **Run the Application**

   ```bash
   python web_app.py
   ```

7. **Access the Application**
   - Open your browser and go to `http://localhost:5000`
   - Use the login credentials provided below

## 🔑 Default Login Credentials

### ADMIN ACCOUNTS:

- **Username**: `superadmin` | **Password**: `admin123`
- **Username**: `hradmin` | **Password**: `hr123`

### DOCTOR ACCOUNTS:

- **Username**: `dr.smith` | **Password**: `doctor123`
- **Username**: `dr.johnson` | **Password**: `doctor123`
- **Username**: `dr.williams` | **Password**: `doctor123`

### STAFF ACCOUNTS:

- **Username**: `nurse.mary` | **Password**: `nurse123`
- **Username**: `nurse.david` | **Password**: `nurse123`
- **Username**: `receptionist1` | **Password**: `staff123`
- **Username**: `receptionist2` | **Password**: `staff123`
- **Username**: `lab.tech1` | **Password**: `lab123`
- **Username**: `lab.tech2` | **Password**: `lab123`

### PATIENT/CUSTOMER ACCOUNTS:

- **Username**: `patient1` | **Password**: `patient123`
- **Username**: `patient2` | **Password**: `patient123`
- **Username**: `patient3` | **Password**: `patient123`

## 📋 User Database Summary

**Total Users**: 20 accounts across all roles

### ACCOUNTANTS:

- `accountant` - Robert Miller

### ADMINS:

- `admin` - System Administrator
- `hradmin` - HR Administrator
- `superadmin` - Super Administrator

### DOCTORS:

- `doctor` - Dr. John Smith
- `dr.johnson` - Dr. Sarah Johnson
- `dr.smith` - Dr. John Smith
- `dr.williams` - Dr. Michael Williams

### LAB_TECHS:

- `lab.tech1` - Robert Davis
- `lab.tech2` - Jennifer Garcia
- `labtech` - David Brown

### NURSES:

- `nurse` - Sarah Johnson
- `nurse.david` - David Brown
- `nurse.mary` - Mary Wilson

### PATIENTS:

- `patient1` - John Doe
- `patient2` - Jane Smith
- `patient3` - Bob Johnson

### PHARMACISTS:

- `pharmacist` - Lisa Davis

### RECEPTIONISTS:

- `receptionist` - Mary Wilson
- `receptionist2` - James Miller

## 🏗️ Deployment

### Development Deployment

1. **Environment Setup**

   ```bash
   # Set environment variables
   export FLASK_ENV=development
   export FLASK_DEBUG=1
   export SECRET_KEY=your-secret-key-here
   ```

2. **Run Development Server**
   ```bash
   python web_app.py
   ```

### Production Deployment

#### Option 1: Using Gunicorn (Recommended)

1. **Install Gunicorn**

   ```bash
   pip install gunicorn
   ```

2. **Create Gunicorn Configuration**

   ```python
   # gunicorn.conf.py
   bind = "0.0.0.0:8000"
   workers = 4
   worker_class = "sync"
   timeout = 120
   keepalive = 2
   max_requests = 1000
   max_requests_jitter = 100
   ```

3. **Run with Gunicorn**
   ```bash
   gunicorn --config gunicorn.conf.py web_app:app
   ```

#### Option 2: Using Docker

1. **Create Dockerfile**

   ```dockerfile
   FROM python:3.9-slim

   WORKDIR /app
   COPY requirements_web_app.txt .
   RUN pip install -r requirements_web_app.txt

   COPY . .

   EXPOSE 5000
   CMD ["gunicorn", "--bind", "0.0.0.0:5000", "web_app:app"]
   ```

2. **Build and Run**
   ```bash
   docker build -t medicare-pro .
   docker run -p 5000:5000 medicare-pro
   ```

#### Option 3: Using Apache/Nginx

1. **Install mod_wsgi (Apache)**

   ```bash
   pip install mod_wsgi
   ```

2. **Create WSGI file**

   ```python
   # app.wsgi
   import sys
   import os

   sys.path.insert(0, '/path/to/your/app')
   from web_app import app as application
   ```

3. **Configure Apache Virtual Host**

   ```apache
   <VirtualHost *:80>
       ServerName your-domain.com
       DocumentRoot /path/to/your/app
       WSGIScriptAlias / /path/to/your/app/app.wsgi

       <Directory /path/to/your/app>
           WSGIApplicationGroup %{GLOBAL}
           Require all granted
       </Directory>
   </VirtualHost>
   ```

### Environment Variables

Create a `.env` file for production:

```env
# Flask Configuration
FLASK_ENV=production
SECRET_KEY=your-super-secret-key-change-in-production
DATABASE_URL=sqlite:///instance/hospital_web.db

# Email Configuration
EMAIL_ENABLED=true
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=noreply@yourhospital.com

# SMS Configuration
SMS_ENABLED=true
SMS_API_KEY=your-sms-api-key
SMS_SENDER_ID=HOSPITAL

# Security
SESSION_TIMEOUT=3600
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION=1800

# Backup Configuration
BACKUP_ENABLED=true
BACKUP_SCHEDULE=daily
BACKUP_RETENTION_DAYS=30
```

## 🔧 Configuration

### Database Configuration

The system uses SQLite by default. For production, consider PostgreSQL:

```python
# config.py
SQLALCHEMY_DATABASE_URI = 'postgresql://user:password@localhost/hospital_db'
```

### Redis Configuration (Optional)

For caching and session storage:

```python
REDIS_URL = 'redis://localhost:6379/0'
CACHE_TYPE = 'redis'
```

### File Storage Configuration

```python
UPLOAD_FOLDER = 'uploads'
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx'}
```

## 🛠️ Maintenance

### Database Backup

```bash
# Manual backup
python -c "from backup_manager import BackupManager; BackupManager().create_backup()"

# Automated backups are configured in the system settings
```

### Log Management

```bash
# View application logs
tail -f logs/app.log

# View audit logs
tail -f audit_logs/audit.log
```

### System Health Check

```bash
# Check system status
python -c "from web_app import app; print('System OK')"
```

## 📚 API Documentation

The system provides RESTful APIs for integration:

- **Base URL**: `http://your-domain.com/api`
- **Authentication**: Bearer token or session-based
- **Format**: JSON

### Key Endpoints:

- `GET /api/patients` - List patients
- `POST /api/appointments` - Create appointment
- `GET /api/medical-records/{patient_id}` - Get medical records
- `POST /api/prescriptions` - Create prescription

## 🔒 Security Features

- **Password Policies**: Configurable complexity requirements
- **Session Management**: Secure session handling with timeout
- **CSRF Protection**: Cross-site request forgery protection
- **SQL Injection Prevention**: Parameterized queries
- **XSS Protection**: Input sanitization and output encoding
- **Audit Trail**: Complete activity logging
- **Data Encryption**: Sensitive data encryption at rest

## 🧪 Testing

```bash
# Run unit tests
python -m pytest tests/

# Run integration tests
python -m pytest tests/integration/

# Run security tests
python -m pytest tests/security/
```

## 📖 Documentation

- **User Manual**: Available in `/docs/user-manual.pdf`
- **Admin Guide**: Available in `/docs/admin-guide.pdf`
- **API Documentation**: Available at `/api/docs` when running
- **Database Schema**: Available in `/docs/database-schema.md`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check the `/docs` folder
- **Issues**: Report bugs via GitHub Issues
- **Email**: support@medicarepro.com
- **Phone**: +1-800-MEDICARE

## 🔄 Version History

- **v2.0.0** - Multi-tenant SaaS architecture, advanced security
- **v1.5.0** - Telemedicine, mobile app support
- **v1.0.0** - Initial release with core HMS features

---

**MediCare Pro** - Transforming Healthcare Management with Technology 🏥✨
