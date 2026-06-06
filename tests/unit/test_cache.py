import os
import time
from zakatable import cache

def test_cache_set_and_get():
    ticker = "TSET"
    test_payload = {"name": "Test Company", "value": 123}
    
    # Assert cache is empty on start
    assert cache.get_cached_data(ticker) is None
    
    # Write to cache
    cache.set_cached_data(ticker, test_payload)
    
    # Verify file is physically created in isolated temp CACHE_DIR
    cache_file_path = os.path.join(cache.CACHE_DIR, f"{ticker}.json")
    assert os.path.exists(cache_file_path)
    
    # Retrieve from cache
    cached_res = cache.get_cached_data(ticker)
    assert cached_res is not None
    assert cached_res["data"]["name"] == "Test Company"
    assert cached_res["data"]["value"] == 123

def test_cache_expiration():
    ticker = "EXP"
    test_payload = {"name": "Expired Company"}
    
    # Set cache
    cache.set_cached_data(ticker, test_payload)
    
    # Retrieve immediately with positive expiry (should pass)
    assert cache.get_cached_data(ticker, expiry_seconds=10) is not None
    
    # Retrieve with negative expiry (should fail / return None)
    assert cache.get_cached_data(ticker, expiry_seconds=-1) is None

def test_cache_clear_specific():
    ticker1 = "T1"
    ticker2 = "T2"
    
    cache.set_cached_data(ticker1, {"id": 1})
    cache.set_cached_data(ticker2, {"id": 2})
    
    assert cache.get_cached_data(ticker1) is not None
    assert cache.get_cached_data(ticker2) is not None
    
    # Clear only T1
    cache.clear_cache(ticker1)
    
    assert cache.get_cached_data(ticker1) is None
    assert cache.get_cached_data(ticker2) is not None

def test_cache_clear_all():
    ticker1 = "T1"
    ticker2 = "T2"
    
    cache.set_cached_data(ticker1, {"id": 1})
    cache.set_cached_data(ticker2, {"id": 2})
    
    assert cache.get_cached_data(ticker1) is not None
    assert cache.get_cached_data(ticker2) is not None
    
    # Clear all
    cache.clear_cache()
    
    assert cache.get_cached_data(ticker1) is None
    assert cache.get_cached_data(ticker2) is None
