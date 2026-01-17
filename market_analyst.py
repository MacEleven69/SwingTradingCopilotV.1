"""
Market Analyst Module - Holistic AI Analysis
============================================

Comprehensive market analysis combining:
- Technical indicators
- Market regime data
- Relative strength
- News sentiment

Uses OpenAI GPT-4o-mini as a "Senior Swing Trading Mentor"
Provides actionable insights even without news data.
"""

import requests
import json
from typing import Dict, List, Optional
from datetime import datetime
from config import config


class MarketAnalyst:
    """
    Holistic market analysis using AI + quantitative data
    Provides insights even when news is unavailable
    """
    
    def __init__(self):
        """Initialize with API keys from config"""
        self.polygon_api_key = config.POLYGON_API_KEY
        self.openai_api_key = config.OPENAI_API_KEY
        
        if not self.polygon_api_key:
            raise ValueError("POLYGON_API_KEY not found in config")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in config")
        
        print(f"[OK] MarketAnalyst initialized")
        print(f"   Polygon: {self.polygon_api_key[:8]}...")
        print(f"   OpenAI: {self.openai_api_key[:15]}...")
    
    def fetch_news(self, ticker: str, limit: int = 10) -> List[Dict]:
        """
        Fetch recent news articles for a ticker
        
        Args:
            ticker: Stock ticker symbol
            limit: Number of articles to fetch
            
        Returns:
            List of news articles with title, url, etc.
        """
        try:
            # Fetch general market news (no ticker filter since it doesn't work well)
            url = "https://api.polygon.io/v2/reference/news"
            params = {
                'limit': 50,  # Fetch more to find relevant ones
                'order': 'desc',
                'sort': 'published_utc',
                'apiKey': self.polygon_api_key
            }
            
            print(f"[NEWS] Fetching news for {ticker}...")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if 'results' not in data or len(data['results']) == 0:
                print(f"   [!]  No news found")
                return []
            
            print(f"   [OK] Found {len(data['results'])} articles from API")
            
            # Search through articles for ticker-specific ones
            ticker_articles = []
            
            for article in data['results']:
                title = article.get('title', '')
                article_tickers = article.get('tickers', [])
                
                # Check if ticker is in the tickers list OR mentioned in title
                ticker_upper = ticker.upper()
                in_tickers_list = ticker_upper in [t.upper() for t in article_tickers]
                in_title = ticker_upper in title.upper()
                
                if in_tickers_list or in_title:
                    ticker_articles.append({
                        'title': title,
                        'description': article.get('description', ''),
                        'published_utc': article.get('published_utc', ''),
                        'publisher': article.get('publisher', {}).get('name', 'Unknown'),
                        'article_url': article.get('article_url', '#')
                    })
                    
                    # Stop after finding enough relevant articles
                    if len(ticker_articles) >= 10:
                        break
            
            # Show results
            if ticker_articles:
                print(f"   [OK] Found {len(ticker_articles)} relevant articles")
                print(f"   📄 First: {ticker_articles[0]['title'][:60]}...")
            else:
                print(f"   [!]  No ticker-specific articles found")
            
            return ticker_articles
            
        except Exception as e:
            print(f"   [ERROR] Error fetching news: {e}")
            return []
    
    def analyze_context(self, ticker: str, score: int, breakdown: Dict, news_list: List[Dict] = None) -> Dict:
        """
        Holistic analysis using ALL available context
        
        This is the MASTER method that combines:
        - Technical score
        - Market regime data
        - Relative strength
        - News (if available)
        
        Args:
            ticker: Stock ticker symbol
            score: Final swing score (0-100)
            breakdown: Full breakdown with technicals, regime, relative strength
            news_list: Optional list of news articles (can be empty/None)
            
        Returns:
            Dict with analysis, key_risk, and sentiment_score
        """
        try:
            if news_list is None:
                news_list = []
            
            # Build context for AI
            news_text = ""
            if news_list and len(news_list) > 0:
                news_headlines = "\n".join([f"- {article['title']}" for article in news_list[:5]])
                news_text = f"\n\nRECENT NEWS:\n{news_headlines}"
            else:
                news_text = "\n\n[No recent news available - Focus on technical/market data]"
            
            # Extract breakdown details
            details = breakdown.get('details', {})
            tech_details = details.get('technicals', {})
            regime_details = details.get('market_regime', {})
            rel_details = details.get('relative_strength', {})
            
            # Build quantitative summary
            quant_summary = f"""
QUANTITATIVE ANALYSIS:
- Overall Score: {score}/100
- Technical Score: {breakdown.get('technicals', 0)}/40
  • RSI: {tech_details.get('rsi', 'N/A')}
  • Trend: {tech_details.get('price_vs_200sma', 'N/A')}
  • Volume: {tech_details.get('volume', 'N/A')}
- Market Regime: {breakdown.get('market_regime', 0)}/30
  • SPY Trend: {regime_details.get('spy_trend', 'N/A')}
  • VIX: {regime_details.get('vix', 'N/A')}
- Relative Strength: {breakdown.get('relative_strength', 0)}/20
  • Stock 5D: {rel_details.get('stock_5d_return', 'N/A')}
  • SPY 5D: {rel_details.get('spy_5d_return', 'N/A')}
  • Status: {rel_details.get('status', 'N/A')}
"""
            
            # The Master Prompt - Senior Swing Trading Mentor
            system_prompt = """You are a Senior Swing Trading Analyst at a prestigious hedge fund.
Your job is to provide ACTIONABLE insights to traders, not generic commentary.

CRITICAL RULES:
1. Always provide value - even without news, you can analyze the technicals
2. Be direct and specific - no fluff or generic statements
3. Focus on what matters most for the current score level
4. Professional tone - think Bloomberg Terminal, not Reddit

SCORING INTERPRETATION:
- 80-100: Strong Buy - Explain WHY this is a screaming opportunity
- 60-79: Buy - What's driving the setup, what's the risk
- 40-59: Hold - "If you're in, hold. If flat, wait for better entry."
- 20-39: Avoid - Clear reasons why this isn't tradeable
- 0-19: Strong Sell - Red flags that traders must know

IF NO NEWS:
- DO NOT say "no news available" or "insufficient data"
- INSTEAD: Focus on what you DO have - technicals, regime, momentum
- Example: "Despite quiet news cycle, technicals show strong setup..."

Return ONLY valid JSON:
{
  "analysis": "2-3 sentence actionable summary",
  "key_risk": "The single biggest risk right now",
  "sentiment_score": <number -10 to +10 based on OVERALL outlook>
}"""
            
            user_prompt = f"""Analyze ${ticker}

{quant_summary}{news_text}

Provide your professional analysis."""
            
            # Call OpenAI
            headers = {
                'Authorization': f'Bearer {self.openai_api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': 'gpt-4o-mini',
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt}
                ],
                'temperature': 0.7,  # Slightly creative but still professional
                'max_tokens': 250,
                'response_format': {'type': 'json_object'}
            }
            
            print(f"[AI] Calling GPT-4o-mini for holistic analysis...")
            
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=payload,
                timeout=15
            )
            response.raise_for_status()
            
            result = response.json()
            analysis_text = result['choices'][0]['message']['content']
            analysis = json.loads(analysis_text)
            
            sentiment_score = analysis.get('sentiment_score', 0)
            
            # Ensure score is in range
            sentiment_score = max(-10, min(10, int(sentiment_score)))
            
            print(f"   [OK] Analysis complete (sentiment: {sentiment_score:+d}/10)")
            
            return {
                'sentiment_score': sentiment_score,
                'analysis': analysis.get('analysis', 'Analysis unavailable'),
                'key_risk': analysis.get('key_risk', 'Monitor market conditions'),
                'news_count': len(news_list) if news_list else 0
            }
            
        except Exception as e:
            print(f"   [ERROR] Error in holistic analysis: {e}")
            
            # Intelligent fallback based on score
            if score >= 70:
                fallback_analysis = "Strong technical setup with favorable market conditions. Monitor for entry timing."
                fallback_risk = "Potential for short-term pullback"
                fallback_score = 5
            elif score >= 50:
                fallback_analysis = "Mixed signals present. If holding, maintain position. If flat, wait for clearer setup."
                fallback_risk = "Unclear momentum direction"
                fallback_score = 0
            else:
                fallback_analysis = "Technical setup not favorable for swing entry at current levels."
                fallback_risk = "Weak momentum and market headwinds"
                fallback_score = -3
            
            return {
                'sentiment_score': fallback_score,
                'analysis': fallback_analysis,
                'key_risk': fallback_risk,
                'news_count': 0
            }
    
    def get_comprehensive_analysis(self, ticker: str, score: int, breakdown: Dict) -> Dict:
        """
        Complete workflow: Fetch news -> Perform holistic analysis
        
        Args:
            ticker: Stock ticker symbol
            score: Final swing score
            breakdown: Full scoring breakdown
            
        Returns:
            Dict with comprehensive analysis
        """
        try:
            # Fetch news (may return empty list)
            news_list = self.fetch_news(ticker, limit=10)
            
            # Perform holistic analysis (works with or without news)
            analysis = self.analyze_context(ticker, score, breakdown, news_list)
            
            return analysis
            
        except Exception as e:
            print(f"   [ERROR] Error in comprehensive analysis: {e}")
            return {
                'sentiment_score': 0,
                'analysis': f'Analysis temporarily unavailable',
                'key_risk': 'System error',
                'news_count': 0
            }


