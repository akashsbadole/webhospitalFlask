"""
Patients Blueprint for Hospital Management System
"""

from flask import Blueprint

bp = Blueprint('patients', __name__)

from . import routes
