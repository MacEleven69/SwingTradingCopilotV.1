/**
 * Swing Trading Copilot - Frontend Logic
 * Production-ready with error handling, animations, and license authentication
 */

const API_URL = 'https://swingtradingcopilotv1-production.up.railway.app/api/analyze';

// ═══════════════════════════════════════════════════════════════════════════
// MARKET WATCHLIST DATA
// ═══════════════════════════════════════════════════════════════════════════

const stockCategories = [
    { category: "The Titans", tickers: ["MSFT", "AMZN", "META", "TSLA", "GOOGL", "AAPL", "NVDA", "MAGS"] },
    { category: "The Chip War", tickers: ["AMD", "MU", "SMCI", "ASML", "AVGO", "TSM", "INTC", "ARM", "SOXL"] },
    { category: "Crypto & Blockchain", tickers: ["MSTR", "COIN", "CLSK", "MARA", "IREN"] },
    { category: "The East (China)", tickers: ["BABA", "PDD", "JD", "BIDU", "NIO", "BYDDY", "FXI"] },
    { category: "Space & Defense", tickers: ["RKLB", "ASTS", "LUNR", "PL", "KTOS"] },
    { category: "Nuclear & Energy", tickers: ["SMR", "BWXT", "LEU", "BE", "AMRC"] },
    { category: "AI & Robotics", tickers: ["SOUN", "PATH", "SYM", "BBAI", "ROBO"] },
    { category: "Quantum Computing", tickers: ["IONQ", "QBTS", "QUBT", "RGTI"] },
    { category: "Fintech", tickers: ["NU", "DLO", "RELY"] }
];

// Dummy price data for visual display (replace with real API later)
const basePrices = {
    MSFT: 378, AMZN: 178, META: 485, TSLA: 243, GOOGL: 141, AAPL: 190, NVDA: 875, MAGS: 52,
    AMD: 126, MU: 84, SMCI: 893, ASML: 726, AVGO: 1246, TSM: 142, INTC: 45, ARM: 128, SOXL: 43,
    MSTR: 1425, COIN: 186, CLSK: 12, MARA: 19, IREN: 9,
    BABA: 78, PDD: 125, JD: 29, BIDU: 103, NIO: 6, BYDDY: 58, FXI: 29,
    RKLB: 6, ASTS: 18, LUNR: 13, PL: 3, KTOS: 22,
    SMR: 25, BWXT: 99, LEU: 78, BE: 19, AMRC: 8,
    SOUN: 5, PATH: 15, SYM: 28, BBAI: 3, ROBO: 53,
    IONQ: 12, QBTS: 7, QUBT: 9, RGTI: 2,
    NU: 13, DLO: 15, RELY: 11
};

// DOM Elements - Auth Screen
const authScreen = document.getElementById('authScreen');
const mainApp = document.getElementById('mainApp');
const licenseKeyInput = document.getElementById('licenseKeyInput');
const activateBtn = document.getElementById('activateBtn');
const authError = document.getElementById('authError');

// DOM Elements - Main App
const tickerInput = document.getElementById('tickerInput');
const analyzeBtn = document.getElementById('analyzeBtn');
const errorMessage = document.getElementById('errorMessage');
const resultsSection = document.getElementById('results');
const skeletonLoader = document.getElementById('skeleton');
const status = document.getElementById('status');

// Result elements
const tickerSymbol = document.getElementById('tickerSymbol');
const currentPrice = document.getElementById('currentPrice');
const scoreNumber = document.getElementById('scoreNumber');
const gaugeFill = document.getElementById('gaugeFill');
const verdictBadge = document.getElementById('verdict-badge');
const trend = document.getElementById('trend');
const momentum = document.getElementById('momentum');
const volatility = document.getElementById('volatility');
const volume = document.getElementById('volume');
const supportResistance = document.getElementById('supportResistance');
const rsi = document.getElementById('rsi');
const aiSummary = document.getElementById('aiSummary');
const biggestRisk = document.getElementById('biggestRisk');
const biggestStrength = document.getElementById('biggestStrength');
const newsList = document.getElementById('newsList');

