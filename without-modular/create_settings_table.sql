-- Create hospital_setting table
CREATE TABLE IF NOT EXISTS hospital_setting (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER,
    setting_key VARCHAR(100) NOT NULL,
    setting_value TEXT,
    setting_type VARCHAR(20) DEFAULT 'string',
    category VARCHAR(50) DEFAULT 'general',
    description TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Insert default settings
INSERT OR IGNORE INTO hospital_setting (setting_key, setting_value, setting_type, category, description) VALUES
('hospital_name', 'MediCare Pro', 'string', 'organization', 'Hospital name'),
('hospital_tagline', 'Your Health, Our Priority', 'string', 'organization', 'Hospital tagline'),
('primary_color', '#0d6efd', 'string', 'organization', 'Primary theme color'),
('secondary_color', '#6c757d', 'string', 'organization', 'Secondary theme color'),
('currency', 'USD', 'string', 'billing', 'Default currency'),
('password_min_length', '8', 'number', 'security', 'Minimum password length'),
('password_expiry_days', '90', 'number', 'security', 'Password expiry in days'),
('default_language', 'en', 'string', 'organization', 'Default language'),
('enable_multilingual', 'false', 'boolean', 'organization', 'Enable multilingual support');