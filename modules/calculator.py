import os
from sqlalchemy import create_engine, Column, Integer, String, Date, select
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, date
import pandas as pd
from typing import List, Tuple

Base = declarative_base()

class Bet(Base):
    __tablename__ = 'bets'
    id = Column(Integer, primary_key=True)
    date = Column(Date)
    place = Column(String)
    race_num = Column(Integer)
    bet_type = Column(String)
    buy_details = Column(String)
    amount = Column(Integer)
    payout = Column(Integer, default=0)
    result = Column(String, default="未") # 未, 的中, ハズレ

class Calculator:
    def __init__(self, db_url: str = None):
        # Use DATABASE_URL env var or default to local sqlite
        if db_url is None:
            db_url = os.environ.get("DATABASE_URL", "sqlite:///data/jra_bot.db")
        
        # Determine strictness for sqlite vs postgres
        if db_url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
        else:
            connect_args = {}
            
        self.engine = create_engine(db_url, connect_args=connect_args)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def add_bet(self, bet_date_str: str, place: str, race_num: int, bet_type: str, buy_details: str, amount: int):
        session = self.Session()
        try:
            # Date format expected: YYYYMMDD in older code, but let's standardize or handle both
            try:
                dt = datetime.strptime(bet_date_str, "%Y%m%d").date()
            except ValueError:
                # Fallback or try hyphenated
                try:
                    dt = datetime.strptime(bet_date_str, "%Y-%m-%d").date()
                except:
                    dt = date.today()

            bet = Bet(
                date=dt,
                place=place,
                race_num=race_num,
                bet_type=bet_type,
                buy_details=buy_details,
                amount=amount
            )
            session.add(bet)
            session.commit()
            print(f"Bet added: {bet_date_str} {place}{race_num}R")
        except Exception as e:
            session.rollback()
            print(f"Error adding bet: {e}")
        finally:
            session.close()

    def update_result(self, bet_id: int, payout: int):
        session = self.Session()
        try:
            bet = session.get(Bet, bet_id)
            if bet:
                bet.payout = payout
                bet.result = "的中" if payout > 0 else "ハズレ"
                session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error updating result: {e}")
        finally:
            session.close()

    def get_monthly_summary(self, year: int, month: int):
        """Returns dict with total_bet, total_return, balance"""
        session = self.Session()
        try:
            from sqlalchemy import extract
            stmt = select(Bet).where(
                extract('year', Bet.date) == year,
                extract('month', Bet.date) == month
            )
            bets = session.execute(stmt).scalars().all()
            
            total_bet = sum(b.amount for b in bets)
            total_return = sum(b.payout for b in bets)
            return {
                "total_bet": total_bet,
                "total_return": total_return,
                "balance": total_return - total_bet
            }
        finally:
            session.close()

    def get_all_bets_for_month(self, year: int, month: int) -> pd.DataFrame:
        session = self.Session()
        try:
            from sqlalchemy import extract
            stmt = select(Bet).where(
                extract('year', Bet.date) == year,
                extract('month', Bet.date) == month
            ).order_by(Bet.date)
            
            bets = session.execute(stmt).scalars().all()
            
            data = []
            for b in bets:
                data.append({
                    "date": b.date,
                    "amount": b.amount,
                    "payout": b.payout
                })
            
            if not data:
                return pd.DataFrame(columns=["date", "amount", "payout"])
                
            return pd.DataFrame(data)
        finally:
            session.close()

if __name__ == "__main__":
    calc = Calculator()
    calc.add_bet("2023-10-29", "Tokyo", 11, "WIN", "1", 1000)
    print(calc.get_monthly_summary(2023, 10))