// Trade Setup Card elements are fetched dynamically in displayTradeSetup()

// State
let isLoading = false;
let licenseKey = null;
let currentTab = 'analyzer';

// Initialize app - check for license key
initializeApp();

// ═══════════════════════════════════════════════════════════════════════════
// TAB NAVIGATION
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Initialize tab navigation
 */
function initializeTabs() {
    const tabAnalyzer = document.getElementById('tabAnalyzer');
    const tabMarket = document.getElementById('tabMarket');
    
    if (tabAnalyzer) {
        tabAnalyzer.addEventListener('click', () => switchTab('analyzer'));
    }
    if (tabMarket) {
        tabMarket.addEventListener('click', () => switchTab('market'));
    }
}

/**
 * Switch between tabs
 */
function switchTab(tabName) {
    currentTab = tabName;
    
    // Update tab buttons
    const tabBtns = document.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.tab === tabName) {
            btn.classList.add('active');
        }
    });
    
    // Update tab content
    const analyzerView = document.getElementById('analyzer-view');
    const marketView = document.getElementById('market-view');
    
    if (analyzerView && marketView) {
        if (tabName === 'analyzer') {
            analyzerView.style.display = 'block';
            analyzerView.classList.add('active');
            marketView.style.display = 'none';
            marketView.classList.remove('active');
        } else {
            analyzerView.style.display = 'none';
            analyzerView.classList.remove('active');
            marketView.style.display = 'block';
            marketView.classList.add('active');
            
            // Render market on first view
            renderMarketView();
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// MARKET VIEW RENDERING
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Generate dummy stock data
 */
function generateDummyData(ticker) {
    const basePrice = basePrices[ticker] || (50 + Math.random() * 200);
    const changePercent = (Math.random() - 0.5) * 10; // -5% to +5%
    const price = basePrice * (1 + changePercent / 100);
    
    return {
        ticker,
        price: price.toFixed(2),
        changePercent: changePercent.toFixed(2)
    };
}

/**
 * Render the market watchlist view
 */
function renderMarketView() {
    const container = document.getElementById('marketCategories');
    if (!container) return;
    
    // Check if already rendered
    if (container.dataset.rendered === 'true') return;
    
    container.innerHTML = '';
    container.dataset.rendered = 'true';
    
    stockCategories.forEach(category => {
        const categoryEl = document.createElement('div');
        categoryEl.className = 'market-category';
        
        // Category title
        const titleEl = document.createElement('h3');
        titleEl.className = 'category-title';
        titleEl.textContent = category.category;
        categoryEl.appendChild(titleEl);
        
        // Stock row (horizontal scroll)
        const rowEl = document.createElement('div');
        rowEl.className = 'stock-row';
        
        category.tickers.forEach((ticker, index) => {
            const data = generateDummyData(ticker);
            const isPositive = parseFloat(data.changePercent) >= 0;
            
            const cardEl = document.createElement('div');
            cardEl.className = 'stock-card' + (index === 0 ? ' featured' : '');
            cardEl.innerHTML = `
                <div class="stock-ticker">${data.ticker}</div>
                <div class="stock-price">$${data.price}</div>
                <div class="stock-change ${isPositive ? 'positive' : 'negative'}">
                    ${isPositive ? '+' : ''}${data.changePercent}%
                </div>
            `;
            
            // Click handler - analyze this stock
            cardEl.addEventListener('click', () => {
                analyzeFromMarket(data.ticker);
            });
            
            rowEl.appendChild(cardEl);
        });
        
        categoryEl.appendChild(rowEl);
        container.appendChild(categoryEl);
    });
}

/**
 * Handle click on market stock card
 * Switches to analyzer tab and triggers analysis
 */
function analyzeFromMarket(ticker) {
    // Switch to analyzer tab
    switchTab('analyzer');
    
    // Fill in the ticker input
    const tickerInputEl = document.getElementById('tickerInput');
    if (tickerInputEl) {
        tickerInputEl.value = ticker;
    }
    
    // Trigger analysis
    setTimeout(() => {
        analyzeTicker();
    }, 100);
}

/**
 * Initialize application - check for license and show appropriate UI
 */
async function initializeApp() {
    try {
        // Check for stored license key
        const result = await chrome.storage.sync.get(['licenseKey']);
        
        if (result.licenseKey) {
            licenseKey = result.licenseKey;
            showMainApp();
        } else {
            showAuthScreen();
        }
    } catch (error) {
        console.error('Initialization error:', error);
        showAuthScreen();
    }
}

/**
 * Show auth screen (license entry)
 */
function showAuthScreen() {
    authScreen.style.display = 'flex';
    mainApp.style.display = 'none';
    licenseKeyInput.focus();
}

/**
 * Show main application
 */
function showMainApp() {
    authScreen.style.display = 'none';
    mainApp.style.display = 'block';
    tickerInput.focus();
    
    // Initialize tab navigation
    initializeTabs();
}

/**
 * Activate license key
 */
async function activateLicense() {
    const key = licenseKeyInput.value.trim().toUpperCase();
    
    // Validate format
    if (!validateLicenseKey(key)) {
        showAuthError('Invalid license key format. Expected: PRO-XXXXXX-YYYYYY');
        return;
    }
    
    // Show loading state
    activateBtn.classList.add('loading');
    activateBtn.disabled = true;
    clearAuthError();
    
    try {
        // Test the license key with API
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-License-Key': key
            },
            body: JSON.stringify({ 
                ticker: 'AAPL',  // Test with AAPL
                use_ai: false    // Don't use AI for validation
            })
        });
        
        if (response.status === 401) {
            // Invalid license
            const data = await response.json();
            throw new Error(data.message || 'Invalid license key');
        }
        
        if (!response.ok) {
            // Other error (but license is valid)
            console.log('License valid but API error:', response.status);
        }
        
        // License is valid! Save it
        await chrome.storage.sync.set({ licenseKey: key });
        licenseKey = key;
        
        // Show success feedback
        activateBtn.classList.add('success');
        activateBtn.querySelector('.auth-btn-text').textContent = '✓ Activated!';
        
        // Transition to main app
        setTimeout(() => {
            showMainApp();
            activateBtn.classList.remove('success', 'loading');
            activateBtn.disabled = false;
            activateBtn.querySelector('.auth-btn-text').textContent = 'Activate License';
        }, 1000);
        
    } catch (error) {
        console.error('Activation error:', error);
        showAuthError(error.message || 'Could not activate license. Please try again.');
        activateBtn.classList.remove('loading');
        activateBtn.disabled = false;
    }
}

