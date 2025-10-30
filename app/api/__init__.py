"""
API Blueprint for Hospital Management System
"""

from flask import Blueprint

# Create the API blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Import all routes to register them with the blueprint
from app.api.routes import *