"""
License Management CLI
======================

Command-line tool for managing API licenses.

Usage:
    python manage_keys.py create <email> [tier]
    python manage_keys.py revoke <key>
    python manage_keys.py list
    python manage_keys.py stats
    python manage_keys.py info <key>
"""

import sys
import os
from datetime import datetime
from flask import Flask
from database import db, License, create_license, revoke_license, get_license_stats


def init_app():
    """Initialize Flask app for database access"""
    app = Flask(__name__)
    
    # Database configuration
    db_path = os.path.join(os.path.dirname(__file__), 'licenses.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
    
    return app


def cmd_create(email, tier='pro'):
    """Create a new license"""
    app = init_app()
    
    with app.app_context():
        print(f"\n[KEY] Creating new license for: {email}")
        print(f"   Tier: {tier.upper()}")
        
        try:
            license = create_license(email, tier=tier)
            
            print(f"\n[OK] License Created Successfully!")
            print("="*60)
            print(f"License Key:  {license.key}")
            print(f"Email:        {license.email}")
            print(f"Tier:         {license.tier.upper()}")
            print(f"Status:       {license.status.upper()}")
            print(f"Created:      {license.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print("="*60)
            print(f"\n[INFO] Usage:")
            print(f"   curl -X POST http://localhost:5000/api/analyze \\")
            print(f"     -H 'X-License-Key: {license.key}' \\")
            print(f"     -H 'Content-Type: application/json' \\")
            print(f"     -d '{{\"ticker\": \"AAPL\", \"use_ai\": true}}'")
            print()
            
            return license
            
        except Exception as e:
            print(f"\n[ERROR] Error creating license: {e}")
            return None


def cmd_revoke(key):
    """Revoke a license"""
    app = init_app()
    
    with app.app_context():
        print(f"\n[BLOCKED] Revoking license: {key}")
        
        # Check if exists first
        license = License.query.filter_by(key=key).first()
        
        if not license:
            print(f"[ERROR] License not found: {key}")
            return False
        
        print(f"   Email: {license.email}")
        print(f"   Status: {license.status}")
        
        if license.status == 'revoked':
            print(f"[!]  License already revoked")
            return False
        
        success = revoke_license(key)
        
        if success:
            print(f"[OK] License revoked successfully")
            return True
        else:
            print(f"[ERROR] Failed to revoke license")
            return False


def cmd_list(status=None):
    """List all licenses"""
    app = init_app()
    
    with app.app_context():
        print(f"\n[INFO] License List")
        print("="*80)
        
        query = License.query
        if status:
            query = query.filter_by(status=status)
        
        licenses = query.order_by(License.created_at.desc()).all()
        
        if not licenses:
            print("No licenses found")
            return
        
        print(f"{'Key':<25} {'Email':<30} {'Tier':<8} {'Status':<10} {'Requests':<10}")
        print("-"*80)
        
        for lic in licenses:
            key_short = lic.key[:22] + "..."
            email_short = lic.email[:27] + "..." if len(lic.email) > 30 else lic.email
            print(f"{key_short:<25} {email_short:<30} {lic.tier.upper():<8} {lic.status.upper():<10} {lic.request_count:<10}")
        
        print("="*80)
        print(f"Total: {len(licenses)} licenses")
        print()


def cmd_stats():
    """Show license statistics"""
    app = init_app()
    
    with app.app_context():
        stats = get_license_stats()
        
        print(f"\n[STATS] License Statistics")
        print("="*60)
        print(f"Total Licenses:    {stats['total_licenses']}")
        print(f"Active:            {stats['active']}")
        print(f"Revoked:           {stats['revoked']}")
        print(f"Total API Calls:   {stats['total_requests']:,}")
        print("="*60)
        
        # Show top users
        top_users = License.query.order_by(License.request_count.desc()).limit(5).all()
        
        if top_users:
            print(f"\n[TOP] Top Users:")
            for i, lic in enumerate(top_users, 1):
                print(f"   {i}. {lic.email:<30} {lic.request_count:>6} requests")
        
        print()


def cmd_info(key):
    """Show detailed info about a license"""
    app = init_app()
    
    with app.app_context():
        license = License.query.filter_by(key=key).first()
        
        if not license:
            print(f"\n[ERROR] License not found: {key}")
            return
        
        print(f"\n[SEARCH] License Details")
        print("="*60)
        print(f"Key:           {license.key}")
        print(f"Email:         {license.email}")
        print(f"Tier:          {license.tier.upper()}")
        print(f"Status:        {license.status.upper()}")
        print(f"Created:       {license.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        if license.last_used:
            print(f"Last Used:     {license.last_used.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        else:
            print(f"Last Used:     Never")
        
        print(f"Request Count: {license.request_count:,}")
        print("="*60)
        print()


def show_help():
    """Show usage help"""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                         LICENSE MANAGEMENT CLI                               ║
╚══════════════════════════════════════════════════════════════════════════════╝

COMMANDS:

  create <email> [tier]      Create a new license
                             Tier: free, pro (default), enterprise
                             
  revoke <key>               Revoke an existing license
  
  list [status]              List all licenses
                             Status: active, revoked (optional filter)
  
  stats                      Show license statistics
  
  info <key>                 Show detailed info about a license

EXAMPLES:

  # Create a PRO license
  python manage_keys.py create john@example.com
  
  # Create an ENTERPRISE license
  python manage_keys.py create vip@company.com enterprise
  
  # Revoke a license
  python manage_keys.py revoke PRO-ABC123-XYZ789
  
  # List all active licenses
  python manage_keys.py list active
  
  # Show statistics
  python manage_keys.py stats
  
  # Get license details
  python manage_keys.py info PRO-ABC123-XYZ789

TIERS:

  FREE       - 10 requests/day
  PRO        - 1,000 requests/day
  ENTERPRISE - 10,000 requests/day

""")


def main():
    """Main CLI entry point"""
    
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == 'create':
        if len(sys.argv) < 3:
            print("[ERROR] Error: Email required")
            print("Usage: python manage_keys.py create <email> [tier]")
            return
        
        email = sys.argv[2]
        tier = sys.argv[3] if len(sys.argv) > 3 else 'pro'
        
        if tier.lower() not in ['free', 'pro', 'enterprise']:
            print(f"[ERROR] Error: Invalid tier '{tier}'")
            print("Valid tiers: free, pro, enterprise")
            return
        
        cmd_create(email, tier)
    
    elif command == 'revoke':
        if len(sys.argv) < 3:
            print("[ERROR] Error: License key required")
            print("Usage: python manage_keys.py revoke <key>")
            return
        
        key = sys.argv[2]
        cmd_revoke(key)
    
    elif command == 'list':
        status = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_list(status)
    
    elif command == 'stats':
        cmd_stats()
    
    elif command == 'info':
        if len(sys.argv) < 3:
            print("[ERROR] Error: License key required")
            print("Usage: python manage_keys.py info <key>")
            return
        
        key = sys.argv[2]
        cmd_info(key)
    
    elif command in ['help', '-h', '--help']:
        show_help()
    
    else:
        print(f"[ERROR] Unknown command: {command}")
        print("Run 'python manage_keys.py help' for usage")


if __name__ == '__main__':
    main()

