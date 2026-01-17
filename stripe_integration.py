"""
Stripe Payment Integration
===========================

Handles payment processing, checkout sessions, and webhook events.
Automatically creates license keys upon successful payment.
"""

import os
import stripe
from datetime import datetime
from dotenv import load_dotenv
from database import create_license

# Load environment variables
load_dotenv()

def get_stripe_api_key():
    """Get Stripe API key at runtime"""
    key = os.getenv('STRIPE_SECRET_KEY')
    if key:
        stripe.api_key = key
    return key

def get_webhook_secret():
    """Get webhook secret at runtime"""
    return os.getenv('STRIPE_WEBHOOK_SECRET')

# Configuration (read at runtime when needed)
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')
STRIPE_PRODUCT_ID = os.getenv('STRIPE_PRODUCT_ID')
STRIPE_PRICE_ID = os.getenv('STRIPE_PRICE_ID')


def create_checkout_session(success_url, cancel_url, customer_email=None, tier='pro'):
    """
    Create a Stripe checkout session for purchasing a license
    
    Args:
        success_url: URL to redirect after successful payment
        cancel_url: URL to redirect if payment is cancelled
        customer_email: Optional pre-filled customer email
        tier: License tier (pro, enterprise)
        
    Returns:
        dict: Checkout session object with URL
    """
    try:
        # Prepare session parameters
        session_params = {
            'payment_method_types': ['card'],
            'line_items': [{
                'price': STRIPE_PRICE_ID,
                'quantity': 1,
            }],
            'mode': 'subscription',  # or 'payment' for one-time
            'success_url': success_url,
            'cancel_url': cancel_url,
            'metadata': {
                'source': 'chrome_extension',
                'tier': tier,
                'created_at': datetime.utcnow().isoformat()
            }
        }
        
        # Add customer email if provided
        if customer_email:
            session_params['customer_email'] = customer_email
        
        # Create checkout session
        session = stripe.checkout.Session.create(**session_params)
        
        print(f"[OK] Checkout session created: {session.id}")
        
        return {
            'session_id': session.id,
            'url': session.url,
            'publishable_key': STRIPE_PUBLISHABLE_KEY
        }
        
    except Exception as e:
        print(f"[ERROR] Error creating checkout session: {e}")
        return {'error': str(e)}


