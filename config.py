"""
Configuration Management
Loads API keys from environment variables or .env file
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """
    Centralized configuration for all API keys and settings
    """
    
    # Alpaca API (REST only - no WebSocket interference with HFT bot)
    ALPACA_API_KEY = os.getenv('ALPACA_API_KEY')
    ALPACA_SECRET_KEY = os.getenv('ALPACA_SECRET_KEY')
    ALPACA_BASE_URL = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
    # For live: 'https://api.alpaca.markets'
    
    # Polygon API (News)
    POLYGON_API_KEY = os.getenv('POLYGON_API_KEY')
    
    # OpenAI API (Sentiment)
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # Data fetching settings
    LOOKBACK_DAYS = 250  # Fetch 250 days of history for 200-day SMA
    CACHE_TIMEOUT = 900  # 15 minutes
    
    # API settings
    REQUEST_TIMEOUT = 30  # seconds
    MAX_RETRIES = 3
    
    @classmethod
    def validate(cls):
        """Validate that all required keys are present"""
        required = {
            'ALPACA_API_KEY': cls.ALPACA_API_KEY,
            'ALPACA_SECRET_KEY': cls.ALPACA_SECRET_KEY,
            'POLYGON_API_KEY': cls.POLYGON_API_KEY,
            'OPENAI_API_KEY': cls.OPENAI_API_KEY
        }
        
        missing = [key for key, value in required.items() if not value]
        
        if missing:
            raise ValueError(f"Missing required API keys: {', '.join(missing)}")
        
        return True
    
    @classmethod
    def get_summary(cls):
        """Get configuration summary (safe for logging)"""
        return {
            'alpaca_key': f"{cls.ALPACA_API_KEY[:8]}..." if cls.ALPACA_API_KEY else "NOT SET",
            'alpaca_url': cls.ALPACA_BASE_URL,
            'polygon_key': f"{cls.POLYGON_API_KEY[:8]}..." if cls.POLYGON_API_KEY else "NOT SET",
            'openai_key': f"{cls.OPENAI_API_KEY[:15]}..." if cls.OPENAI_API_KEY else "NOT SET",
            'lookback_days': cls.LOOKBACK_DAYS,
            'cache_timeout': f"{cls.CACHE_TIMEOUT}s"
        }


# Create singleton instance
config = Config()


if __name__ == '__main__':
    """Test configuration"""
    print("="*80)
    print("CONFIGURATION TEST")
    print("="*80)
    
    try:
        config.validate()
        print("\n[OK] All API keys present")
        
        summary = config.get_summary()
        print("\n[STATS] Configuration Summary:")
        for key, value in summary.items():
            print(f"   {key}: {value}")
        
        print("\n[!]  IMPORTANT: Using REST API only (no WebSocket)")
        print("   This ensures no interference with your HFT bot")
        
    except ValueError as e:
        print(f"\n[ERROR] Configuration Error: {e}")






















