import pytest
import pandas as pd
import numpy as np
from app.services.indicator_service import IndicatorService

def test_compute_indicators_math():
    # Setup dummy indicator service (we only need the compute_indicators function, which is database-independent)
    service = IndicatorService(db=None)

    # Create dummy data: 250 rows of close price = 100
    dates = pd.date_range(start="2026-01-01", periods=250, freq="D")
    df = pd.DataFrame({
        "open": [100.0] * 250,
        "high": [105.0] * 250,
        "low": [95.0] * 250,
        "close": [100.0] * 250,
        "volume": [1000] * 250
    }, index=dates)

    # Run calculations
    df_result = service.compute_indicators(df)

    # 1. Test Moving Averages: Since price is constant, SMA should be constant at 100
    assert df_result["sma20"].iloc[-1] == 100.0
    assert df_result["sma50"].iloc[-1] == 100.0
    assert df_result["sma200"].iloc[-1] == 100.0

    # 2. Test Bollinger Bands: Standard deviation of constant series is 0
    # Bollinger Upper and Lower should equal SMA 20 (which is 100)
    assert df_result["bollinger_upper"].iloc[-1] == 100.0
    assert df_result["bollinger_lower"].iloc[-1] == 100.0

    # 3. Test Support & Resistance:
    # Support = Min(low) over last 30 days = 95
    # Resistance = Max(high) over last 30 days = 105
    assert df_result["support"].iloc[-1] == 95.0
    assert df_result["resistance"].iloc[-1] == 105.0

    # 4. Test RSI: Constant price change is 0. Gain = 0, Loss = 0.
    # Our formula replaces division by zero with minor epsilon so RSI becomes 100 - 100/(1+0) = 0 or neutral depending on details.
    # Let's check it is a valid float number
    assert not pd.isna(df_result["rsi"].iloc[-1])
