import os
import sys
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, ImageMessage, ImageSendMessage
)
from modules.qr_reader import QRReader, JRAParser
from modules.jra_scraper import JRAScraper
from modules.calculator import Calculator
from modules.reporter import Reporter
import datetime
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

# Mount static files for LIFF
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return RedirectResponse(url="/static/scanner.html")

# LINE Bot credentials (should be loaded from env vars in prod)
# For local testing, these might be empty or placeholders
CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET', 'YOUR_CHANNEL_SECRET')
CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', 'YOUR_CHANNEL_ACCESS_TOKEN')

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# Initialize modules
# Initialize modules
qr_reader = QRReader()
scraper = JRAScraper()
calculator = Calculator() # Uses env var or default sqlite
reporter = Reporter(calculator)

# Ensure temp directory for images exists
os.makedirs("data/temp", exist_ok=True)
os.makedirs("data/charts", exist_ok=True)

class TicketItem(BaseModel):
    place_code: str
    race_num: int
    bet_type: str
    amount: int
    buy_details: str

class BetRequest(BaseModel):
    tickets: List[TicketItem]

class ParseRequest(BaseModel):
    raw_qr: str

@app.post("/api/parse_qr")
async def parse_qr(request: ParseRequest):
    try:
        # JRAParser is imported from modules.qr_reader
        # Try converting raw string (which might be 2 QRs concatenated)
        ticket = JRAParser.parse(request.raw_qr)
        
        return {
            "status": "success",
            "data": {
                "place_code": ticket.place_code,
                "race_num": ticket.race_num,
                "bet_type": ticket.bet_type,
                "amount": ticket.amount,
                "buy_details": ticket.buy_details
            }
        }
    except Exception as e:
        print(f"Parse error: {e}")
        raise HTTPException(status_code=400, detail="解析に失敗しました")

@app.post("/api/bets")
async def register_bets(request: BetRequest):
    try:
        current_date = datetime.date.today().strftime("%Y-%m-%d")
        registered_count = 0
        
        for ticket in request.tickets:
            calculator.add_bet(
                current_date,
                ticket.place_code,
                ticket.race_num,
                ticket.bet_type,
                ticket.buy_details,
                ticket.amount
            )
            registered_count += 1
            
        return {"status": "success", "count": registered_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/balance/{year}/{month}")
async def get_monthly_balance(year: int, month: int):
    try:
        summary = calculator.get_monthly_summary(year, month)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/callback")
async def callback(request: Request):
    # get X-Line-Signature header value
    signature = request.headers.get('X-Line-Signature', '')

    # get request body as text
    body = await request.body()
    body_text = body.decode('utf-8')

    # handle webhook body
    try:
        handler.handle(body_text, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    text = event.message.text.strip()
    
    # Fallback to text commands if LIFF is not used
    if text == "収支":
        today = datetime.date.today()
        summary = calculator.get_monthly_summary(today.year, today.month)
        balance = summary['balance']
        msg = f"{today.year}年{today.month}月の収支:\n購入: {summary['total_bet']}円\n払戻: {summary['total_return']}円\n収支: {balance:+d}円"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))

if __name__ == "__main__":
    import uvicorn
    # Local development
    uvicorn.run(app, host="0.0.0.0", port=8000)