/**
 * Validate license key format
 */
function validateLicenseKey(key) {
    // Format: PRO-XXXXXX-YYYYYY or ENT-XXXXXX-YYYYYY or FREE-XXXXXX-YYYYYY
    const regex = /^(PRO|ENT|FREE)-[A-F0-9]{6}-[A-F0-9]{6}$/;
    return regex.test(key);
}

/**
 * Show auth error message
 */
function showAuthError(message) {
    authError.textContent = message;
    authError.style.display = 'block';
    licenseKeyInput.classList.add('error');
}

/**
 * Clear auth error message
 */
function clearAuthError() {
    authError.style.display = 'none';
    licenseKeyInput.classList.remove('error');
}

// Event Listeners - Auth Screen
activateBtn.addEventListener('click', activateLicense);
licenseKeyInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        activateLicense();
    }
});
licenseKeyInput.addEventListener('input', clearAuthError);

// Event Listeners - Main App
analyzeBtn.addEventListener('click', analyzeTicker);
tickerInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !isLoading) {
        analyzeTicker();
    }
});

tickerInput.addEventListener('input', () => {
    clearError();
});

/**
 * Main analysis function
 */
async function analyzeTicker() {
    const ticker = tickerInput.value.trim().toUpperCase();
    
    // Client-side validation
    if (!validateTicker(ticker)) {
        showError('Please enter a valid ticker symbol (e.g., AAPL, TSLA)');
        return;
    }
    
    // Check for license key
    if (!licenseKey) {
        showError('License key missing. Please re-enter your license key.');
        setTimeout(() => showAuthScreen(), 2000);
        return;
    }
    
    // Update UI state
    setLoadingState(true);
    clearError();
    hideResults();
    showSkeleton();
    
    try {
        // Call API with license key
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-License-Key': licenseKey  // Include license key
            },
            body: JSON.stringify({ 
                ticker: ticker,
                use_ai: true  // Enable AI analysis
            })
        });
        
        const data = await response.json();
        
        // Handle unauthorized (invalid/revoked license)
        if (response.status === 401) {
            // Clear invalid license
            await chrome.storage.sync.remove('licenseKey');
            licenseKey = null;
            
            // Show error and return to auth screen
            showError('License key is invalid or has been revoked. Please re-enter.');
            hideSkeleton();
            
            setTimeout(() => {
                showAuthScreen();
                licenseKeyInput.value = '';
            }, 2000);
            
            return;
        }
        
        if (!response.ok) {
            throw new Error(data.error || 'Analysis failed');
        }
        
        console.log('📊 API Response:', data);  // Debug log
        
        // Display results
        displayResults(data);
        
    } catch (error) {
        console.error('Analysis error:', error);
        showError(error.message || 'Could not analyze ticker. Please try again.');
        hideSkeleton();
    } finally {
        setLoadingState(false);
    }
}

