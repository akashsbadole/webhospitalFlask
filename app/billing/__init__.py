"""
Billing Blueprint for Hospital Management System
"""

from flask import Blueprint

bp = Blueprint('billing', __name__)

from . import routes
