"""
Tenant Context Manager
Handles tenant identification and context management for multi-tenant SaaS
"""

from flask import g, request, session, redirect, url_for, abort
from functools import wraps
import logging

logger = logging.getLogger(__name__)

class TenantContext:
    def __init__(self, app, db):
        self.app = app
        self.db = db
        
    def get_current_tenant(self):
        """Get current tenant from request context"""
        # Check if already loaded in request context
        if hasattr(g, 'current_tenant'):
            return g.current_tenant
        
        # Import here to avoid circular imports
        try:
            from web_app import Tenant
        except ImportError:
            logger.error("Failed to import Tenant model")
            return None
        
        # Try to get from subdomain
        host = request.host.split(':')[0]
        parts = host.split('.')
        
        # Check if subdomain exists (e.g., hospital1.localhost or hospital1.yourdomain.com)
        if len(parts) >= 2:
            subdomain = parts[0]
            
            # Skip www and common subdomains
            if subdomain not in ['www', 'localhost', '127']:
                try:
                    tenant = self.db.session.query(Tenant).filter_by(
                        subdomain=subdomain, 
                        is_active=True
                    ).first()
                    
                    if tenant:
                        g.current_tenant = tenant
                        logger.info(f"Tenant loaded from subdomain: {tenant.name}")
                        return tenant
                except Exception as e:
                    logger.error(f"Error querying tenant by subdomain: {e}")
        
        # Try to get from custom domain
        try:
            tenant = self.db.session.query(Tenant).filter_by(
                custom_domain=host, 
                is_active=True
            ).first()
            
            if tenant:
                g.current_tenant = tenant
                logger.info(f"Tenant loaded from custom domain: {tenant.name}")
                return tenant
        except Exception as e:
            logger.error(f"Error querying tenant by custom domain: {e}")
        
        # Try to get from session (for admin panel or manual selection)
        tenant_id = session.get('tenant_id')
        if tenant_id:
            try:
                tenant = self.db.session.get(Tenant, tenant_id)
                if tenant and tenant.is_active:
                    g.current_tenant = tenant
                    logger.info(f"Tenant loaded from session: {tenant.name}")
                    return tenant
            except Exception as e:
                logger.error(f"Error querying tenant by session: {e}")
        
        # No tenant found
        logger.debug(f"No tenant found for host: {host}")
        return None
    
    def set_current_tenant(self, tenant):
        """Set current tenant in context"""
        g.current_tenant = tenant
        session['tenant_id'] = tenant.id
        logger.info(f"Tenant set in context: {tenant.name}")
    
    def clear_tenant(self):
        """Clear tenant from context"""
        if hasattr(g, 'current_tenant'):
            delattr(g, 'current_tenant')
        session.pop('tenant_id', None)
    
    def require_tenant(self, f):
        """Decorator to require tenant context"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            tenant = self.get_current_tenant()
            if not tenant:
                logger.warning("Access denied: No tenant context")
                return redirect(url_for('select_tenant'))
            return f(*args, **kwargs)
        return decorated_function
    
    def validate_tenant_access(self, f):
        """Decorator to validate tenant subscription and access"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from datetime import datetime
            
            tenant = self.get_current_tenant()
            if not tenant:
                abort(403, 'No tenant context')
            
            # Check if tenant is active
            if not tenant.is_active:
                return redirect(url_for('tenant_suspended'))
            
            # Check subscription status
            if tenant.subscription_status == 'suspended':
                return redirect(url_for('subscription_suspended'))
            
            if tenant.subscription_status == 'cancelled':
                return redirect(url_for('subscription_cancelled'))
            
            # Check trial expiry
            if tenant.subscription_status == 'trial':
                if tenant.trial_ends_at and tenant.trial_ends_at < datetime.utcnow():
                    return redirect(url_for('trial_expired'))
            
            # Check subscription expiry
            if tenant.subscription_status == 'active':
                if tenant.subscription_ends_at and tenant.subscription_ends_at < datetime.utcnow():
                    return redirect(url_for('subscription_expired'))
            
            return f(*args, **kwargs)
        return decorated_function

# Global instance
tenant_context = None

def init_tenant_context(app, db):
    """Initialize tenant context manager"""
    global tenant_context
    tenant_context = TenantContext(app, db)
    
    @app.before_request
    def load_tenant():
        """Load tenant before each request"""
        # Skip for static files and certain endpoints
        if request.endpoint and not request.endpoint.startswith('static'):
            # Only load tenant if we're in an application context
            try:
                tenant_context.get_current_tenant()
            except Exception as e:
                logger.error(f"Error loading tenant: {e}")
    
    logger.info("Tenant context manager initialized")
    return tenant_context

def get_tenant():
    """Helper function to get current tenant"""
    if tenant_context:
        return tenant_context.get_current_tenant()
    return None
