"""
Clinical Blueprint for Hospital Management System
"""

from flask import Blueprint

bp = Blueprint('clinical', __name__)

from . import routes
