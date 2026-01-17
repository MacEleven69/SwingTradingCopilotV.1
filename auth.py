"""
Authentication Module - License Gatekeeper
==========================================

Middleware for protecting API endpoints with license validation.
Implements decorator for easy route protection.
"""

from functools import wraps
from flask import request, jsonify
from database import validate_license


def require_license(f):
    """
    Decorator to require valid license for endpoint access
    
    Usage:
        @app.route('/analyze', methods=['POST'])
        @require_license
        def analyze():
            # Protected endpoint
            pass
    
    Expects license key in request header:
        X-License-Key: PRO-ABC123-XYZ789
    
    Returns:
        401 Unauthorized if:
        - License key missing
        - License key invalid
        - License revoked/expired
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Extract license key from header
        license_key = request.headers.get('X-License-Key')
        
        # Validate license
        is_valid, result = validate_license(license_key)
        
        if not is_valid:
            return jsonify({
                'error': 'Unauthorized',
                'message': result,
                'hint': 'Include valid license key in X-License-Key header'
            }), 401
        
        # License is valid - add to request context for use in endpoint
        request.license = result
        
        # Continue to endpoint
        return f(*args, **kwargs)
    
    return decorated_function


def optional_license(f):
    """
    Decorator for endpoints that work with or without license
    (but may provide enhanced features with license)
    
    Usage:
        @app.route('/demo', methods=['POST'])
        @optional_license
        def demo():
            if hasattr(request, 'license'):
                # Licensed user - full features
                pass
            else:
                # Guest - limited features
                pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Try to validate license, but don't block if missing
        license_key = request.headers.get('X-License-Key')
        
        if license_key:
            is_valid, result = validate_license(license_key)
            if is_valid:
                request.license = result
        
        # Continue regardless of license status
        return f(*args, **kwargs)
    
    return decorated_function


def get_license_info(request):
    """
    Extract license information from request
    
    Args:
        request: Flask request object
        
    Returns:
        dict: License information or None
    """
    if hasattr(request, 'license'):
        return {
            'email': request.license.email,
            'tier': request.license.tier,
            'request_count': request.license.request_count
        }
    return None


def check_rate_limit(license, endpoint='analyze'):
    """
    Check if license has exceeded rate limits
    
    Args:
        license: License object
        endpoint: Endpoint being accessed
        
    Returns:
        tuple: (allowed, message)
    """
    # Rate limits by tier (requests per day)
    rate_limits = {
        'free': 10,
        'pro': 1000,
        'enterprise': 10000
    }
    
    limit = rate_limits.get(license.tier, 10)
    
    # For now, just check total count (in production, track daily/hourly)
    # This is a placeholder - implement time-based limits in production
    
    if license.request_count >= limit * 365:  # Lifetime limit
        return False, f"Rate limit exceeded for {license.tier} tier"
    
    return True, "OK"


if __name__ == '__main__':
    """Test authentication module"""
    print("\n" + "="*80)
    print("AUTHENTICATION MODULE TEST")
    print("="*80)
    
    print("\n[OK] Decorators defined:")
    print("   - @require_license (strict)")
    print("   - @optional_license (flexible)")
    
    print("\n[INFO] Usage Example:")
    print("""
    from auth import require_license
    
    @app.route('/analyze', methods=['POST'])
    @require_license
    def analyze():
        # This endpoint now requires valid license
        license_info = get_license_info(request)
        return jsonify({'user': license_info['email']})
    """)
    
    print("\n[OK] Authentication module ready!")






