def verify_webhook_signature(payload, signature):
    """
    Verify that webhook came from Stripe
    
    Args:
        payload: Raw request body
        signature: Stripe-Signature header value
        
    Returns:
        event: Verified Stripe event object or None
    """
    try:
        # Initialize Stripe API key at runtime
        api_key = get_stripe_api_key()
        print(f"[DEBUG] Stripe API key set: {bool(api_key)}")
        
        # Read webhook secret at runtime
        webhook_secret = get_webhook_secret()
        print(f"[DEBUG] Webhook secret set: {bool(webhook_secret)}")
        print(f"[DEBUG] Webhook secret prefix: {webhook_secret[:10] if webhook_secret else 'NONE'}...")
        print(f"[DEBUG] Signature received: {signature[:50] if signature else 'NONE'}...")
        print(f"[DEBUG] Payload type: {type(payload)}, length: {len(payload) if payload else 0}")
        
        if not webhook_secret:
            print("[ERROR] STRIPE_WEBHOOK_SECRET not set!")
            return None
        
        if not signature:
            print("[ERROR] No signature provided!")
            return None
        
        # Ensure payload is bytes
        if isinstance(payload, str):
            payload = payload.encode('utf-8')
        
        event = stripe.Webhook.construct_event(
            payload, signature, webhook_secret
        )
        print(f"[DEBUG] Event constructed successfully: {event['type']}")
        return event
    except ValueError as e:
        print(f"[ERROR] Invalid payload: {e}")
        import traceback
        traceback.print_exc()
        return None
    except stripe.error.SignatureVerificationError as e:
        print(f"[ERROR] Invalid signature: {e}")
        import traceback
        traceback.print_exc()
        return None
    except Exception as e:
        print(f"[ERROR] Webhook verification error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None


def handle_checkout_completed(session):
    """
    Handle successful checkout - create license key
    
    Args:
        session: Stripe checkout session object
        
    Returns:
        dict: Created license information
    """
    try:
        # Extract customer information
        customer_email = session.get('customer_details', {}).get('email') or session.get('customer_email')
        
        if not customer_email:
            print("[!]  No customer email found in session")
            return {'error': 'No customer email'}
        
        # Get tier from metadata (default to 'pro')
        tier = session.get('metadata', {}).get('tier', 'pro')
        
        # Create license key
        license = create_license(customer_email, tier=tier, status='active')
        
        print(f"[OK] License created for {customer_email}: {license.key}")
        
        # Return license info for email sending
        return {
            'email': customer_email,
            'license_key': license.key,
            'tier': tier,
            'session_id': session.get('id')
        }
        
    except Exception as e:
        print(f"[ERROR] Error handling checkout: {e}")
        return {'error': str(e)}


def handle_subscription_deleted(subscription):
    """
    Handle subscription cancellation - revoke license
    
    Args:
        subscription: Stripe subscription object
        
    Returns:
        dict: Result of revocation
    """
    try:
        # Get customer email from subscription
        customer_id = subscription.get('customer')
        customer = stripe.Customer.retrieve(customer_id)
        customer_email = customer.get('email')
        
        if not customer_email:
            print("[!]  No customer email found")
            return {'error': 'No customer email'}
        
        # Find and revoke license
        from database import License, db
        license = License.query.filter_by(email=customer_email, status='active').first()
        
        if license:
            license.status = 'revoked'
            db.session.commit()
            print(f"[OK] License revoked for {customer_email}: {license.key}")
            return {'revoked': license.key}
        else:
            print(f"[!]  No active license found for {customer_email}")
            return {'message': 'No active license found'}
            
    except Exception as e:
        print(f"[ERROR] Error handling subscription deletion: {e}")
        return {'error': str(e)}


def send_license_email(email, license_key, tier='pro'):
    """
    Send license key to customer via email
    
    Args:
        email: Customer email address
        license_key: Generated license key
        tier: License tier
        
    Returns:
        bool: Success status
    """
    # TODO: Implement email sending
    # For now, just log it
    
    print("\n" + "="*80)
    print("[EMAIL] EMAIL TO SEND")
    print("="*80)
    print(f"To: {email}")
    print(f"Subject: Your Swing Trading Copilot License Key")
    print()
    print(f"License Key: {license_key}")
    print(f"Tier: {tier.upper()}")
    print("="*80 + "\n")
    
    # TODO: Implement with SendGrid, AWS SES, or SMTP
    """
    Example with SendGrid:
    
    import sendgrid
    from sendgrid.helpers.mail import Mail
    
    sg = sendgrid.SendGridAPIClient(api_key=os.getenv('SENDGRID_API_KEY'))
    message = Mail(
        from_email='support@swingcopilot.com',
        to_emails=email,
        subject='Your Swing Trading Copilot License Key',
        html_content=f'''
            <h1>Welcome to Swing Trading Copilot!</h1>
            <p>Your License Key: <strong>{license_key}</strong></p>
            <p>Get started at: https://chrome.google.com/webstore/...</p>
        '''
    )
    response = sg.send(message)
    return response.status_code == 202
    """
    
    return True


def get_session_details(session_id):
    """
    Retrieve checkout session details
    
    Args:
        session_id: Stripe session ID
        
    Returns:
        dict: Session details
    """
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        return {
            'id': session.id,
            'payment_status': session.payment_status,
            'customer_email': session.get('customer_details', {}).get('email'),
            'amount_total': session.amount_total,
            'currency': session.currency
        }
    except Exception as e:
        print(f"[ERROR] Error retrieving session: {e}")
        return {'error': str(e)}


if __name__ == '__main__':
    """Test Stripe integration"""
    print("\n" + "="*80)
    print("STRIPE INTEGRATION TEST")
    print("="*80)
    
    print(f"\n[OK] Stripe API Key: {stripe.api_key[:15]}...")
    print(f"[OK] Product ID: {STRIPE_PRODUCT_ID}")
    print(f"[OK] Price ID: {STRIPE_PRICE_ID}")
    
    # Test creating checkout session
    print("\n[INFO] Testing checkout session creation...")
    result = create_checkout_session(
        success_url='http://localhost:5000/success?session_id={CHECKOUT_SESSION_ID}',
        cancel_url='http://localhost:5000/cancel',
        customer_email='test@example.com'
    )
    
    if 'url' in result:
        print(f"[OK] Checkout URL: {result['url']}")
    else:
        print(f"[ERROR] Error: {result.get('error')}")
    
    print("\n" + "="*80)






















