from fastapi import FastAPI, Request, Response
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import database as db
import os

app = FastAPI()

# Setup templates directory
templates = Jinja2Templates(directory="templates")

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    db.init_db()

# 1x1 Transparent GIF
TRANSPARENT_GIF = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'

@app.get("/track/open/{token}.gif")
async def track_open(token: str):
    # Mark email as opened
    db.mark_opened(token)
    # Return a 1x1 transparent image
    return Response(content=TRANSPARENT_GIF, media_type="image/gif")

@app.get("/track/click/{token}")
async def track_click(token: str):
    # Mark email as clicked
    db.mark_clicked(token)
    # Redirect to the Telegram Bot
    telegram_bot_url = "https://t.me/ToolTXbot" 
    return RedirectResponse(url=telegram_bot_url)

@app.get("/api/stats")
async def get_stats():
    # Return JSON stats for the dashboard
    return db.get_stats()

@app.get("/api/daily_stats")
async def api_daily_stats():
    return db.get_daily_stats()

@app.get("/api/status")
async def api_status():
    return {"status": db.get_campaign_status()}

@app.post("/api/toggle")
async def api_toggle():
    new_status = db.toggle_campaign_status()
    return {"status": new_status}

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    # Serve the dashboard page
    return templates.TemplateResponse(request, "dashboard.html")

# --- SCHEDULER SYSTEM ---
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import send_campaign

def job_send_emails():
    # 1. Check if campaign is ON
    if db.get_campaign_status() != 'ON':
        return

    # 2. Check if within golden hours
    # Khung giờ 1: 11:30 - 13:00
    # Khung giờ 2: 20:00 - 23:30
    now = datetime.now()
    current_time = now.time()
    
    time_1_start = datetime.strptime("11:30", "%H:%M").time()
    time_1_end = datetime.strptime("13:00", "%H:%M").time()
    
    time_2_start = datetime.strptime("20:00", "%H:%M").time()
    time_2_end = datetime.strptime("23:30", "%H:%M").time()
    
    in_golden_hour = (time_1_start <= current_time <= time_1_end) or (time_2_start <= current_time <= time_2_end)
    
    if not in_golden_hour:
        return

    # 3. Check daily limit (max 200/day for Sandbox)
    daily_stats = db.get_daily_stats()
    today_str = now.strftime("%Y-%m-%d")
    today_sent = 0
    for stat in daily_stats:
        if stat['date'] == today_str:
            today_sent = stat['sent'] + stat['failed']
            break
            
    if today_sent >= 200:
        return # Reached limit
        
    # 4. If all checks pass, run a small batch (10 emails)
    # The scheduler runs every minute, so 10 emails/min is safe.
    batch_size = min(10, 200 - today_sent)
    if batch_size > 0:
        send_campaign.run_campaign(batch_size=batch_size, delay_seconds=1)

scheduler = BackgroundScheduler()
scheduler.add_job(job_send_emails, 'interval', minutes=1)

@app.on_event("startup")
def startup_event():
    db.init_db()
    scheduler.start()

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
