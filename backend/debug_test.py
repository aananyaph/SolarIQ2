"""
SolarIQ Backend Debug Test
Tests all endpoints for functionality
"""
import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://127.0.0.1:5000"

def test_health():
    """Test root health check"""
    print("\n[HEALTH] Testing Health Check...")
    resp = requests.get(f"{BASE_URL}/")
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}")
    return resp.status_code == 200

def test_history():
    """Test history endpoint"""
    print("\n[HISTORY] Testing /history...")
    resp = requests.get(f"{BASE_URL}/history")
    print(f"Status: {resp.status_code}")
    data = resp.json()
    print(f"Records: {len(data)}")
    if data:
        print(f"Sample: {json.dumps(data[0], indent=2)}")
    return resp.status_code == 200

def test_today_status():
    """Test today's status"""
    print("\n[TODAY] Testing /today_status...")
    resp = requests.get(f"{BASE_URL}/today_status")
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}")
    return resp.status_code == 200

def test_solar_status():
    """Test solar status with different categories"""
    print("\n[SOLAR] Testing /solar_status...")
    for cat in ["domestic", "institution", "industry"]:
        resp = requests.get(f"{BASE_URL}/solar_status?category={cat}&avg_power=3")
        print(f"Category {cat}: Status {resp.status_code}")
        if resp.status_code != 200:
            print(f"  Error: {resp.json()}")
    return True

def test_predict():
    """Test predict endpoint"""
    print("\n[PREDICT] Testing /predict (POST)...")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    next_week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    
    payload = {
        "start_date": tomorrow,
        "end_date": next_week
    }
    
    resp = requests.post(f"{BASE_URL}/predict", json=payload)
    print(f"Status: {resp.status_code}")
    data = resp.json()
    print(f"Response: {json.dumps({k: v[:2] if isinstance(v, list) else v for k, v in data.items()}, indent=2)}")
    return resp.status_code == 200

def test_nasa_data():
    """Test NASA data endpoint"""
    print("\n[NASA] Testing /nasa_data...")
    resp = requests.get(f"{BASE_URL}/nasa_data?lat=12.97&lon=77.59")
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Data points: {len(data.get('data', []))}")
    else:
        print(f"Error: {resp.json()}")
    return resp.status_code == 200

if __name__ == "__main__":
    print("SolarIQ Backend Debug Tests")
    print("=" * 50)
    
    try:
        # Run tests
        test_health()
        test_history()
        test_today_status()
        test_solar_status()
        test_predict()
        test_nasa_data()
        
        print("\n" + "=" * 50)
        print("All tests completed!")
        
    except requests.exceptions.ConnectionError:
        print("ERROR: Cannot connect to backend at", BASE_URL)
        print("Make sure Flask app is running: python run.py")
    except Exception as e:
        print(f"ERROR: {e}")