/**
 * Validate ticker format
 */
function validateTicker(ticker) {
    // Must be 1-5 uppercase letters
    return /^[A-Z]{1,5}$/.test(ticker);
}

/**
 * Update verdict badge with appropriate styling
 */
function updateVerdictBadge(verdict) {
    if (!verdict) return;
    
    // Set text
    verdictBadge.textContent = verdict;
    
    // Remove all verdict classes
    verdictBadge.className = 'verdict-badge';
    
    // Add appropriate class based on verdict
    const verdictLower = verdict.toLowerCase();
    
    if (verdictLower.includes('strong buy')) {
        verdictBadge.classList.add('verdict-strong-buy');
    } else if (verdictLower.includes('buy')) {
        verdictBadge.classList.add('verdict-buy');
    } else if (verdictLower.includes('hold')) {
        verdictBadge.classList.add('verdict-hold');
    } else if (verdictLower.includes('avoid') || verdictLower.includes('weakness')) {
        verdictBadge.classList.add('verdict-avoid');
    } else if (verdictLower.includes('strong sell') || verdictLower.includes('sell')) {
        verdictBadge.classList.add('verdict-strong-sell');
    }
}

/**
 * Display analysis results with animations
 */
function displayResults(data) {
    hideSkeleton();
    
    // Debug: Log the full API response
    console.log('📊 API Response:', data);
    console.log('🤖 AI Summary:', data.ai_summary);
    console.log('📋 Breakdown Details:', data.breakdown?.details);
    
    // Update ticker and price
    tickerSymbol.textContent = data.ticker;
    currentPrice.textContent = `$${data.current_price.toFixed(2)}`;
    
    // Animate score gauge
    animateScore(data.score);
    
    // Update verdict badge
    updateVerdictBadge(data.verdict);
    
    // Update breakdown - match actual API response structure
    const breakdown = data.breakdown || {};
    
    // Display score components (out of max points)
    trend.textContent = `${breakdown.technicals || 0}/40`;
    momentum.textContent = `${breakdown.market_regime || 0}/30`;
    volatility.textContent = `${breakdown.relative_strength || 0}/20`;
    volume.textContent = `${breakdown.ai_sentiment || 0}/10`;
    supportResistance.textContent = data.verdict || 'N/A';
    rsi.textContent = `${data.score}/100`;
    
    // Update analyst insights
    const aiSummaryText = data.ai_summary || 'No AI analysis available';
    const details = breakdown.details || {};
    const aiDetails = details.ai_sentiment || {};
    
    // AI SUMMARY PARAGRAPH: Main analysis
    if (aiSummaryText && aiSummaryText !== 'AI analysis disabled' && aiSummaryText !== 'N/A' && aiSummaryText !== 'Sentiment analysis failed') {
        aiSummary.textContent = aiSummaryText;
        aiSummary.style.color = 'var(--accent-success)';
    } else {
        aiSummary.textContent = 'Analyzing market sentiment... (AI sentiment analysis in progress)';
        aiSummary.style.color = 'var(--text-secondary)';
    }
    
    // KEY STRENGTH: Extract from AI details or use fallback
    if (aiDetails.analysis && aiDetails.analysis !== 'N/A' && aiDetails.analysis !== 'AI analysis unavailable') {
        biggestStrength.textContent = aiDetails.analysis;
    } else if (details.technicals && details.technicals.rsi) {
        // Fallback: Show technical summary
        biggestStrength.textContent = `Technical: ${details.technicals.rsi}`;
    } else {
        biggestStrength.textContent = 'Positive market conditions detected';
    }
    
    // KEY RISK: Show from AI sentiment details, then warning, then relative strength
    if (aiDetails.key_risk && aiDetails.key_risk !== 'N/A' && aiDetails.key_risk !== 'Analysis error') {
        biggestRisk.textContent = aiDetails.key_risk;
    } else if (data.warning) {
        biggestRisk.textContent = `⚠️ ${data.warning}`;
    } else if (details.relative_strength && details.relative_strength.status) {
        biggestRisk.textContent = `Relative Strength: ${details.relative_strength.status}`;
    } else {
        biggestRisk.textContent = 'Monitor market conditions';
    }
    
    // Update news
    displayNews(data.news);
    
    // Update Trade Setup Card (Beginner Friendly)
    displayTradeSetup(data);
    
    // Show results with fade-in
    resultsSection.style.display = 'block';
    resultsSection.style.opacity = '0';
    setTimeout(() => {
        resultsSection.style.transition = 'opacity 0.3s ease';
        resultsSection.style.opacity = '1';
    }, 10);
    
    // Update status
    updateStatus('Analysis complete', 'success');
}

