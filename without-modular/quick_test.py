#!/usr/bin/env python3
"""
Quick test to verify the pharmacy.orders endpoint exists
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import create_app
    app = create_app()
    
    with app.app_context():
        # Test if the endpoint exists
        try:
            from flask import url_for
            url = url_for('pharmacy.orders')
            print(f"✓ pharmacy.orders endpoint exists: {url}")
        except Exception as e:
            print(f"✗ pharmacy.orders endpoint error: {e}")
        
        # List all pharmacy endpoints
        pharmacy_endpoints = [rule.endpoint for rule in app.url_map.iter_rules() if 'pharmacy' in rule.endpoint]
        print(f"Available pharmacy endpoints: {pharmacy_endpoints}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()