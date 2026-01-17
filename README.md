# Swing Trading Copilot

AI-powered swing trading analysis Chrome extension with license key system.

## Quick Deploy to Railway

### 1. Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/SwingTradingCopilot.git
git push -u origin main
```

### 2. Deploy on Railway
1. Go to [railway.app](https://railway.app)
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository
4. Add environment variables (see below)
5. Deploy!

### 3. Environment Variables (Railway)
Add these in Railway Dashboard → Variables:

```
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_... (get after step 4)
STRIPE_PRODUCT_ID=prod_...
STRIPE_PRICE_ID=price_...
ALPACA_API_KEY=...
ALPACA_SECRET_KEY=...
POLYGON_API_KEY=...
OPENAI_API_KEY=...
```

### 4. Setup Stripe Webhook
1. Go to Stripe Dashboard → Developers → Webhooks
2. Add endpoint: `https://YOUR-APP.railway.app/webhook`
3. Select events: `checkout.session.completed`, `customer.subscription.deleted`
4. Copy the signing secret (`whsec_...`)
5. Add `STRIPE_WEBHOOK_SECRET` to Railway variables

### 5. Update Extension
Change `API_URL` in `extension/popup.js` to your Railway URL:
```javascript
const API_URL = 'https://YOUR-APP.railway.app/api/analyze';
```

## Local Development
```bash
pip install -r requirements.txt
python app_new.py
```

## Files
- `app_new.py` - Flask API server
- `database.py` - License management
- `stripe_integration.py` - Payment processing
- `swing_score_engine.py` - Trading analysis
- `market_analyst.py` - AI sentiment
- `extension/` - Chrome extension files
