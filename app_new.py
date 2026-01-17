"""
Swing Trading Copilot - Flask Backend (REST API Only)
Production-ready API with NO WebSocket interference with HFT bot
"""

from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
from flask_caching import Cache
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import re
import os
from config import config
from swing_score_engine import SwingScoreEngine
from market_analyst import MarketAnalyst
from database import db, init_db, get_license_stats, License
from auth import require_license, get_license_info
from stripe_integration import (
    create_checkout_session,
    verify_webhook_signature,
    handle_checkout_completed,
    handle_subscription_deleted,
    send_license_email,
    get_session_details
)

app = Flask(__name__)
CORS(app)  # Allow Chrome Extension to call API

# Initialize database (environment-aware: Postgres in production, SQLite locally)
# Database URL is determined by DATABASE_URL env var (see database.py)
init_db(app)

# Configure caching (15 minute TTL)
cache = Cache(app, config={
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': config.CACHE_TIMEOUT
})

# Initialize engines
print("\n" + "="*80)
print("INITIALIZING SWING TRADING COPILOT BACKEND")
print("="*80)

try:
    config.validate()
    print("\n[OK] Configuration validated")
    
    summary = config.get_summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")
    
    print("\n[!]  IMPORTANT: Using REST API only (no WebSocket)")
    print("   Safe for HFT bot coexistence [OK]")
    
except Exception as e:
    print(f"\n[ERROR] Configuration error: {e}")
    print("   Backend may not function correctly")

# Initialize components
try:
    scorer = SwingScoreEngine()
    print("\n[OK] Swing Score Engine ready (REST API only)")
except Exception as e:
    print(f"\n[ERROR] Failed to initialize Swing Score Engine: {e}")
    scorer = None

try:
    market_analyst = MarketAnalyst()
    print("[OK] Market Analyst ready (Holistic AI)")
except Exception as e:
    print(f"[ERROR] Failed to initialize Market Analyst: {e}")
    market_analyst = None

print("\n" + "="*80)


def validate_ticker(ticker: str) -> tuple[bool, str]:
    """
    Validate ticker symbol
    Returns: (is_valid, cleaned_ticker)
    """
    if not ticker:
        return False, ""
    
    # Remove $ and spaces, uppercase
    cleaned = ticker.strip().upper().replace('$', '')
    
    # Must be 1-5 letters only
    if not re.match(r'^[A-Z]{1,5}$', cleaned):
        return False, ""
    
    return True, cleaned


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'api_type': 'REST_ONLY',
        'websocket': 'DISABLED',
        'hft_safe': True
    }), 200