/**
 * Display Trade Setup Card with dual targets and smart colors
 */
function displayTradeSetup(data) {
    // Check if Trade Setup Card elements exist
    const entryZoneEl = document.getElementById('entryZone');
    const stopPriceEl = document.getElementById('stopPrice');
    const entryRowEl = document.getElementById('entryRow');
    const setupStatusDotEl = document.getElementById('setupStatusDot');
    const setupStatusTextEl = document.getElementById('setupStatusText');
    
    // Dual target elements
    const targetSafePriceEl = document.getElementById('targetSafePrice');
    const targetSafePctEl = document.getElementById('targetSafePct');
    const targetAggroPriceEl = document.getElementById('targetAggroPrice');
    const targetAggroPctEl = document.getElementById('targetAggroPct');
    const probSafeEl = document.getElementById('probSafe');
    const probAggroEl = document.getElementById('probAggro');
    const targetAggroEl = document.getElementById('targetAggro');
    const targetRecommendationEl = document.getElementById('targetRecommendation');
    
    // If key elements don't exist, skip
    if (!entryZoneEl || !stopPriceEl) {
        console.log('Trade Setup Card elements not found - skipping');
        return;
    }
    
    const tradeSetup = data.trade_setup || {};
    const price = data.current_price;
    
    // Get values from API
    const buyMin = tradeSetup.buy_min || 0;
    const buyMax = tradeSetup.buy_max || 0;
    const sellStop = tradeSetup.sell_stop || 0;
    
    // Dual targets
    const targetSafe = tradeSetup.target_safe || price * 1.04;
    const targetSafePct = tradeSetup.target_safe_pct || 4.0;
    const targetAggro = tradeSetup.target_aggro || price * 1.10;
    const targetAggroPct = tradeSetup.target_aggro_pct || 10.0;
    const probSafe = tradeSetup.prob_safe || 75;
    const probAggro = tradeSetup.prob_aggro || 40;
    const volatilitySupported = tradeSetup.volatility_supported !== false;
    
    // Display entry zone
    if (buyMin && buyMax) {
        entryZoneEl.textContent = `$${buyMin.toFixed(2)} - $${buyMax.toFixed(2)}`;
    } else {
        entryZoneEl.textContent = 'Calculating...';
    }
    
    // Display stop loss
    if (sellStop) {
        stopPriceEl.textContent = `$${sellStop.toFixed(2)}`;
    } else {
        stopPriceEl.textContent = '--';
    }
    
    // Display dual targets (if elements exist)
    if (targetSafePriceEl) {
        targetSafePriceEl.textContent = `$${targetSafe.toFixed(2)}`;
    }
    if (targetSafePctEl) {
        targetSafePctEl.textContent = `+${targetSafePct.toFixed(1)}%`;
    }
    if (targetAggroPriceEl) {
        targetAggroPriceEl.textContent = `$${targetAggro.toFixed(2)}`;
    }
    if (targetAggroPctEl) {
        targetAggroPctEl.textContent = `+${targetAggroPct.toFixed(1)}%`;
    }
    
    // Display probabilities
    if (probSafeEl) {
        probSafeEl.textContent = `~${probSafe}%`;
    }
    if (probAggroEl) {
        probAggroEl.textContent = `~${probAggro}%`;
        // Dim aggro target if volatility doesn't support it
        if (targetAggroEl) {
            if (!volatilitySupported || probAggro < 30) {
                targetAggroEl.classList.add('low-probability');
            } else {
                targetAggroEl.classList.remove('low-probability');
            }
        }
    }
    
    // Update recommendation
    if (targetRecommendationEl) {
        if (probSafe >= 70) {
            targetRecommendationEl.innerHTML = `<span class="rec-icon">💡</span><span class="rec-text">Recommended: Take the <strong>Safe</strong> target for consistent gains</span>`;
        } else {
            targetRecommendationEl.innerHTML = `<span class="rec-icon">⚠️</span><span class="rec-text">Caution: Market conditions are uncertain</span>`;
        }
    }
    
    // Smart Color Logic for Entry Row
    if (entryRowEl && setupStatusDotEl && setupStatusTextEl) {
        entryRowEl.classList.remove('in-zone', 'wait-for-dip', 'below-zone');
        setupStatusDotEl.classList.remove('good-to-buy', 'wait', 'caution');
        
        if (price && buyMin && buyMax) {
            if (price >= buyMin && price <= buyMax) {
                entryRowEl.classList.add('in-zone');
                setupStatusDotEl.classList.add('good-to-buy');
                setupStatusTextEl.textContent = '✅ Good to buy now - price is in the sweet spot!';
            } else if (price > buyMax) {
                const pctAbove = ((price - buyMax) / buyMax * 100).toFixed(1);
                entryRowEl.classList.add('wait-for-dip');
                setupStatusDotEl.classList.add('wait');
                setupStatusTextEl.textContent = `⏳ Wait for a dip - price is ${pctAbove}% above ideal range`;
            } else {
                entryRowEl.classList.add('below-zone');
                setupStatusDotEl.classList.add('caution');
                setupStatusTextEl.textContent = '⚠️ Price below target zone - verify trend first';
            }
        } else {
            setupStatusTextEl.textContent = 'Analyzing trade setup...';
        }
    }
}

