import requests
import yfinance as yf

# Shared requests session with standard browser User-Agent to bypass Yahoo Finance datacenter blocks
_SESSION = None

def get_yf_ticker(symbol: str) -> yf.Ticker:
    """
    Returns a yfinance.Ticker object initialized with a shared browser session.
    """
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
        _SESSION.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    return yf.Ticker(symbol, session=_SESSION)