@app.route('/api/analyze', methods=['POST'])
@require_license
def analyze_ticker():
    """
    Main endpoint: Analyze a ticker for swing trading
    
    Request Body:
        {
            "ticker": "AAPL",
            "use_ai": true  // Optional, default: true
        }
    
    Response:
        {
            "ticker": "AAPL",
            "score": 78,
            "verdict": "STRONG",
            "breakdown": {...},
            "ai_summary": "...",
            "current_price": 178.42,
            "news": [...],
            "timestamp": "..."
        }
    """
    try:
        data = request.get_json()
        ticker = data.get('ticker', '').strip()
        use_ai = data.get('use_ai', True)
        
        # Validate ticker
        is_valid, cleaned_ticker = validate_ticker(ticker)
        if not is_valid:
            return jsonify({
                'error': 'Invalid ticker symbol. Please enter 1-5 letters (e.g., AAPL, TSLA)'
            }), 400
        
        # Check if engines are initialized
        if not scorer:
            return jsonify({
                'error': 'Swing Score Engine not available'
            }), 500
        
        print(f"\n{'='*80}")
        print(f"ANALYZING: {cleaned_ticker}")
        print(f"{'='*80}")
        print(f"Use AI: {use_ai}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        
        # Execute in parallel for speed
        with ThreadPoolExecutor(max_workers=3) as executor:
            # Technical score (REST API only - no WebSocket)
            future_technical = executor.submit(scorer.calculate_score, cleaned_ticker)
            
            # Wait for technical results first
            technical_result = future_technical.result()
            
            if 'error' in technical_result:
                return jsonify(technical_result), 500
            
            # Always fetch news
            future_news = None
            if market_analyst:
                future_news = executor.submit(market_analyst.fetch_news, cleaned_ticker)
            
            # Get news articles
            news_articles = []
            if future_news:
                try:
                    news_articles = future_news.result()
                except Exception as e:
                    print(f"[!]  News fetch failed: {e}")
                    news_articles = []
        
        # STEP 2: Holistic AI Analysis (if enabled)
        if use_ai and market_analyst:
            try:
                # Pass full context: score + breakdown + news
                ai_result = market_analyst.analyze_context(
                    cleaned_ticker,
                    technical_result['score'],
                    technical_result['breakdown'],
                    news_articles
                )
            except Exception as e:
                print(f"[!]  AI analysis failed: {e}")
                ai_result = {
                    'sentiment_score': 0,
                    'analysis': 'AI analysis unavailable',
                    'key_risk': 'Analysis error'
                }
        else:
            ai_result = {
                'sentiment_score': 0,
                'analysis': 'AI analysis disabled',
                'key_risk': 'N/A'
            }
        
        # Calculate AI adjustment (0-10 points)
        ai_sentiment_score = ai_result.get('sentiment_score', 0)
        ai_points = ((ai_sentiment_score + 10) / 20) * 10
        ai_points = max(0, min(10, int(round(ai_points))))
        
        # Add AI analysis to breakdown
        technical_result['breakdown']['ai_sentiment'] = ai_points
        technical_result['breakdown']['details']['ai_sentiment'] = {
            'ai_score': f'{ai_sentiment_score:+d}/10',
            'points': f'{ai_points}/10',
            'analysis': ai_result.get('analysis', 'N/A'),
            'key_risk': ai_result.get('key_risk', 'N/A')
        }
        
        # Adjust final score with AI
        final_score = technical_result['score'] + ai_points
        final_score = min(100, final_score)
        
        # Get verdict using same logic as scoring engine
        kill_switch = 'reason' in technical_result
        if kill_switch:
            verdict = "AVOID (Rel. Weakness)"
        elif final_score >= 80:
            verdict = "STRONG BUY"
        elif final_score >= 60:
            verdict = "BUY"
        elif final_score >= 40:
            verdict = "HOLD"
        elif final_score >= 20:
            verdict = "AVOID"
        else:
            verdict = "STRONG SELL"
        
        # Build response
        response = {
            'ticker': cleaned_ticker,
            'score': final_score,
            'verdict': verdict,
            'breakdown': technical_result['breakdown'],
            'ai_summary': ai_result.get('analysis', 'No analysis available'),
            'current_price': technical_result['current_price'],
            'news': news_articles[:3] if news_articles else [],  # Top 3 articles
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'trade_setup': technical_result.get('trade_setup', {})  # Beginner-friendly entry/exit
        }
        
        # Add warning if kill switch triggered
        if 'reason' in technical_result:
            response['warning'] = technical_result['reason']
        
        print(f"\n[OK] Analysis complete:")
        print(f"   Score: {final_score}/100")
        print(f"   Verdict: {verdict}")
        print(f"{'='*80}\n")
        
        return jsonify(response), 200
        
    except Exception as e:
        print(f"\n[ERROR] Error: {e}\n")
        return jsonify({
            'error': 'Could not analyze ticker. Please try again.'
        }), 500


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration (safe summary)"""
    return jsonify({
        'status': 'operational',
        'config': config.get_summary(),
        'engines': {
            'scorer': 'available' if scorer else 'unavailable',
            'market_analyst': 'available' if market_analyst else 'unavailable'
        }
    }), 200


@app.route('/api/license/info', methods=['GET'])
@require_license
def license_info():
    """
    Get information about the authenticated license
    
    Returns license details including tier, usage, etc.
    """
    try:
        license_data = get_license_info(request)
        
        if not license_data:
            return jsonify({
                'error': 'License information not available'
            }), 500
        
        return jsonify({
            'status': 'success',
            'license': license_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': f'Failed to retrieve license info: {str(e)}'
        }), 500


@app.route('/create-checkout-session', methods=['POST'])
def create_checkout():
    """
    Create Stripe Checkout Session
    
    POST body:
    {
        "email": "customer@example.com",  // optional
        "tier": "pro"  // optional, defaults to 'pro'
    }
    
    Returns:
    {
        "session_id": "cs_...",
        "url": "https://checkout.stripe.com/..."
    }
    """
    try:
        data = request.get_json() or {}
        
        # Get customer email and tier from request
        customer_email = data.get('email')
        tier = data.get('tier', 'pro')
        
        # Create success and cancel URLs
        base_url = request.host_url.rstrip('/')
        success_url = f"{base_url}/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{base_url}/cancel"
        
        # Create checkout session
        result = create_checkout_session(
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=customer_email,
            tier=tier
        )
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    """
    Stripe Webhook Handler - PRODUCTION READY
    
    Automatically processes payments and creates license keys.
    
    Handles:
    - checkout.session.completed → Create license + send email
    - customer.subscription.deleted → Revoke license
    """
    try:
        # Get raw payload and signature
        payload = request.data
        signature = request.headers.get('Stripe-Signature')
        
        # Verify webhook signature
        event = verify_webhook_signature(payload, signature)
        
        if not event:
            return jsonify({'error': 'Invalid signature'}), 400
        
        # Log event
        print("\n" + "="*80)
        print(f"[STRIPE] STRIPE WEBHOOK: {event['type']}")
        print("="*80)
        
        # Handle different event types
        event_type = event['type']
        
        if event_type == 'checkout.session.completed':
            # Payment successful - create license
            session = event['data']['object']
            result = handle_checkout_completed(session)
            
            if 'error' not in result:
                # Send license key via email
                send_license_email(
                    email=result['email'],
                    license_key=result['license_key'],
                    tier=result['tier']
                )
                print(f"[OK] License created and emailed: {result['license_key']}")
            else:
                print(f"[ERROR] Error creating license: {result['error']}")
        
        elif event_type == 'customer.subscription.deleted':
            # Subscription cancelled - revoke license
            subscription = event['data']['object']
            result = handle_subscription_deleted(subscription)
            
            if 'revoked' in result:
                print(f"[OK] License revoked: {result['revoked']}")
            else:
                print(f"[!]  {result.get('message', 'Unknown result')}")
        
        elif event_type == 'invoice.payment_failed':
            # Payment failed - notify customer
            print("[!]  Payment failed - customer should be notified")
            # TODO: Send email notification
        
        print("="*80 + "\n")
        
        # Return success
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        print(f"[ERROR] Webhook error: {e}")
        return jsonify({'error': str(e)}), 400


@app.route('/success')
def payment_success():
    """
    Payment Success Page
    
    Displays license key to customer immediately after purchase.
    """
    try:
        # Get session ID from URL (optional now)
        session_id = request.args.get('session_id')
        email_param = request.args.get('email')
        
        customer_email = None
        
        # Try to get email from session ID
        if session_id:
            session_details = get_session_details(session_id)
            if 'error' not in session_details:
                customer_email = session_details.get('customer_email')
        
        # Or use email parameter directly
        if not customer_email and email_param:
            customer_email = email_param
        
        # Find license in database
        license = None
        if customer_email:
            license = License.query.filter_by(email=customer_email).order_by(License.created_at.desc()).first()
        
        # If no license found, show lookup form
        if not license:
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Find Your License - Swing Trading Copilot</title>
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 20px; }
                    .container { background: white; border-radius: 20px; padding: 50px; max-width: 500px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); text-align: center; }
                    h1 { color: #1f2937; }
                    input[type="email"] { width: 100%; padding: 15px; font-size: 16px; border: 2px solid #e5e7eb; border-radius: 10px; box-sizing: border-box; margin: 20px 0; }
                    .button { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 40px; border: none; border-radius: 10px; font-size: 16px; cursor: pointer; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Find Your License Key</h1>
                    <p>Enter the email you used for payment:</p>
                    <form method="GET" action="/success">
                        <input type="email" name="email" placeholder="your@email.com" required>
                        <br><button type="submit" class="button">Find My License</button>
                    </form>
                </div>
            </body>
            </html>
            """
            return html
        
        # Display success page with license key
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Payment Successful - Swing Trading Copilot</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    margin: 0;
                    padding: 20px;
                }}
                .container {{
                    background: white;
                    border-radius: 20px;
                    padding: 50px;
                    max-width: 600px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    text-align: center;
                }}
                h1 {{
                    color: #10b981;
                    font-size: 36px;
                    margin-bottom: 20px;
                }}
                .success-icon {{
                    font-size: 72px;
                    margin-bottom: 20px;
                }}
                .license-key {{
                    background: #f3f4f6;
                    border: 2px solid #10b981;
                    border-radius: 12px;
                    padding: 20px;
                    font-family: 'Courier New', monospace;
                    font-size: 24px;
                    font-weight: bold;
                    color: #1f2937;
                    margin: 30px 0;
                    letter-spacing: 2px;
                }}
                .instructions {{
                    background: #f9fafb;
                    border-left: 4px solid #3b82f6;
                    padding: 20px;
                    margin: 30px 0;
                    text-align: left;
                }}
                .instructions h3 {{
                    color: #3b82f6;
                    margin-top: 0;
                }}
                .instructions ol {{
                    line-height: 1.8;
                    color: #4b5563;
                }}
                .button {{
                    display: inline-block;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 15px 40px;
                    border-radius: 12px;
                    text-decoration: none;
                    font-weight: 600;
                    margin-top: 20px;
                    transition: transform 0.3s ease;
                }}
                .button:hover {{
                    transform: translateY(-2px);
                }}
                .email-note {{
                    color: #6b7280;
                    font-size: 14px;
                    margin-top: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success-icon">[OK]</div>
                <h1>Payment Successful!</h1>
                <p>Thank you for subscribing to Swing Trading Copilot PRO!</p>
                
                <div class="license-key">
                    {license.key}
                </div>
                
                <div class="instructions">
                    <h3>[START] Get Started in 3 Steps:</h3>
                    <ol>
                        <li>Install the Chrome Extension (if you haven't already)</li>
                        <li>Open the extension and enter your license key above</li>
                        <li>Start analyzing stocks with AI-powered insights!</li>
                    </ol>
                </div>
                
                <a href="https://chrome.google.com/webstore" class="button">
                    Install Chrome Extension →
                </a>
                
                <div class="email-note">
                    [EMAIL] A copy of your license key has been sent to:<br>
                    <strong>{customer_email}</strong>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
        
    except Exception as e:
        return f"Error: {str(e)}", 500


@app.route('/cancel')
def payment_cancel():
    """
    Payment Cancelled Page
    """
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Payment Cancelled - Swing Trading Copilot</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
                padding: 20px;
            }
            .container {
                background: white;
                border-radius: 20px;
                padding: 50px;
                max-width: 600px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                text-align: center;
            }
            h1 {
                color: #ef4444;
                font-size: 36px;
                margin-bottom: 20px;
            }
            .icon {
                font-size: 72px;
                margin-bottom: 20px;
            }
            p {
                color: #6b7280;
                line-height: 1.6;
                margin-bottom: 30px;
            }
            .button {
                display: inline-block;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 15px 40px;
                border-radius: 12px;
                text-decoration: none;
                font-weight: 600;
                transition: transform 0.3s ease;
            }
            .button:hover {
                transform: translateY(-2px);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="icon">[ERROR]</div>
            <h1>Payment Cancelled</h1>
            <p>Your payment was cancelled. No charges were made to your account.</p>
            <p>If you have any questions, please contact us at support@swingcopilot.com</p>
            <a href="/" class="button">Try Again</a>
        </div>
    </body>
    </html>
    """
    return html


@app.route('/admin/stats', methods=['GET'])
def admin_stats():
    """
    Admin endpoint - License statistics
    
    WARNING: In production, protect this with admin authentication!
    """
    try:
        stats = get_license_stats()
        return jsonify({
            'status': 'success',
            'stats': stats
        }), 200
    except Exception as e:
        return jsonify({
            'error': f'Failed to retrieve stats: {str(e)}'
        }), 500


@app.route('/admin/create-test-key', methods=['POST'])
def create_test_key():
    """Create a test license key (for development only)"""
    try:
        test_key = 'PRO-TEST00-KEY123'
        existing = License.query.filter_by(key=test_key).first()
        
        if existing:
            return jsonify({
                'status': 'exists',
                'key': test_key,
                'message': 'Test key already exists'
            }), 200
        
        test_license = License(
            key=test_key,
            email='test@swingtradingcopilot.com',
            tier='pro',
            status='active'
        )
        db.session.add(test_license)
        db.session.commit()
        
        return jsonify({
            'status': 'created',
            'key': test_key,
            'message': 'Test key created successfully'
        }), 201
    except Exception as e:
        return jsonify({
            'error': f'Failed to create test key: {str(e)}'
        }), 500


if __name__ == '__main__':
    print("\n" + "="*80)
    print("[START] SWING TRADING COPILOT BACKEND")
    print("="*80)
    print("[API] Starting Flask server on http://localhost:5000")
    print("[!]  REST API ONLY - No WebSocket (HFT bot safe)")
    print("="*80 + "\n")
    
    app.run(debug=True, port=5000)

