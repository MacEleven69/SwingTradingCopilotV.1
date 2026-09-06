#!/usr/bin/env python3
"""
Debug script to see actual Yahoo Finance news structure
"""

import yfinance as yf
import json

def debug_yfinance_structure():
    """Debug to see exact structure"""
    print("="*80)
    print("YAHOO FINANCE NEWS STRUCTURE DEBUG")
    print("="*80)
    
    ticker = "AAPL"
    print(f"\nFetching news for {ticker}...")
    
    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        
        if not news:
            print("No news found!")
            return
        
        print(f"\nFound {len(news)} articles")
        print(f"\nType of news: {type(news)}")
        
        # Show first article structure
        print(f"\n{'='*80}")
        print("FIRST ARTICLE STRUCTURE:")
        print(f"{'='*80}")
        
        first = news[0]
        print(f"\nType: {type(first)}")
        print(f"\nKeys available: {list(first.keys()) if isinstance(first, dict) else 'NOT A DICT'}")
        
        print(f"\n{'='*80}")
        print("RAW DATA (First Article):")
        print(f"{'='*80}")
        print(json.dumps(first, indent=2, default=str))
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_yfinance_structure()
