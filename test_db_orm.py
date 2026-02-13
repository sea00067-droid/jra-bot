from modules.calculator import Calculator
from datetime import datetime

def test_db():
    print("Initializing Calculator (SQLAlchemy)...")
    calc = Calculator("sqlite:///data/test_db.sqlite")
    
    print("Adding a bet...")
    calc.add_bet("20231224", "中山", 11, "単勝", "1", 1000)
    
    print("Checking summary...")
    summary = calc.get_monthly_summary(2023, 12)
    bet = summary["total_bet"]
    pay = summary["total_return"]
    bal = summary["balance"]
    print(f"Bet: {bet}, Pay: {pay}, Balance: {bal}")
    
    assert bet == 1000
    assert pay == 0
    assert bal == -1000
    
    print("Test Passed!")

if __name__ == "__main__":
    test_db()
