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
            # Helper to shim Rect interface
            from collections import namedtuple
            Rect = namedtuple('Rect', ['left', 'top', 'width', 'height'])

            qr_items = []
            for obj in decoded_objects:
                # obj.position gives coordinates. Usually TopLeft, TopRight, BottomRight, BottomLeft
                # We need bounding box
                try:
                    p = obj.position
                    # zxing-cpp position is a string or an object with x,y?
                    # Depending on version. Let's assume standard object with x,y properties 
                    # OR check what it returns. 
                    # Wait, zxing-cpp returns `position` as a specific object.
                    # It has `top_left`, `top_right` etc.
                    # Actually, simple way: obj.position -> capturing localized coordinates
                    
                    # Convert position points to rect
                    # Assuming obj.position is convertible to string or has attributes.
                    # Let's inspect via string representation or assume standard bounding box logic if lacking documentation in this context.
                    # Actually, let's use a simpler approach. zxing-cpp usually robustly gives content.
                    # Clustering logic relies on 'rect'.
                    # Let's deduce rect from position.
                    
                    # zxing-cpp binding usually exposes `position` as a specialized Point object
                    # We will try to parse it. 
                    
                    # Hack: For clustering JRA tickets (usually stacked), Y-coordinate is key.
                    # Let's try to get Y from position.
                    # If obj.position is complex, we might fail here.
                    
                    # Let's print obj to debug log just in case
                    print(f"DEBUG: QR object: {obj.text} at {obj.position}")

                    # Approximation: Use dummy rect if position parsing is hard, BUT clustering relies on it.
                    # Let's try to extract basic coords.
                    # obj.position usually has `top_left`, `top_right`...
                    
                    # Simple fallback: if only 1 QR found, rect doesn't matter much.
                    # But JRA has 2 concatenated QRs. They are side-by-side or stacked?
                    # Usually side-by-side.
                    
                    # Let's try to access obj.position.top_left.y etc.
                    # If that fails, assume it's just text.
                    
                    # Simplified logic for now: Treat all found QRs as one row if clustering fails?
                    # No, JRA QRs are split. We NEED to combine them correctly.
                    
                    # Let's assume zxing-cpp `position` string looks like "Point(x,y) ..."
                    # Let's use a robust approach:
                    # zxing-cpp objects have `position` attribute which is a string representation in earlier versions,
                    # or an object in newer.
                    # Given Render environment, let's play safe.
                    
                    # We will create a pseudo-rect from the position string if needed, 
                    # OR just use the order they are returned? zxing-cpp might not guarantee order.
                    
                    # Let's TRY to access `top_left` etc.
                    p = obj.position
                    # The C++ binding typically returns a `Position` object with `top_left`, etc.
                    min_x = min(p.top_left.x, p.bottom_left.x)
                    min_y = min(p.top_left.y, p.top_right.y)
                    max_x = max(p.top_right.x, p.bottom_right.x)
                    max_y = max(p.bottom_left.y, p.bottom_right.y)
                    
                    qr_items.append({
                        'data': obj.text,
                        'rect': Rect(min_x, min_y, max_x - min_x, max_y - min_y)
                    })
                except Exception as pos_e:
                    print(f"WARNING: Could not determine position ({pos_e}), using dummy rect")
                    qr_items.append({
                        'data': obj.text,
                        'rect': Rect(0, 0, 100, 100) # Dummy
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
                print(f"DEBUG: Parsed QR data length: {len(full_qr_data)}")
                
                # Parse
                ticket = JRAParser.parse(full_qr_data)
                tickets.append(ticket)
            
            return tickets

        except Exception as e:
            print(f"Error process image: {e}")
            return []
