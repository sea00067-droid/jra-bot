from modules.qr_reader import JRAParser

def test_parser():
    # Construct a valid-looking 190-digit string based on the logic
    # 1: Format
    # 05: Tokyo
    # 00: Padding
    # 0: Alt
    # 23: Year (2023)
    # 05: Kai
    # 04: Day
    # 11: Race
    # 9: BetType (3-Ren-Tan)
    # Rest: Padding
    
    header = "105000230504119"
    padding = "0" * (190 - len(header))
    raw_data = header + padding
    
    print(f"Testing with raw data (len={len(raw_data)}): {raw_data[:20]}...")
    
    ticket = JRAParser.parse(raw_data)
    
    print("\n--- Parsed Ticket Data ---")
    print(f"Place: {ticket.place_code}")
    print(f"Race: {ticket.race_num}R")
    print(f"Bet Type: {ticket.bet_type}")
    print(f"Raw QR: {ticket.raw_qr_data[:20]}...")
    
    assert ticket.place_code == "東京"
    assert ticket.race_num == 11
    assert ticket.bet_type == "3連単"
    print("\nTest Passed!")

if __name__ == "__main__":
    test_parser()
