"""
Main Blueprint for Hospital Management System
"""

from flask import Blueprint

bp = Blueprint('main', __name__)

from . import routes
