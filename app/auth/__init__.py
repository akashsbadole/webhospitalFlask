"""
Authentication Blueprint for Hospital Management System
"""

from flask import Blueprint

bp = Blueprint('auth', __name__)

from . import routes
