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
    # TODO: Replace with the actual telegram bot link
    telegram_bot_url = "https://t.me/ToolTaiXiuAIBot?start=email_campaign" 
    return RedirectResponse(url=telegram_bot_url)

@app.get("/api/stats")
async def get_stats():
    # Return JSON stats for the dashboard
    return db.get_stats()

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    # Serve the dashboard page
    return templates.TemplateResponse(request, "dashboard.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