# For backward compatibility - keep NewsAnalyzer as alias
NewsAnalyzer = MarketAnalyst


if __name__ == '__main__':
    """Test the MarketAnalyst"""
    print("\n" + "="*80)
    print("MARKET ANALYST TEST")
    print("="*80)
    
    try:
        analyst = MarketAnalyst()
        
        # Test with mock data
        test_ticker = "AAPL"
        test_score = 75
        test_breakdown = {
            'technicals': 35,
            'market_regime': 25,
            'relative_strength': 15,
            'ai_sentiment': 0,
            'details': {
                'technicals': {
                    'rsi': '58.5 (Ideal, +10)',
                    'price_vs_200sma': 'Above $145.20 (+10)',
                    'volume': 'Above avg (+10)'
                },
                'market_regime': {
                    'spy_trend': 'Bull Market: $450.50 > $445.20 (+15)',
                    'vix': '15.2 (Low Fear, +15)'
                },
                'relative_strength': {
                    'stock_5d_return': '+2.5%',
                    'spy_5d_return': '+1.2%',
                    'status': 'Leader (+15)'
                }
            }
        }
        
        print(f"\n[STATS] Testing comprehensive analysis for {test_ticker}...")
        print(f"   Score: {test_score}/100")
        print()
        
        result = analyst.get_comprehensive_analysis(test_ticker, test_score, test_breakdown)
        
        print("\n[OK] ANALYSIS RESULT:")
        print(f"   Sentiment: {result['sentiment_score']:+d}/10")
        print(f"   Analysis: {result['analysis']}")
        print(f"   Key Risk: {result['key_risk']}")
        print(f"   News Articles: {result.get('news_count', 0)}")
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")






















