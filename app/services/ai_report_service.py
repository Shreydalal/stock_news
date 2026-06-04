import logging
from datetime import date
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from groq import Groq

from app.core.config import settings
from app.models.asset import Asset
from app.models.market_data import MarketData
from app.models.indicator import Indicator
from app.repositories.asset_repository import AssetRepository
from app.repositories.market_data_repository import MarketDataRepository
from app.repositories.indicator_repository import IndicatorRepository

logger = logging.getLogger(__name__)

class AIReportService:
    def __init__(self, db: Session):
        self.db = db
        self.asset_repo = AssetRepository(db)
        self.market_data_repo = MarketDataRepository(db)
        self.indicator_repo = IndicatorRepository(db)

    def generate_market_summary(self, asset: Asset, data: MarketData, ind: Indicator) -> str:
        """Generates a structured, rule-based summary for a single asset."""
        # 1. Close status
        direction = "higher" if data.change_percent >= 0 else "lower"
        summary = f"{asset.symbol} closed {abs(data.change_percent):.2f}% {direction} today at {data.close:,.2f}. "

        # 2. RSI status
        if ind.rsi is not None:
            if ind.rsi >= 70:
                rsi_desc = "indicating overbought conditions"
            elif ind.rsi <= 30:
                rsi_desc = "indicating oversold conditions"
            elif ind.rsi >= 55:
                rsi_desc = "indicating strong bullish momentum"
            elif ind.rsi <= 45:
                rsi_desc = "indicating bearish momentum"
            else:
                rsi_desc = "indicating neutral momentum"
            summary += f"RSI is at {ind.rsi:.1f} {rsi_desc}. "

        # 3. SMA 50 structure
        if ind.sma50 is not None:
            above_below = "above" if data.close >= ind.sma50 else "below"
            structure = "bullish" if data.close >= ind.sma50 else "bearish"
            summary += f"Price remains {above_below} the 50-day moving average suggesting {structure} structure. "

        # 4. Support and Resistance
        if ind.support is not None and ind.resistance is not None:
            summary += f"Immediate resistance lies near {ind.resistance:,.2f} while support remains around {ind.support:,.2f}."

        return summary

    def get_all_summaries(self) -> Dict[str, str]:
        """Fetches latest data and returns generated rule-based summaries for all assets."""
        assets = self.asset_repo.list()
        summaries = {}
        
        for asset in assets:
            data = self.market_data_repo.get_latest_for_asset(asset.id)
            ind = self.indicator_repo.get_latest_for_asset(asset.id)
            
            if data and ind:
                summaries[asset.symbol] = self.generate_market_summary(asset, data, ind)
            else:
                summaries[asset.symbol] = f"No complete data available for {asset.symbol}."
        
        return summaries

    def generate_daily_report(self, report_date: date) -> str:
        """
        Gathers raw data and technical summaries, prompts Groq to compile the Markdown report.
        If GROQ_API_KEY is not configured, it generates a fallback mock report.
        """
        assets = self.asset_repo.list()
        context_data = []
        rule_based_summaries = []

        for asset in assets:
            data = self.market_data_repo.get_latest_for_asset(asset.id)
            ind = self.indicator_repo.get_latest_for_asset(asset.id)
            
            if data and ind:
                summary_text = self.generate_market_summary(asset, data, ind)
                rule_based_summaries.append(f"**{asset.symbol}**: {summary_text}")
                context_data.append({
                    "symbol": asset.symbol,
                    "type": asset.asset_type,
                    "close": data.close,
                    "open": data.open,
                    "high": data.high,
                    "low": data.low,
                    "volume": data.volume,
                    "change_percent": data.change_percent,
                    "sma20": ind.sma20,
                    "sma50": ind.sma50,
                    "sma200": ind.sma200,
                    "rsi": ind.rsi,
                    "macd": ind.macd,
                    "bollinger_upper": ind.bollinger_upper,
                    "bollinger_lower": ind.bollinger_lower,
                    "support": ind.support,
                    "resistance": ind.resistance
                })

        if not context_data:
            raise ValueError("No database data found to generate report. Make sure to fetch market data first.")

        # Build prompt
        summaries_input = "\n".join(rule_based_summaries)
        details_input = str(context_data)
        
        prompt = f"""
You are a senior financial analyst and portfolio manager. Generate a professional Daily Market Intelligence Report for {report_date}.

Below is the technical analysis summary for the tracked assets:
{summaries_input}

Below is the complete dataset including technical indicators (SMA, RSI, MACD, Bollinger Bands, Support/Resistance):
{details_input}

Format the report in clean Markdown. The report must contain exactly the following sections:
1. Executive Summary
2. NIFTY Analysis (referencing ticker ^NSEI)
3. BANKNIFTY Analysis (referencing ticker ^NSEBANK)
4. Gold Analysis (referencing ticker GC=F)
5. Silver Analysis (referencing ticker SI=F)
6. Bitcoin Analysis (referencing ticker BTC-USD)
7. Ethereum Analysis (referencing ticker ETH-USD)
8. Risk Factors
9. Trading Opportunities
10. Tomorrow Outlook

Make the report detailed, professional, and full of insights. Incorporate specific price targets, support/resistance lines, momentum observations (e.g. RSI, MACD), and volatility indicators (Bollinger Bands) in the sections. Do not use generic placeholders.
"""

        # Groq Call or Fallback
        if settings.groq_key:
            try:
                logger.info("Connecting to Groq API to generate report...")
                client = Groq(api_key=settings.groq_key)
                completion = client.chat.completions.create(
                    model="llama3-70b-8192",
                    messages=[
                        {"role": "system", "content": "You are an expert market strategist generating highly insightful market intelligence reports."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,
                    max_tokens=4000
                )
                report_content = completion.choices[0].message.content
                logger.info("Successfully generated report using Groq.")
                return report_content
            except Exception as e:
                logger.error(f"Error calling Groq API: {e}. Falling back to programmatically generated report.")
                # fall through to fallback

        # Fallback Mock Report
        logger.info("Generating fallback Markdown report programmatically...")
        return self._generate_mock_report(report_date, context_data)

    def _generate_mock_report(self, report_date: date, context_data: list) -> str:
        """Helper to build a beautiful mock report using the real values from the database."""
        asset_map = {item["symbol"]: item for item in context_data}
        
        def asset_section(symbol: str, name: str) -> str:
            item = asset_map.get(symbol)
            if not item:
                return f"### {name} ({symbol})\nData not available for this period."
            
            trend = "bullish" if item["close"] >= (item["sma50"] or 0) else "bearish"
            rsi_val = f"{item['rsi']:.1f}" if item["rsi"] else "N/A"
            change_dir = "gained" if item["change_percent"] >= 0 else "lost"
            
            return f"""### {name} ({symbol})
- **Closing Price**: {item['close']:,.2f} ({item['change_percent']:.2f}% daily change)
- **Daily Range**: Low: {item['low']:,.2f} | High: {item['high']:,.2f}
- **Moving Averages**: SMA(20): {item['sma20']:,.2f} | SMA(50): {item['sma50']:,.2f} | SMA(200): {item['sma200']:,.2f}
- **Momentum & Volatility**: RSI(14): {rsi_val} | MACD: {item['macd']:.4f} | Bollinger Upper: {item['bollinger_upper']:,.2f} | Bollinger Lower: {item['bollinger_lower']:,.2f}
- **Key Levels**: Support: {item['support']:,.2f} | Resistance: {item['resistance']:,.2f}

**Analysis**:
The asset is currently trading in a **{trend}** structure as the closing price remains above/below key averages. The daily change indicates that buyers/sellers have {change_dir} control. RSI at {rsi_val} indicates momentum is sustainable without immediate overbought or oversold extremes. Key resistance sits at {item['resistance']:,.2f}, representing a local ceiling. A breakout above this level would confirm additional upside target, while immediate defense is anchored at support {item['support']:,.2f}."""

        nifty_sec = asset_section("^NSEI", "NIFTY 50")
        banknifty_sec = asset_section("^NSEBANK", "BANKNIFTY")
        gold_sec = asset_section("GC=F", "Gold Futures")
        silver_sec = asset_section("SI=F", "Silver Futures")
        btc_sec = asset_section("BTC-USD", "Bitcoin")
        eth_sec = asset_section("ETH-USD", "Ethereum")

        report = f"""# Daily Market Intelligence Report - {report_date}

## 1. Executive Summary
On {report_date}, global financial markets showed mixed momentum. Equity markets moved within established bands, while crypto assets registered localized volatility. Commodities (Gold and Silver) continued their behavior as safe-haven buffers. Overall market sentiment remains cautious but structured around key moving averages.

## 2. NIFTY Analysis
{nifty_sec}

## 3. BANKNIFTY Analysis
{banknifty_sec}

## 4. Gold Analysis
{gold_sec}

## 5. Silver Analysis
{silver_sec}

## 6. Bitcoin Analysis
{btc_sec}

## 7. Ethereum Analysis
{eth_sec}

## 8. Risk Factors
- **Interest Rate Uncertainty**: Central bank commentaries continue to inject volatility into global bond yields, impacting growth assets like tech and cryptocurrencies.
- **Geopolitical Backdrops**: Regional tensions could disrupt commodity supplies, particularly gold and silver pricing.
- **Overextended Crypto Momentum**: Crypto RSI values show rapid spikes, presenting a near-term pullback risk if key supports are broken.

## 9. Trading Opportunities
- **NIFTY Breakout Play**: Monitor NIFTY close to the resistance levels for potential momentum extension.
- **Gold Range Trade**: Accumulate Gold near support levels with strict stop losses below the 50-day moving average.
- **Bitcoin Consolidation**: Cryptocurrencies are showing healthy pullbacks near the 20-day SMA, presenting accumulation entries.

## 10. Tomorrow Outlook
We anticipate a consolidation bias in the indices ahead of upcoming macroeconomic indicators. Crypto and commodities are expected to trade in tight channels. Key pivot support levels must be defended by the bulls to retain overall positive structures.
"""
        return report
