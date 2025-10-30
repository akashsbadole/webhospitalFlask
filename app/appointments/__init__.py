"""
Appointments Blueprint for Hospital Management System
"""

from flask import Blueprint

bp = Blueprint('appointments', __name__)

from . import routes
