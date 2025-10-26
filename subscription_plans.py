"""
Subscription Plans Configuration
Defines available subscription tiers and their features
"""

SUBSCRIPTION_PLANS = {
    'basic': {
        'name': 'Basic',
        'description': 'Perfect for small clinics and practices',
        'price_monthly': 99,
        'price_yearly': 990,  # 2 months free
        'max_users': 10,
        'max_patients': 1000,
        'max_storage_gb': 5,
        'features': [
            'Patient Management',
            'Appointment Scheduling',
            'Basic EHR',
            'Billing & Payments',
            'Email Support',
            '5GB Storage',
            'Mobile Access'
        ],
        'color': 'primary'
    },
    'professional': {
        'name': 'Professional',
        'description': 'For growing hospitals and medical centers',
        'price_monthly': 299,
        'price_yearly': 2990,  # 2 months free
        'max_users': 50,
        'max_patients': 10000,
        'max_storage_gb': 50,
        'features': [
            'All Basic Features',
            'Laboratory Management',
            'Pharmacy Management',
            'Radiology/Imaging',
            'Inventory Management',
            'Advanced Reports & Analytics',
            'Priority Email Support',
            '50GB Storage',
            'API Access'
        ],
        'color': 'success'
    },
    'enterprise': {
        'name': 'Enterprise',
        'description': 'For large hospitals and healthcare networks',
        'price_monthly': 999,
        'price_yearly': 9990,  # 2 months free
        'max_users': -1,  # Unlimited
        'max_patients': -1,  # Unlimited
        'max_storage_gb': 500,
        'features': [
            'All Professional Features',
            'Multi-Branch Support',
            'Custom Integrations',
            'Dedicated Database (Optional)',
            'White-Label Branding',
            'Emergency Management',
            'Quality Management',
            'Document Management',
            '24/7 Phone Support',
            'Custom Training',
            '500GB Storage',
            'Dedicated Account Manager'
        ],
        'color': 'warning'
    }
}

# Add-on pricing
ADDONS = {
    'extra_user': {
        'name': 'Additional User',
        'price_monthly': 10,
        'description': 'Add one more user to your plan'
    },
    'extra_storage': {
        'name': 'Extra Storage (per GB)',
        'price_monthly': 5,
        'description': 'Additional storage space'
    },
    'custom_domain': {
        'name': 'Custom Domain',
        'price_monthly': 20,
        'description': 'Use your own domain name'
    },
    'white_label': {
        'name': 'White-Label Branding',
        'price_monthly': 100,
        'description': 'Remove our branding and use yours'
    },
    'priority_support': {
        'name': 'Priority Support',
        'price_monthly': 50,
        'description': '24/7 priority support access'
    }
}

def get_plan_details(plan_name):
    """Get details for a specific plan"""
    return SUBSCRIPTION_PLANS.get(plan_name, SUBSCRIPTION_PLANS['basic'])

def calculate_price(plan_name, billing_cycle='monthly', addons=None):
    """Calculate total price including add-ons"""
    plan = SUBSCRIPTION_PLANS.get(plan_name, SUBSCRIPTION_PLANS['basic'])
    
    if billing_cycle == 'yearly':
        base_price = plan['price_yearly']
    else:
        base_price = plan['price_monthly']
    
    addon_price = 0
    if addons:
        for addon_key, quantity in addons.items():
            if addon_key in ADDONS:
                addon_price += ADDONS[addon_key]['price_monthly'] * quantity
    
    return base_price + addon_price

def get_plan_limits(plan_name):
    """Get resource limits for a plan"""
    plan = SUBSCRIPTION_PLANS.get(plan_name, SUBSCRIPTION_PLANS['basic'])
    return {
        'max_users': plan['max_users'],
        'max_patients': plan['max_patients'],
        'max_storage_gb': plan['max_storage_gb']
    }
