import matplotlib
matplotlib.use('Agg') # Use non-interactive backend
import matplotlib.pyplot as plt
import pandas as pd
from .calculator import Calculator
import os

class Reporter:
    def __init__(self, db_path="data/betting_log.db"):
        self.calculator = Calculator(db_path)

    def generate_monthly_chart(self, year: int, month: int, output_path: str = "data/chart.png") -> str:
        data = self.calculator.get_all_bets_for_month(year, month)
        if not data:
            return None
            
        df = pd.DataFrame(data, columns=['date', 'amount', 'payout', 'status'])
        df['date'] = pd.to_datetime(df['date'])
        
        # Group by date for daily summary
        daily_summary = df.groupby('date').sum(numeric_only=True).reset_index()
        daily_summary['balance'] = daily_summary['payout'] - daily_summary['amount']
        daily_summary['cumulative_balance'] = daily_summary['balance'].cumsum()

        plt.figure(figsize=(10, 6))
        plt.plot(daily_summary['date'], daily_summary['cumulative_balance'], marker='o', linestyle='-')
        plt.title(f"Cumulative Balance - {year}/{month:02d}")
        plt.xlabel("Date")
        plt.ylabel("Balance (Yen)")
        plt.grid(True)
        plt.tight_layout()
        
        plt.savefig(output_path)
        plt.close()
        
        return output_path

if __name__ == "__main__":
    # Test data generation (requires database populated)
    # reporter = Reporter()
    # reporter.generate_monthly_chart(2023, 10)
    pass
