from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional

try:
    import zxingcpp
    print("DEBUG: zxingcpp imported successfully")
except ImportError:
    zxingcpp = None
    print("WARNING: zxingcpp import failed. QR decoding will not work.")

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
        Reads an image (supports JPG, PNG, HEIC) and decodes JRA QR codes using zxing-cpp.
        Handles multiple tickets in one image by clustering QR codes.
        """
        try:
            print(f"DEBUG: decode_ticket called for {image_path}")
            check_image_stat(image_path)
            
            register_heif_opener()
            pil_img = Image.open(image_path)
            
            # Ensure image is in a mode compatible with zxing-cpp (usually RGB or L)
            if pil_img.mode not in ('RGB', 'L'):
                pil_img = pil_img.convert('RGB')
            
            if zxingcpp:
                # zxing-cpp can read PIL images directly or numpy arrays
                decoded_objects = zxingcpp.read_barcodes(pil_img)
                print(f"DEBUG: zxingcpp returned {len(decoded_objects)} objects")
            else:
                print("DEBUG: zxingcpp missing")
                return []

            if not decoded_objects:
                print("DEBUG: No QR codes found in image.")
                return []

            # 1. Extract data and bounding boxes
            from collections import namedtuple
            Rect = namedtuple('Rect', ['left', 'top', 'width', 'height'])

            qr_items = []
            
            for obj in decoded_objects:
                try:
                    # zxing-cpp obj has .text (string) and .position (object with point attributes)
                    p = obj.position
                    
                    # Robust way: Try attributes first, fallback to dummy
                    try:
                        # Standard zxing-cpp point attributes
                        min_x = min(p.top_left.x, p.bottom_left.x)
                        min_y = min(p.top_left.y, p.top_right.y)
                        max_x = max(p.top_right.x, p.bottom_right.x)
                        max_y = max(p.bottom_left.y, p.bottom_right.y)
                        
                        width = max_x - min_x
                        height = max_y - min_y
                    except AttributeError:
                        # Fallback for weird versions or if position is not point object
                        # If we assume JRA QRs are split horizontally side-by-side or vertically stacked.
                        # Since we can't get precise position, let's assume they are returned in reading order?
                        # zxing-cpp usually returns them in found order.
                        # Let's give dummy increasing Y to keep order if sort is used.
                        current_len = len(qr_items)
                        min_x, min_y, width, height = 0, current_len * 100, 100, 100
                        
                    qr_items.append({
                        'data': obj.text,
                        'rect': Rect(min_x, min_y, width, height)
                    })
                except Exception as e:
                    print(f"WARNING: Error processing QR object: {e}")
                    continue

            if not qr_items:
                return []

            # 2. Cluster logic (Sort Top-Down then Left-Right)
            # JRA tickets usually have 2 QRs side-by-side.
            # If side-by-side, they will have similar top/height.
            
            qr_items.sort(key=lambda x: x['rect'].top)
            
            rows = []
            if qr_items:
                current_row = [qr_items[0]]
                for i in range(1, len(qr_items)):
                    prev = current_row[-1]
                    curr = qr_items[i]
                    
                    # Vertical separation threshold
                    prev_cy = prev['rect'].top + prev['rect'].height/2
                    curr_cy = curr['rect'].top + curr['rect'].height/2
                    h_avg = (prev['rect'].height + curr['rect'].height) / 2
                    
                    if abs(prev_cy - curr_cy) < h_avg * 0.5:
                        # Same row
                        current_row.append(curr)
                    else:
                        # New row
                        rows.append(current_row)
                        current_row = [curr]
                rows.append(current_row)

            tickets = []
            for row in rows:
                # Sort Left-Right
                row.sort(key=lambda x: x['rect'].left)
                full_qr_data = "".join([item['data'] for item in row])
                print(f"DEBUG: Parsed QR data length: {len(full_qr_data)}")
                
                # Parse
                ticket = JRAParser.parse(full_qr_data)
                tickets.append(ticket)
            
            return tickets

        except Exception as e:
            print(f"Error process image: {e}")
            return []