/**
 * Animate score gauge from 0 to target
 */
function animateScore(targetScore) {
    const duration = 1500; // 1.5 seconds
    const steps = 60;
    const increment = targetScore / steps;
    const stepDuration = duration / steps;
    
    let currentScore = 0;
    
    const interval = setInterval(() => {
        currentScore += increment;
        
        if (currentScore >= targetScore) {
            currentScore = targetScore;
            clearInterval(interval);
        }
        
        updateGauge(Math.round(currentScore));
    }, stepDuration);
}

/**
 * Update gauge display and color
 */
function updateGauge(score) {
    scoreNumber.textContent = score;
    
    // Calculate stroke-dasharray for SVG arc
    // Full arc length ≈ 251.2 (π * 80)
    const arcLength = 251.2;
    const fillLength = (score / 100) * arcLength;
    gaugeFill.setAttribute('stroke-dasharray', `${fillLength} ${arcLength}`);
    
    // Update color based on score
    let color;
    if (score < 40) {
        color = '#ef4444'; // Red
    } else if (score < 70) {
        color = '#f59e0b'; // Yellow
    } else {
        color = '#10b981'; // Green
    }
    
    gaugeFill.style.stroke = color;
    scoreNumber.style.color = color;
}

/**
 * Display news articles
 */
