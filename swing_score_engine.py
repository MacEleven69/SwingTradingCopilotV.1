"""
Swing Score Engine - Market-Aware Scoring with REST API Only
NO WEBSOCKET - Safe for HFT bot coexistence
"""

import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from config import config
from typing import Dict, List, Tuple


class SwingScoreEngine:
    """
    Market-Aware Swing Trading Scorer using Alpaca REST API ONLY
    
    CRITICAL: This uses ONLY REST API calls, never WebSocket/StreamConn
    This ensures zero interference with your HFT bot's WebSocket connection
    """
    
    def __init__(self):
        """Initialize with REST clients only"""
        # IMPORTANT: Using StockHistoricalDataClient (REST) not StockDataStream (WebSocket)
        self.data_client = StockHistoricalDataClient(
            api_key=config.ALPACA_API_KEY,
            secret_key=config.ALPACA_SECRET_KEY
        )
        
        self.lookback_days = config.LOOKBACK_DAYS
        
        print(f"[OK] SwingScoreEngine initialized (REST API only)")
        print(f"   Lookback: {self.lookback_days} days")
        print(f"   [!]  No WebSocket - HFT bot safe!")
    
    def fetch_bars_rest(self, symbol: str, days: int = None, end_date: datetime = None) -> pd.DataFrame:
        """
        Fetch historical bars using REST API (not WebSocket)
        
        Args:
            symbol: Stock ticker
            days: Number of days to fetch (default from config)
            end_date: Optional end date for point-in-time backtesting (default: now)
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            days = days or self.lookback_days
            end = end_date if end_date else datetime.now()
            start = end - timedelta(days=days)
            
            # REST API call (not WebSocket)
            request_params = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=start,
                end=end
            )
            
            bars = self.data_client.get_stock_bars(request_params)
            
            # Check if data was returned
            if not bars or not bars.data:
                raise ValueError(f"No data returned for {symbol}")
            
            if symbol not in bars.data:
                raise ValueError(f"Symbol {symbol} not in response. Available: {list(bars.data.keys())}")
            
            bar_list = bars.data[symbol]
            if len(bar_list) == 0:
                raise ValueError(f"Empty data for {symbol}")
            
            # Convert to DataFrame
            data = []
            for bar in bar_list:
                data.append({
                    'timestamp': bar.timestamp,
                    'open': float(bar.open),
                    'high': float(bar.high),
                    'low': float(bar.low),
                    'close': float(bar.close),
                    'volume': int(bar.volume)
                })
            
            df = pd.DataFrame(data)
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            print(f"      [OK] {symbol}: {len(df)} bars fetched")
            
            return df
            
        except Exception as e:
            raise Exception(f"Failed to fetch bars for {symbol}: {e}")
    
    def calculate_technicals(self, df: pd.DataFrame) -> Dict:
        """
        Calculate technical indicators using "Trend Pullback" strategy
        
        NEW LOGIC (v2.0 - Pullback Strategy):
        - Trend Filter: Price vs 200 SMA (gatekeeper)
        - RSI Dip Bonus: Rewards pullbacks, penalizes overbought
        - EMA Proximity: Rewards price near 20 EMA support
        
        Returns:
            Dict with technical scores and details
        """
        score = 0
        details = {}
        max_score_cap = 100  # Default no cap
        
        try:
            # Calculate indicators
            df['sma_200'] = ta.sma(df['close'], length=200)
            df['ema_20'] = ta.ema(df['close'], length=20)
            df['rsi'] = ta.rsi(df['close'], length=14)
            
            current_price = df['close'].iloc[-1]
            sma_200 = df['sma_200'].iloc[-1]
            ema_20 = df['ema_20'].iloc[-1]
            rsi = df['rsi'].iloc[-1]
            
            # Store raw values for exit logic
            details['raw_values'] = {
                'price': current_price,
                'sma_200': sma_200 if not pd.isna(sma_200) else None,
                'ema_20': ema_20 if not pd.isna(ema_20) else None,
                'rsi': rsi if not pd.isna(rsi) else None
            }
            
            # ═══════════════════════════════════════════════════════════════
            # TREND FILTER (The Gatekeeper) - 50 points base or 0 cap
            # ═══════════════════════════════════════════════════════════════
            if not pd.isna(sma_200):
                if current_price > sma_200:
                    # UPTREND: Base score starts at 50
                    score = 50
                    details['trend_filter'] = f'[OK] UPTREND: ${current_price:.2f} > 200 SMA ${sma_200:.2f} (Base +50)'
                    details['in_uptrend'] = True
                else:
                    # DOWNTREND: Cap score at 40 maximum (no-trade zone)
                    score = 0
                    max_score_cap = 40
                    details['trend_filter'] = f'⛔ DOWNTREND: ${current_price:.2f} < 200 SMA ${sma_200:.2f} (Capped at 40)'
                    details['in_uptrend'] = False
            else:
                score = 25  # Neutral if insufficient data
                details['trend_filter'] = 'Insufficient data (need 200 days)'
                details['in_uptrend'] = None
            
            # ═══════════════════════════════════════════════════════════════
            # RSI DIP BONUS (The Alpha) - Up to +30 or -20
            # ═══════════════════════════════════════════════════════════════
            rsi_score = 0
            if not pd.isna(rsi):
                if rsi > 70:
                    # OVERBOUGHT - Do not buy!
                    rsi_score = -20
                    details['rsi_signal'] = f'🔴 OVERBOUGHT: RSI {rsi:.1f} > 70 (-20)'
                elif 50 <= rsi <= 70:
                    # Strong momentum, but not ideal entry
                    rsi_score = 10
                    details['rsi_signal'] = f'🟡 MOMENTUM: RSI {rsi:.1f} in 50-70 (+10)'
                elif 30 <= rsi < 50:
                    # THE SWEET SPOT - Pullback in uptrend!
                    rsi_score = 30
                    details['rsi_signal'] = f'🟢 SWEET SPOT: RSI {rsi:.1f} in 30-50 (+30)'
                else:
                    # Oversold - potentially dangerous but cheap
                    rsi_score = 10
                    details['rsi_signal'] = f'🟠 OVERSOLD: RSI {rsi:.1f} < 30 (+10)'
            else:
                details['rsi_signal'] = 'RSI unavailable'
            
            score += rsi_score
            details['rsi_score'] = rsi_score
            
            # ═══════════════════════════════════════════════════════════════
            # EMA PROXIMITY (The Trigger) - Up to +20 or -10
            # ═══════════════════════════════════════════════════════════════
            ema_score = 0
            if not pd.isna(ema_20):
                ema_distance_pct = ((current_price - ema_20) / ema_20) * 100
                
                if abs(ema_distance_pct) <= 2:
                    # Within 2% of EMA - Testing support!
                    ema_score = 20
                    details['ema_signal'] = f'🟢 NEAR SUPPORT: {ema_distance_pct:+.1f}% from 20 EMA (+20)'
                elif ema_distance_pct > 10:
                    # Extended above - risky entry
                    ema_score = -10
                    details['ema_signal'] = f'🔴 EXTENDED: {ema_distance_pct:+.1f}% above 20 EMA (-10)'
                elif ema_distance_pct < -10:
                    # Extended below - falling knife
                    ema_score = -10
                    details['ema_signal'] = f'🔴 FALLING: {ema_distance_pct:+.1f}% below 20 EMA (-10)'
                else:
                    # Moderate distance
                    ema_score = 0
                    details['ema_signal'] = f'🟡 MODERATE: {ema_distance_pct:+.1f}% from 20 EMA (0)'
                
                details['ema_distance_pct'] = ema_distance_pct
            else:
                details['ema_signal'] = '20 EMA unavailable'
            
            score += ema_score
            details['ema_score'] = ema_score
            
            # ═══════════════════════════════════════════════════════════════
            # APPLY CAP (Downtrend protection)
            # ═══════════════════════════════════════════════════════════════
            final_score = max(0, min(score, max_score_cap))
            
            if max_score_cap < 100:
                details['cap_applied'] = f'Score capped at {max_score_cap} (downtrend protection)'
            
            details['trend_score'] = 50 if details.get('in_uptrend') else 0
            
        except Exception as e:
            details['error'] = str(e)
            final_score = 0
        
        return {'score': final_score, 'details': details}
    
    def calculate_market_regime(self, spy_df: pd.DataFrame, vix_df: pd.DataFrame = None) -> Dict:
        """
        Calculate market regime score
        
        Args:
            spy_df: SPY DataFrame
            vix_df: VIX DataFrame (optional)
        
        Returns:
            Dict with regime score and details
        """
        score = 0
        details = {}
        
        try:
            # SPY trend
            spy_df['sma_50'] = ta.sma(spy_df['close'], length=50)
            spy_current = spy_df['close'].iloc[-1]
            spy_sma_50 = spy_df['sma_50'].iloc[-1]
            
            if not pd.isna(spy_sma_50) and spy_current > spy_sma_50:
                score += 15
                details['spy_trend'] = f'Bull: ${spy_current:.2f} > ${spy_sma_50:.2f} (+15)'
            else:
                details['spy_trend'] = f'Bear: ${spy_current:.2f} < ${spy_sma_50:.2f} (0)'
            
            # VIX fear gauge (if available)
            if vix_df is not None and len(vix_df) > 0:
                vix_current = vix_df['close'].iloc[-1]
                
                if vix_current < 20:
                    vix_score = 15
                    details['vix'] = f'{vix_current:.1f} (Low Fear, +15)'
                elif vix_current > 30:
                    vix_score = -20
                    details['vix'] = f'{vix_current:.1f} (HIGH FEAR, -20)'
                else:
                    vix_score = 0
                    details['vix'] = f'{vix_current:.1f} (Elevated, 0)'
                
                score += vix_score
            else:
                # VIX not available, assume neutral (0 points)
                details['vix'] = 'Not available (assuming neutral)'
            
            details['regime_score'] = max(0, score)
            
        except Exception as e:
            details['error'] = str(e)
        
        return {'score': max(0, score), 'details': details}
    
    def calculate_relative_strength(self, stock_df: pd.DataFrame, spy_df: pd.DataFrame) -> Tuple[int, Dict, bool]:
        """
        Calculate relative strength
        
        Returns:
            (score, details, kill_switch_triggered)
        """
        details = {}
        kill_switch = False
        
        try:
            # 5-day returns
            stock_return = ((stock_df['close'].iloc[-1] - stock_df['close'].iloc[-6]) / 
                           stock_df['close'].iloc[-6]) * 100
            spy_return = ((spy_df['close'].iloc[-1] - spy_df['close'].iloc[-6]) / 
                         spy_df['close'].iloc[-6]) * 100
            
            details['stock_5d_return'] = f'{stock_return:+.2f}%'
            details['spy_5d_return'] = f'{spy_return:+.2f}%'
            
            # KILL SWITCH
            if stock_return < 0 and spy_return > 0:
                kill_switch = True
                details['status'] = '[ALERT] RELATIVE WEAKNESS (Auto-Fail)'
                return 0, details, True
            
            # Leader vs Laggard
            if stock_return > spy_return:
                score = 20
                details['status'] = 'Leader (+20)'
            else:
                score = 0
                details['status'] = 'Laggard (0)'
            
        except Exception as e:
            details['error'] = str(e)
            score = 0
        
        return score, details, kill_switch
    
    def calculate_trade_setup(self, df: pd.DataFrame) -> Dict:
        """
        Calculate beginner-friendly trade setup with DUAL TARGETS.
        
        Base Hit Strategy:
        - Target A (Safe): +4% or nearest resistance
        - Target B (Aggro): +10% if volatility supports it
        
        Returns:
        - buy_min, buy_max: Entry zone
        - sell_stop: Stop loss
        - target_safe: Conservative +4% target (high probability)
        - target_aggro: Aggressive +10% target (lower probability)
        - prob_safe, prob_aggro: Estimated win probabilities
        """
        try:
            # Calculate indicators
            df['ema_20'] = ta.ema(df['close'], length=20)
            df['sma_50'] = ta.sma(df['close'], length=50)
            df['sma_200'] = ta.sma(df['close'], length=200)
            df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
            
            current_price = df['close'].iloc[-1]
            ema_20 = df['ema_20'].iloc[-1]
            sma_50 = df['sma_50'].iloc[-1]
            sma_200 = df['sma_200'].iloc[-1]
            atr = df['atr'].iloc[-1]
            
            # Entry Zone: -2% to +2% around 20 EMA
            if not pd.isna(ema_20):
                buy_min = ema_20 * 0.98
                buy_max = ema_20 * 1.02
            else:
                buy_min = current_price * 0.98
                buy_max = current_price * 1.02
            
            # Stop Loss: -8% or below 200 SMA
            if not pd.isna(sma_200):
                sma_stop = sma_200 * 0.99  # Just below 200 SMA
                pct_stop = current_price * 0.92  # -8%
                sell_stop = max(sma_stop, pct_stop)
            else:
                sell_stop = current_price * 0.92
            
            # ═══════════════════════════════════════════════════════════════
            # TARGET A: "BASE HIT" (+4% or nearest resistance)
            # ═══════════════════════════════════════════════════════════════
            base_target = current_price * 1.04  # Default +4%
            
            # Check if 50 SMA is a closer resistance (only if above current price)
            if not pd.isna(sma_50) and sma_50 > current_price:
                distance_to_sma50 = (sma_50 - current_price) / current_price
                if distance_to_sma50 < 0.04:  # 50 SMA is closer than 4%
                    base_target = sma_50 * 0.995  # Just below resistance
            
            target_safe = base_target
            target_safe_pct = ((target_safe - current_price) / current_price) * 100
            
            # ═══════════════════════════════════════════════════════════════
            # TARGET B: "GRAND SLAM" (+10% if volatility supports it)
            # ═══════════════════════════════════════════════════════════════
            target_aggro = current_price * 1.10  # Default +10%
            
            # Check if ATR supports this move (need ~2.5 ATR of room)
            volatility_supported = True
            if not pd.isna(atr):
                atr_ratio = (target_aggro - current_price) / atr
                if atr_ratio > 5:  # Need more than 5 ATRs - unlikely
                    volatility_supported = False
            
            target_aggro_pct = ((target_aggro - current_price) / current_price) * 100
            
            # ═══════════════════════════════════════════════════════════════
            # PROBABILITY ESTIMATES (Mock logic - can be refined)
            # ═══════════════════════════════════════════════════════════════
            # Base probability based on target distance
            prob_safe = 75  # Base hit has ~75% probability
            prob_aggro = 40  # Grand slam has ~40% probability
            
            # Adjust based on trend (if above 200 SMA, boost probabilities)
            if not pd.isna(sma_200) and current_price > sma_200:
                prob_safe = min(85, prob_safe + 10)
                prob_aggro = min(55, prob_aggro + 10)
            
            # Reduce aggro probability if volatility doesn't support
            if not volatility_supported:
                prob_aggro = max(20, prob_aggro - 15)
            
            return {
                'buy_min': float(buy_min),
                'buy_max': float(buy_max),
                'sell_stop': float(sell_stop),
                # Dual targets
                'target_safe': float(target_safe),
                'target_safe_pct': round(target_safe_pct, 1),
                'target_aggro': float(target_aggro),
                'target_aggro_pct': round(target_aggro_pct, 1),
                # Probabilities
                'prob_safe': int(prob_safe),
                'prob_aggro': int(prob_aggro),
                # Meta
                'volatility_supported': volatility_supported,
                'recommended': 'safe'  # Always recommend base hit
            }
            
        except Exception as e:
            return {
                'buy_min': 0,
                'buy_max': 0,
                'sell_stop': 0,
                'target_safe': 0,
                'target_safe_pct': 4.0,
                'target_aggro': 0,
                'target_aggro_pct': 10.0,
                'prob_safe': 75,
                'prob_aggro': 40,
                'volatility_supported': True,
                'recommended': 'safe',
                'error': str(e)
            }
    
    def _get_verdict(self, score: int, kill_switch: bool = False) -> str:
        """
        Map numerical score to clear text verdict (v2.0 Pullback Strategy)
        
        NEW THRESHOLDS:
        - 80+: STRONG BUY (Uptrend + Pullback + Near Support)
        - 60-79: BUY (Good setup, minor flaws)
        - 40-59: HOLD (Neutral or capped by downtrend)
        - <40: AVOID (Downtrend or poor setup)
        
        Args:
            score: Swing score (0-100)
            kill_switch: If True, force "AVOID (Rel. Weakness)"
            
        Returns:
            Verdict string
        """
        if kill_switch:
            return "AVOID (Rel. Weakness)"
        
        if score >= 80:
            return "STRONG BUY"  # Uptrend + RSI pullback + Near EMA support
        elif score >= 60:
            return "BUY"         # Good setup, maybe slightly extended
        elif score >= 40:
            return "HOLD"        # Neutral or capped (downtrend)
        else:
            return "AVOID"       # Poor setup or downtrend
    
    def calculate_score(self, ticker: str, end_date: datetime = None, verbose: bool = True) -> Dict:
        """
        Calculate complete market-aware swing score using REST API only
        
        Args:
            ticker: Stock symbol
            end_date: Optional end date for point-in-time backtesting (default: now)
            verbose: If True, print progress messages (default: True)
            
        Returns:
            Dict with score and detailed breakdown
        """
        try:
            if verbose:
                date_str = end_date.strftime('%Y-%m-%d') if end_date else 'today'
                print(f"\n[STATS] Fetching data for {ticker} as of {date_str}...")
            
            # Fetch data via REST (not WebSocket)
            stock_df = self.fetch_bars_rest(ticker, end_date=end_date)
            spy_df = self.fetch_bars_rest('SPY', end_date=end_date)
            
            # Try to fetch VIX (might not be available on all feeds)
            try:
                vix_df = self.fetch_bars_rest('VIX', end_date=end_date)
            except:
                # VIX not available, use a synthetic fear gauge or default
                if verbose:
                    print(f"      [!]  VIX: Not available (will use default regime score)")
                vix_df = None
            
            # Calculate components
            tech_result = self.calculate_technicals(stock_df)
            regime_result = self.calculate_market_regime(spy_df, vix_df)
            rel_score, rel_details, kill_switch = self.calculate_relative_strength(stock_df, spy_df)
            
            # KILL SWITCH check
            if kill_switch:
                return {
                    'ticker': ticker,
                    'score': 0,
                    'verdict': self._get_verdict(0, kill_switch=True),
                    'reason': 'RELATIVE WEAKNESS KILL SWITCH',
                    'breakdown': {
                        'technicals': tech_result['score'],
                        'market_regime': regime_result['score'],
                        'relative_strength': 0,
                        'details': {
                            'technicals': tech_result['details'],
                            'market_regime': regime_result['details'],
                            'relative_strength': rel_details
                        }
                    },
                    'current_price': float(stock_df['close'].iloc[-1])
                }
            
            # Calculate final score
            final_score = tech_result['score'] + regime_result['score'] + rel_score
            
            # Get verdict using the mapping method
            verdict = self._get_verdict(final_score)
            
            # Calculate beginner-friendly trade setup
            trade_setup = self.calculate_trade_setup(stock_df)
            
            return {
                'ticker': ticker,
                'score': final_score,
                'verdict': verdict,
                'breakdown': {
                    'technicals': tech_result['score'],
                    'market_regime': regime_result['score'],
                    'relative_strength': rel_score,
                    'details': {
                        'technicals': tech_result['details'],
                        'market_regime': regime_result['details'],
                        'relative_strength': rel_details
                    }
                },
                'current_price': float(stock_df['close'].iloc[-1]),
                'trade_setup': trade_setup  # Beginner-friendly entry/exit levels
            }
            
        except Exception as e:
            return {
                'error': f'Score calculation failed: {str(e)}'
            }


if __name__ == '__main__':
    """Test the scoring engine"""
    print("="*80)
    print("SWING SCORE ENGINE TEST (REST API ONLY)")
    print("="*80)
    
    engine = SwingScoreEngine()
    
    # Test with a ticker
    result = engine.calculate_score('AAPL')
    
    if 'error' in result:
        print(f"\n[ERROR] Error: {result['error']}")
    else:
        print(f"\n[OK] SUCCESS!")
        print(f"\n[TARGET] {result['ticker']}: {result['score']}/100")
        print(f"   Verdict: {result['verdict']}")
        print(f"   Price: ${result['current_price']:.2f}")
        
        breakdown = result['breakdown']
        print(f"\n[STATS] Breakdown:")
        print(f"   Technicals: {breakdown['technicals']}/40")
        print(f"   Market Regime: {breakdown['market_regime']}/30")
        print(f"   Relative Strength: {breakdown['relative_strength']}/20")

