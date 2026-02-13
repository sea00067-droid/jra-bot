import requests
from bs4 import BeautifulSoup
import re
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class RaceResult:
    bet_type: str # 単勝, 複勝, etc.
    combinations: List[str] # [1], [1, 2]
    payouts: List[int] # [250], [110, 140]

class NetkeibaScraper:
    def __init__(self):
        self.headers = {
             "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        # Place codes mapping (Netkeiba specific)
        self.place_map = {
            "札幌": "01", "函館": "02", "福島": "03", "新潟": "04",
            "東京": "05", "中山": "06", "中京": "07", "京都": "08",
            "阪神": "09", "小倉": "10"
        }

    def _get_soup(self, url):
        res = requests.get(url, headers=self.headers)
        res.encoding = 'EUC-JP'
        return BeautifulSoup(res.content, 'html.parser')

    def find_race_id(self, date_str: str, place_name: str, race_num: int) -> str:
        """
        Find race ID from date, place name (kanji), and race number.
        date_str: YYYYMMDD
        place_name: "東京", "中山" etc.
        """
        url = f"https://db.netkeiba.com/race/list/{date_str}/"
        soup = self._get_soup(url)
        
        # This is a bit heuristic. Netkeiba lists usually have structure.
        # Simplest is to find a link that contains the race num and looks like a race link,
        # and check if it belongs to the correct place section.
        # For robustness, we might need to parse the specific section.
        
        # Searching for race link usually found as /race/YYYYPPKKDDRR
        # PP is place code.
        place_code = self.place_map.get(place_name)
        if not place_code:
            return None
            
        target_suffix = f"{race_num:02d}"
        
        links = soup.find_all('a', href=re.compile(r"/race/\d{12}"))
        for link in links:
            href = link.get('href')
            race_id = href.split('/')[2]
            
            # Check place code (digits 5-6) and race num (digits 11-12)
            # Race ID: YYYY PP KK DD RR
            r_place = race_id[4:6]
            r_num = race_id[10:12]
            
            if r_place == place_code and r_num == target_suffix:
                return race_id
                
        return None

    def get_payout(self, race_id: str) -> List[RaceResult]:
        url = f"https://db.netkeiba.com/race/{race_id}/"
        soup = self._get_soup(url)
        
        results = []
        
        # Payout tables
        # Usually found in <dl class="pay_block"> or <table class="pay_table_01">
        tables = soup.find_all('table', class_='pay_table_01')
        
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                th = row.find('th')
                if not th: continue
                bet_type = th.text.strip()
                
                tds = row.find_all('td')
                if len(tds) < 2: continue
                
                # Extract combinations and payouts
                # They are separated by <br> tags
                combinations_raw = tds[0].decode_contents()
                payouts_raw = tds[1].decode_contents()
                
                # Split by <br> or <br/>
                combs_list = re.split(r'<br\s*/?>', combinations_raw)
                pays_list = re.split(r'<br\s*/?>', payouts_raw)
                
                # Clean up extracted strings
                clean_combs = []
                for c in combs_list:
                    # Remove HTML tags if any left (e.g. formatting) and whitespace
                    text = BeautifulSoup(c, 'html.parser').text.strip()
                    if text:
                        clean_combs.append(text)
                        
                clean_pays = []
                for p in pays_list:
                    text = BeautifulSoup(p, 'html.parser').text.strip()
                    if text:
                        try:
                            clean_pays.append(int(text.replace(',', '')))
                        except:
                            pass
                            
                results.append(RaceResult(bet_type, clean_combs, clean_pays))
                
        return results

if __name__ == "__main__":
    scraper = NetkeibaScraper()
    # Test: Japan Cup 2023 (2023-11-26, Tokyo 12R)
    rid = scraper.find_race_id("20231126", "東京", 12)
    print(f"Race ID: {rid}")
    if rid:
        payouts = scraper.get_payout(rid)
        for p in payouts:
            print(p)
