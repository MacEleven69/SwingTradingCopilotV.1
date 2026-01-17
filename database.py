"""
Database Module - License Management
====================================

Environment-aware database configuration:
- Production (Render): Uses DATABASE_URL (Postgres)
- Local Development: Uses SQLite (licenses.db)
"""

import os
import secrets
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

db = SQLAlchemy()


def get_database_url():
    """
    Get database URL based on environment.
    
    Production (Render/Heroku): Uses DATABASE_URL env var (Postgres)
    Local Development: Uses SQLite file
    
    Returns:
        str: Database connection URL
    """
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url:
        # Production: Use Postgres
        # Fix for SQLAlchemy 1.4+: postgres:// -> postgresql://
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        print("[DB] Using Production Database (Postgres)")
        return database_url
    else:
        # Local: Use SQLite
        db_path = os.path.join(os.path.dirname(__file__), 'licenses.db')
        print("[DB] Using Local Database (SQLite)")
        return f'sqlite:///{db_path}'


class License(db.Model):
    """
    License Model - Tracks API access keys
    
    Attributes:
        key: Unique license key (e.g., "PRO-ABC123-XYZ789")
        email: Customer email address
        status: License status (active, revoked, expired)
        tier: License tier (free, pro, enterprise)
        created_at: Timestamp of license creation
        last_used: Timestamp of last API call
        request_count: Total number of API requests
    """
    __tablename__ = 'licenses'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(20), default='active', nullable=False)
    tier = db.Column(db.String(20), default='pro', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_used = db.Column(db.DateTime, nullable=True)
    request_count = db.Column(db.Integer, default=0, nullable=False)
    
    def __repr__(self):
        return f'<License {self.key[:12]}... ({self.status})>'
    
    def to_dict(self):
        """Convert license to dictionary"""
        return {
            'key': self.key,
            'email': self.email,
            'status': self.status,
            'tier': self.tier,
            'created_at': self.created_at.isoformat(),
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'request_count': self.request_count
        }
    
    def is_valid(self):
        """Check if license is valid and active"""
        return self.status == 'active'
    
    def record_usage(self):
        """Record API usage"""
        self.last_used = datetime.utcnow()
        self.request_count += 1
        db.session.commit()


def generate_license_key(prefix='PRO'):
    """
    Generate a secure, unique license key
    
    Format: PREFIX-XXXXXX-YYYYYY
    Example: PRO-A3F92E-B7D4C1
    
    Args:
        prefix: License tier prefix (PRO, ENT, FREE)
        
    Returns:
        str: Unique license key
    """
    # Generate two random segments
    segment1 = secrets.token_hex(3).upper()  # 6 characters
    segment2 = secrets.token_hex(3).upper()  # 6 characters
    
    key = f"{prefix}-{segment1}-{segment2}"
    
    # Ensure uniqueness (very rare collision, but safe)
    while License.query.filter_by(key=key).first():
        segment1 = secrets.token_hex(3).upper()
        segment2 = secrets.token_hex(3).upper()
        key = f"{prefix}-{segment1}-{segment2}"
    
    return key


def create_license(email, tier='pro', status='active'):
    """
    Create a new license
    
    Args:
        email: Customer email
        tier: License tier (free, pro, enterprise)
        status: Initial status (default: active)
        
    Returns:
        License: Created license object
    """
    # Generate key based on tier
    tier_prefixes = {
        'free': 'FREE',
        'pro': 'PRO',
        'enterprise': 'ENT'
    }
    prefix = tier_prefixes.get(tier.lower(), 'PRO')
    
    key = generate_license_key(prefix)
    
    license = License(
        key=key,
        email=email,
        tier=tier.lower(),
        status=status
    )
    
    db.session.add(license)
    db.session.commit()
    
    return license


def validate_license(key):
    """
    Validate a license key
    
    Args:
        key: License key to validate
        
    Returns:
        tuple: (is_valid, license_obj or error_message)
    """
    if not key:
        return False, "License key is required"
    
    license = License.query.filter_by(key=key).first()
    
    if not license:
        return False, "License key not found"
    
    if not license.is_valid():
        return False, f"License is {license.status}"
    
    # Record usage
    license.record_usage()
    
    return True, license


def revoke_license(key):
    """
    Revoke a license
    
    Args:
        key: License key to revoke
        
    Returns:
        bool: True if revoked, False if not found
    """
    license = License.query.filter_by(key=key).first()
    
    if not license:
        return False
    
    license.status = 'revoked'
    db.session.commit()
    
    return True


def get_license_stats():
    """
    Get license statistics
    
    Returns:
        dict: Statistics about licenses
    """
    total = License.query.count()
    active = License.query.filter_by(status='active').count()
    revoked = License.query.filter_by(status='revoked').count()
    
    # Total requests across all licenses
    total_requests = db.session.query(func.sum(License.request_count)).scalar() or 0
    
    return {
        'total_licenses': total,
        'active': active,
        'revoked': revoked,
        'total_requests': total_requests
    }


def init_db(app):
    """
    Initialize database with Flask app
    
    Args:
        app: Flask application instance
    """
    # Set database URL based on environment
    app.config['SQLALCHEMY_DATABASE_URI'] = get_database_url()
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        print("[OK] Database initialized")
        
        # Check if we have any licenses
        license_count = License.query.count()
        if license_count == 0:
            print("[!] No licenses found. Create one with: python manage_keys.py create <email>")
        else:
            stats = get_license_stats()
            print(f"[DB] Licenses: {stats['active']} active, {stats['revoked']} revoked")


if __name__ == '__main__':
    """Test license generation"""
    print("\n" + "="*80)
    print("LICENSE GENERATOR TEST")
    print("="*80)
    
    # Test key generation
    print("\n[KEY] Generating test keys:")
    for tier in ['free', 'pro', 'enterprise']:
        key = generate_license_key(tier.upper()[:3] if tier != 'enterprise' else 'ENT')
        print(f"   {tier.upper():12} → {key}")
    
    print("\n[OK] License generation working!")