function displayNews(articles) {
    // Handle case where articles is not an array
    if (!articles || !Array.isArray(articles) || articles.length === 0) {
        newsList.innerHTML = '<div class="news-empty">No recent news available</div>';
        return;
    }
    
    newsList.innerHTML = articles.map(article => `
        <a href="${article.article_url || '#'}" target="_blank" class="news-item">
            <div class="news-title">${escapeHtml(article.title || 'No title')}</div>
            <div class="news-meta">
                <span class="news-source">${escapeHtml(article.publisher || 'Unknown')}</span>
                <span class="news-date">${formatDate(article.published_utc)}</span>
            </div>
        </a>
    `).join('');
}

/**
 * Format date string
 */
function formatDate(dateString) {
    if (!dateString) return '';
    
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    
    if (diffHours < 1) {
        return 'Just now';
    } else if (diffHours < 24) {
        return `${diffHours}h ago`;
    } else {
        const diffDays = Math.floor(diffHours / 24);
        return `${diffDays}d ago`;
    }
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

/**
 * Show error message
 */
function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
    updateStatus('Error', 'error');
}

/**
 * Clear error message
 */
function clearError() {
    errorMessage.textContent = '';
    errorMessage.style.display = 'none';
}

/**
 * Set loading state
 */
function setLoadingState(loading) {
    isLoading = loading;
    
    if (loading) {
        analyzeBtn.classList.add('loading');
        analyzeBtn.disabled = true;
        tickerInput.disabled = true;
        updateStatus('Analyzing...', 'loading');
    } else {
        analyzeBtn.classList.remove('loading');
        analyzeBtn.disabled = false;
        tickerInput.disabled = false;
    }
}

/**
 * Update status indicator
 */
function updateStatus(text, type) {
    const statusDot = status.querySelector('.dot');
    const statusText = status.querySelector('.text');
    
    statusText.textContent = text;
    
    // Remove all status classes
    statusDot.classList.remove('status-ready', 'status-loading', 'status-success', 'status-error');
    
    // Add appropriate class
    switch(type) {
        case 'loading':
            statusDot.classList.add('status-loading');
            break;
        case 'success':
            statusDot.classList.add('status-success');
            setTimeout(() => {
                updateStatus('Ready', 'ready');
            }, 3000);
            break;
        case 'error':
            statusDot.classList.add('status-error');
            setTimeout(() => {
                updateStatus('Ready', 'ready');
            }, 5000);
            break;
        default:
            statusDot.classList.add('status-ready');
    }
}

/**
 * Show skeleton loader
 */
function showSkeleton() {
    skeletonLoader.style.display = 'block';
}

/**
 * Hide skeleton loader
 */
function hideSkeleton() {
    skeletonLoader.style.display = 'none';
}

/**
 * Hide results section
 */
function hideResults() {
    resultsSection.style.display = 'none';
}

