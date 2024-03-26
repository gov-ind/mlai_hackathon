"""
Crawlers that crawl opennem's API forever in intervals and writes to a DB.
"""
from datetime import datetime
import os
from threading import Thread
from time import sleep

import pandas as pd
import requests

from energy_db import EnergyDB, TIMESTAMP_COL

DEFAULT_SOURCE_INTERVAL = 5
DEFAULT_REGION = 'SA1'
DEFAULT_URL = f'https://api.opennem.org.au/stats/price/network/NEM/{DEFAULT_REGION}'

def get_file_path(network: str='NEM', region: str=DEFAULT_REGION):
    return f"bot/data/{network}_{region}_test_data.csv"

def get_data(url: str, source_interval: int=DEFAULT_SOURCE_INTERVAL):
    response = requests.get(url).json()
    history = response["data"][0]["history"]
    start_time = datetime.fromisoformat(history["start"])
    end_time = datetime.fromisoformat(history["last"])
    time_range = pd.date_range(start=start_time, end=end_time, freq=f"{source_interval}min")

    return pd.DataFrame({ TIMESTAMP_COL: time_range, "price": history["data"] })

class Crawler:
    def __init__(
        self,
        db,
        url: str=DEFAULT_URL,
        crawl_interval: int=15,
        source_interval: int=DEFAULT_SOURCE_INTERVAL
    ):
        self.db = db
        self.url = url
        self.crawl_interval = crawl_interval
        self.source_interval = source_interval
    
    def get_data(self, url: str, source_interval: int):
        return get_data(url, source_interval)
    
    def crawl_forever(self):
        Thread(target=self._crawl_forever, daemon=False).start()
    
    def _crawl_forever(self):
        while True:
            print(f"Crawling at {datetime.now()}")

            num_records_added = self.crawl()

            print(f"Discovered {num_records_added} new timestamps")
            sleep(self.crawl_interval * 60)
    
    def crawl(self):
        data = self.get_data(self.url, self.source_interval)
        return self.db.save_new_data(data)

if __name__ == "__main__":
    source = DEFAULT_URL.split('https://api.opennem.org.au/stats/price/network/')[1]
    network, region = source.split('/')
    
    file_path = get_file_path(network, region)
    if not os.path.exists(file_path):
        pd.DataFrame({ TIMESTAMP_COL: [], "price": [] }).to_csv(file_path, index=False)

    db = EnergyDB(file_location=file_path)
    crawler = Crawler(db=db)
    crawler.crawl_forever()