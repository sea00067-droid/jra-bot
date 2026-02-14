from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional

try:
    from pyzbar.pyzbar import decode
    print("DEBUG: pyzbar imported successfully")
except Exception as e:
    decode = None
    print(f"ERROR: pyzbar import failed: {e}")
from PIL import Image
from pillow_heif import register_heif_opener
import numpy as np

# DEBUG: Image loading check
def check_image_stat(path):
    try:
        register_heif_opener()
        img = Image.open(path)
        print(f"DEBUG: Image opened - Size: {img.size}, Mode: {img.mode}")
        return True
    except Exception as e:
        print(f"DEBUG: Image open failed: {e}")
        return False

@dataclass
class TicketData:
    place_code: str
    race_num: int
    bet_type: str # 単勝, 複勝, etc.
    buy_details: str # 1-2, 3-4-5 etc.
    amount: int
    raw_qr_data: str

class JRAParser:
    """
    Parses the combined 190-digit JRA QR code data.
    Ported from: https://github.com/strangerxxxx/horceracing_ticket_qr_reader/blob/main/lib/parse.dart
    """
    PLACE_MAP = {
        "01": "札幌", "02": "函館", "03": "福島", "04": "新潟",
        "05": "東京", "06": "中山", "07": "中京", "08": "京都",
        "09": "阪神", "10": "小倉"
    }
    
    # Dart code suggests type fits in a specific substring
    BET_TYPE_MAP = {
        "1": "単勝", "2": "複勝", "3": "枠連", "5": "馬連",
        "6": "馬単", "7": "ワイド", "8": "3連複", "9": "3連単"
    }

    @staticmethod
    def parse(raw_data: str) -> TicketData:
        # Expected format: 190 digits (Concat of two 95-digit QRs)
        # Based on Dart implementation:
        # iter.next() usually consumes 1 char unless specified
        
        # Raw string iterator simulation
        pos = 0
        def next_chars(n=1):
            nonlocal pos
            ret = raw_data[pos:pos+n]
            pos += n
            return ret
        
        try:
            # 1. Format Version? (1 digit)
            ticket_format = next_chars(1)
            
            # 2. Place Code (2 digits)
            place_code_key = next_chars(2)
            place_name = JRAParser.PLACE_MAP.get(place_code_key, "Unknown")
            
            # 3. Skip 2 digits (padding?)
            next_chars(2)
            
            # 4. Alternative Type (1 digit) - e.g. "0"
            alt_code = next_chars(1)
            
            # 5. Date & Race Info
            year_short = next_chars(2) # e.g. "23" for 2023
            kai = next_chars(2)      # "05" (5th meeting)
            day = next_chars(2)      # "05" (5th day)
            race_num = int(next_chars(2)) # "11"
            
            # 6. Bet Type (1 digit)
            bet_type_key = next_chars(1)
            bet_type_name = JRAParser.BET_TYPE_MAP.get(bet_type_key, "Unknown")
            
            # 7. Skipping unknown/fixed/buy details for now
            # Dart Code consumes specific chunks for "underDigits" but DOES NOT full parse buy details (combinations).
            # It constructs a URL for Netkeiba using date/place/race.
            
            # To extract amount or combinations, we need more advanced logic not present in the reference Dart file.
            # The reference mainly extracts Metadata to build a Netkeiba URL.
            
            # For this prototype, we will stick to what's reliably extracted:
            # Place, Race, BetType, Date.
            
            # Amount and Combinations are seemingly encrypted/packed in the remaining digits.
            # We will use placeholder or look for patterns in future.
            
            amount = 0 # Cannot verify amount parsing from the provided Dart code
            buy_details = "Parsed from QR" 

            return TicketData(
                place_code=place_name,
                race_num=race_num,
                bet_type=bet_type_name,
                buy_details=buy_details,
                amount=amount,
                raw_qr_data=raw_data
            )

        except Exception as e:
            print(f"JRA Parse Error: {e}")
            return TicketData("Error", 0, "Error", "ParseFailed", 0, raw_data)

class QRReader:
    def __init__(self):
        pass

    def decode_ticket(self, image_path: str) -> List[TicketData]:
        """
        Reads an image (supports JPG, PNG, HEIC) and decodes JRA QR codes.
        Handles multiple tickets in one image by clustering QR codes.
        """
        try:
            print(f"DEBUG: decode_ticket called for {image_path}")
            check_image_stat(image_path)
            
            register_heif_opener()
            pil_img = Image.open(image_path)
            
            if decode is None:
                print("DEBUG: decode function is None (pyzbar missing)")
                return []
                
            decoded_objects = decode(pil_img)
            print(f"DEBUG: decode returned {len(decoded_objects)} objects")
            
            if not decoded_objects:
                print("DEBUG: No QR codes found in image.")
                return []

            # 1. Extract data and bounding boxes
            qr_items = []
            for obj in decoded_objects:
                qr_items.append({
                    'data': obj.data.decode("utf-8"),
                    'rect': obj.rect
                })

            # 2. Cluster logic (Sort Top-Down then Left-Right)
            qr_items.sort(key=lambda x: x['rect'].top)
            
            rows = []
            current_row = []
            if qr_items:
                current_row.append(qr_items[0])
                for i in range(1, len(qr_items)):
                    prev = current_row[-1]
                    curr = qr_items[i]
                    # Threshold: Center Y difference < 50% of avg height
                    prev_cy = prev['rect'].top + prev['rect'].height/2
                    curr_cy = curr['rect'].top + curr['rect'].height/2
                    h_avg = (prev['rect'].height + curr['rect'].height) / 2
                    
                    if abs(prev_cy - curr_cy) < h_avg * 0.5:
                        current_row.append(curr)
                    else:
                        rows.append(current_row)
                        current_row = [curr]
                rows.append(current_row)

            tickets = []
            for row in rows:
                # Sort Left-Right to concatenate correctly
                row.sort(key=lambda x: x['rect'].left)
                full_qr_data = "".join([item['data'] for item in row])
                
                # Parse
                ticket = JRAParser.parse(full_qr_data)
                tickets.append(ticket)
            
            return tickets

        except Exception as e:
            print(f"Error process image: {e}")
            return []
