import os
import json
import time
from typing import Optional, Any, Dict

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".cache")
DEFAULT_EXPIRY_SECONDS = 86400  # 24 hours

# Ensure cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)

def _get_cache_path(ticker: str) -> str:
    # Normalize ticker to uppercase and clean up for filenames
    safe_ticker = "".join([c for c in ticker.upper() if c.isalnum() or c in ("-", "_", ".")])
    return os.path.join(CACHE_DIR, f"{safe_ticker}.json")

def get_cached_data(ticker: str, expiry_seconds: int = DEFAULT_EXPIRY_SECONDS) -> Optional[Dict[str, Any]]:
    """
    Retrieve cached data for a ticker if it exists and has not expired.
    """
    cache_path = _get_cache_path(ticker)
    if not os.path.exists(cache_path):
        return None
    
    try:
        # Check modification time
        mtime = os.path.getmtime(cache_path)
        age = time.time() - mtime
        if age > expiry_seconds:
            return None
        
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        # If cache read fails, treat as cache miss
        print(f"Warning: Failed to read cache for {ticker}: {e}")
        return None

def set_cached_data(ticker: str, data: Dict[str, Any]) -> None:
    """
    Save ticker data to the local cache.
    """
    cache_path = _get_cache_path(ticker)
    try:
        # Include metadata
        payload = {
            "cached_at": time.time(),
            "data": data
        }
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)
    except Exception as e:
        print(f"Warning: Failed to write cache for {ticker}: {e}")

def clear_cache(ticker: Optional[str] = None) -> None:
    """
    Clear cache for a specific ticker, or all cache if ticker is None.
    """
    if ticker:
        cache_path = _get_cache_path(ticker)
        if os.path.exists(cache_path):
            try:
                os.remove(cache_path)
            except Exception as e:
                print(f"Warning: Failed to delete cache file {cache_path}: {e}")
    else:
        for filename in os.listdir(CACHE_DIR):
            if filename.endswith(".json"):
                try:
                    os.remove(os.path.join(CACHE_DIR, filename))
                except Exception as e:
                    print(f"Warning: Failed to delete cache file {filename}: {e}")
