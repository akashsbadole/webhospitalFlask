"""
Hospital Management System - Modular Flask Application
Main application factory and initialization
"""

from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import os

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

def create_app(config_name='default'):
    """Application factory function"""
    app = Flask(__name__, 
                static_folder='../static', 
                static_url_path='/static',
                template_folder='../templates')
    
    # Load configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
    
    # Use absolute path for database
    if not os.environ.get('DATABASE_URL'):
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance', 'hospital_web.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # Register blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from app.patients import bp as patients_bp
    app.register_blueprint(patients_bp, url_prefix='/patients')
    
    from app.appointments import bp as appointments_bp
    app.register_blueprint(appointments_bp, url_prefix='/appointments')
    
    from app.clinical import bp as clinical_bp
    app.register_blueprint(clinical_bp, url_prefix='/clinical')
    
    from app.pharmacy import bp as pharmacy_bp
    app.register_blueprint(pharmacy_bp, url_prefix='/pharmacy')
    
    from app.billing import bp as billing_bp
    app.register_blueprint(billing_bp, url_prefix='/billing')
    
    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    from app.api import api_bp
    app.register_blueprint(api_bp)
    
    # Register existing API routes if they exist
    try:
        from api_routes import api_bp as legacy_api_bp
        app.register_blueprint(legacy_api_bp, url_prefix='/api/legacy', name='legacy_api')
    except ImportError:
        pass
    
    # Context processor for global variables
    @app.context_processor
    def inject_global_vars():
        from app.utils.language import get_text, get_language
        from app.utils.helpers import get_all_settings
        from datetime import datetime
        from flask_login import current_user
        from app.models.admin import HospitalBranch
        
        current_branch = None
        if current_user.is_authenticated and 'current_branch_id' in session:
            current_branch = HospitalBranch.query.get(session['current_branch_id'])
        
        # Get settings for all templates
        all_settings = get_all_settings()
        
        return dict(
            get_text=get_text,
            get_language=get_language,
            datetime=datetime,
            current_branch=current_branch,
            settings=all_settings
        )
    
    return app
