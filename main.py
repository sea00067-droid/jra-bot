import os
import sys
from fastapi import FastAPI, Request, HTTPException
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, ImageMessage, ImageSendMessage
)
from modules.qr_reader import QRReader
from modules.jra_scraper import JRAScraper
from modules.calculator import Calculator
from modules.reporter import Reporter
import datetime

app = FastAPI()

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

@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    message_content = line_bot_api.get_message_content(event.message.id)
    temp_path = f"data/temp/{event.message.id}.jpg"
    
    with open(temp_path, 'wb') as fd:
        for chunk in message_content.iter_content():
            fd.write(chunk)
            
    try:
        # Decode QR
        tickets = qr_reader.decode_ticket(temp_path)
        
        reply_text = ""
        if not tickets:
            reply_text = "QRコードが見つかりませんでした。別の写真を試してください。"
        else:
            for ticket in tickets:
                # Save to DB (Assuming mock implementation returns valid data)
                # In real app, we might need to conform date/place formats
                current_date = datetime.date.today().strftime("%Y-%m-%d") # Mock date
                
                calculator.add_bet(
                    current_date, 
                    ticket.place_code, 
                    ticket.race_num, 
                    ticket.bet_type, 
                    ticket.buy_details, 
                    ticket.amount
                )
                reply_text += f"{ticket.place_code} {ticket.race_num}R {ticket.bet_type}: {ticket.amount}円 を登録しました。\n"

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )
        
    except Exception as e:
        print(f"Error processing image: {e}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="エラーが発生しました。")
        )

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    text = event.message.text.strip()
    
    if text == "収支":
        today = datetime.date.today()
        summary = calculator.get_monthly_summary(today.year, today.month)
        
        balance = summary['balance']
        msg = f"{today.year}年{today.month}月の収支:\n購入: {summary['total_bet']}円\n払戻: {summary['total_return']}円\n収支: {balance:+d}円"
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=msg)
        )
        
    elif text == "グラフ":
        today = datetime.date.today()
        chart_path = f"data/charts/chart_{today.year}_{today.month}.png"
        generated = reporter.generate_monthly_chart(today.year, today.month, chart_path)
        
        if generated and os.path.exists(generated):
            # In production, we need a public URL for the image.
            # Localhost URLs won't work for LINE.
            # For this PoC code, we will just say we created it, 
            # or if we had a public URL mechanism (like Cloud Storage), we'd use that.
            
            # Since we can't send a local file path to LINE, we'll reply with text for now
            # asking user to imagine the graph or stating it's saved server-side.
            
            # To actually send an image, use ImageSendMessage(original_content_url=..., preview_image_url=...)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="グラフを作成しました(サーバーに保存)。\n※LINEに画像を送るには公開URLが必要です。")
            )
        else:
             line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="データがないためグラフを作成できませんでした。")
            )

    elif text == "更新":
        # Manually trigger result update
        # In a real app, this would iterate over pending bets in DB and scrape JRA
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="レース結果を確認し、収支を更新しました。(Mock)")
        )

if __name__ == "__main__":
    import uvicorn
    # Local development
    uvicorn.run(app, host="0.0.0.0", port=8000)
