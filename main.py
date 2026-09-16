
import requests
import pandas as pd
from datetime import datetime, timedelta

# NSE FII Data Fetcher
class FIIDataFetcher:
    def __init__(self):
        self.base_url = "https://www.nseindia.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def fetch_fii_data(self):
        """Fetch FII data from NSE"""
        try:
            # NSE FII DII data endpoint
            url = f"{self.base_url}/api/fiidii"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching FII data: {e}")
            return None
    
    def fetch_fii_historical(self, days=30):
        """Fetch historical FII data for specified days"""
        data = []
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            # Add your logic to fetch data for each date
            data.append({
                'date': date.strftime('%Y-%m-%d'),
                'fii_buy': 0,
                'fii_sell': 0,
                'net_fii': 0
            })
        return data
    
    def save_to_csv(self, data, filename='fii_data.csv'):
        """Save FII data to CSV"""
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False)
        print(f"Data saved to {filename}")

# Main execution
if __name__ == "__main__":
    fetcher = FIIDataFetcher()
    
    # Fetch current FII data
    fii_data = fetcher.fetch_fii_data()
    if fii_data:
        print("FII Data:", fii_data)
    
    # Fetch historical data
    historical = fetcher.fetch_fii_historical(days=30)
    fetcher.save_to_csv(historical)
