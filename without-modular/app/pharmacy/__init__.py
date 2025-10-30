"""
Pharmacy Blueprint for Hospital Management System
"""

from flask import Blueprint

bp = Blueprint('pharmacy', __name__)

from . import routes
