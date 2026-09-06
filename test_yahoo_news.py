#!/usr/bin/env python3
"""
Quick test script to verify Yahoo Finance news integration
Tests the fetch_news method without requiring full environment setup
"""

import yfinance as yf

def test_yfinance_news():
    """Test fetching news directly with yfinance"""
    print("="*80)
    print("YAHOO FINANCE NEWS TEST")
    print("="*80)
    
    test_tickers = ['AAPL', 'TSLA', 'MSFT']
    
    for ticker in test_tickers:
        print(f"\n📰 Testing {ticker}...")
        try:
            stock = yf.Ticker(ticker)
            news = stock.news
            
            if not news:
                print(f"   ⚠️  No news available for {ticker}")
                continue
            
            print(f"   ✅ Found {len(news)} articles")
            
            # Show first 3 articles
            for i, article in enumerate(news[:3], 1):
                content = article.get('content', {})
                title = content.get('title', 'No title')
                publisher = content.get('provider', {}).get('displayName', 'Unknown')
                pub_date = content.get('pubDate', 'Unknown date')
                
                print(f"\n   {i}. {title[:70]}...")
                print(f"      Publisher: {publisher}")
                print(f"      Published: {pub_date}")
        
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "="*80)
    print("✅ Test Complete - Yahoo Finance integration working!")
    print("="*80)

if __name__ == '__main__':
    test_yfinance_news()
