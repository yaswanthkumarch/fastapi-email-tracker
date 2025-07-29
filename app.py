from fastapi import FastAPI, Request, Form
from fastapi.responses import Response, HTMLResponse, FileResponse
from datetime import datetime
import base64
import json
import os
import smtplib
from email.message import EmailMessage
import logging
import uvicorn
import uuid

app = FastAPI()

# Constants
DATA_FILE = "/tmp/data.json"
MAPPING_FILE = "/tmp/mapping.json"
PIXEL_GIF_BASE64 = "R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw=="
PIXEL_GIF = base64.b64decode(PIXEL_GIF_BASE64)

# SMTP Config (Use App Password, not real password!)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "yaswanthkumarch2001@gmail.com"
SMTP_PASSWORD = "wxsy qntv rwny zjgp"  # App password, keep secure!

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure JSON files exist
for file_path, default in [(DATA_FILE, []), (MAPPING_FILE, {})]:
    if not os.path.exists(file_path):
        with open(file_path, "w") as f:
            json.dump(default, f)


@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <html><head><title>Email Tracker</title></head>
    <body>
        <h1>Email Tracker</h1>
        <form action="/send-email" method="post">
            <label>Recipient Emails (comma separated):</label><br>
            <textarea name="recipient_emails" rows="3" required></textarea><br><br>
            <label>Subject:</label><br>
            <input type="text" name="subject" required /><br><br>
            <label>Body (HTML allowed):</label><br>
            <textarea name="body" rows="8" required></textarea><br><br>
            <button type="submit">Send Tracked Email</button>
        </form>
        <p><a href="/logs">View Logs</a> | <a href="/download-logs">Download Logs</a></p>
    </body>
    </html>
    """


@app.post("/send-email", response_class=HTMLResponse)
async def send_email(
    recipient_emails: str = Form(...),
    subject: str = Form(...),
    body: str = Form(...)
):
    recipients = [email.strip() for email in recipient_emails.split(",") if email.strip()]
    sent, failed = [], []

    with open(MAPPING_FILE, "r") as f:
        mapping = json.load(f)

    for recipient in recipients:
        uid = str(uuid.uuid4())
        tracking_url = f"https://fastapi-email-tracker.onrender.com/track?id={uid}"

        # Prepare HTML email with pixel
        html_content = f"""
        <html><body>{body}<img src="{tracking_url}" width="1" height="1" style="display:none;" /></body></html>
        """

        # Store ID mapping
        mapping[uid] = {
            "email": recipient,
            "subject": subject,
            "sent_at": datetime.utcnow().isoformat()
        }

        # Email Setup
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = SMTP_USERNAME
        msg["To"] = recipient
        msg.set_content("This email requires an HTML-compatible client.")
        msg.add_alternative(html_content, subtype="html")

        try:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)
            sent.append(recipient)
            logger.info(f"Sent to {recipient} with ID {uid}")
        except Exception as e:
            failed.append((recipient, str(e)))
            logger.error(f"Failed to send to {recipient}: {e}")

    with open(MAPPING_FILE, "w") as f:
        json.dump(mapping, f, indent=2)

    # Show Result
    html = "<h2>Send Results</h2>"
    if sent:
        html += "<h3>Success:</h3><ul>" + "".join(f"<li>{r}</li>" for r in sent) + "</ul>"
    if failed:
        html += "<h3>Failed:</h3><ul>" + "".join(f"<li>{r}: {e}</li>" for r, e in failed) + "</ul>"

    html += "<p><a href='/'>Send Another</a> | <a href='/logs'>View Logs</a></p>"
    return html


@app.get("/track")
async def track_email(request: Request, id: str):
    user_agent = request.headers.get("user-agent", "").lower()
    ip = request.client.host
    timestamp = datetime.utcnow().isoformat()

    # Expanded list of known bot substrings (case-insensitive)
    KNOWN_BOTS = [
        "googleimageproxy",  # Google Image Proxy used by Gmail, Google apps
        "outlook",           # Outlook image proxy / crawler
        "yahoo",             # Yahoo mail proxy / crawler
        "bingbot",           # Bing search engine bot
        "facebookexternalhit", # Facebook crawler
        "twitterbot",        # Twitter crawler
        "linkedinbot",       # LinkedIn crawler
        "slackbot",          # Slack crawler
        "telegrambot",       # Telegram crawler
        "applebot",          # Apple crawler
        "discordbot",        # Discord crawler
        "bot",               # Generic bot keyword to catch many bots
        "spider",            # Generic spider keyword
        "crawl",             # Generic crawler keyword
        "curl",              # curl command line tool
        "wget",              # wget command line tool
        "python",            # Python scripts
        "java",              # Java HTTP clients
        "httpclient",        # Generic HTTP client keyword
        "fetch",             # fetch API bots
        "postman",           # Postman API tool
        "monitor",           # Monitoring tools
        "scan",              # Scanners
        "validator",         # HTML or SEO validators
        "scrapy",            # Scrapy spider
        "php",               # PHP-based bots or clients
        "axios",             # Axios HTTP client
    ]

    if any(bot in user_agent for bot in KNOWN_BOTS):
        logger.info(f"Ignored bot access: {user_agent}")
        return Response(content=PIXEL_GIF, media_type="image/gif")

    with open(MAPPING_FILE, "r") as f:
        mapping = json.load(f)

    if id not in mapping:
        logger.warning(f"Unknown tracking ID: {id}")
        return Response(content=PIXEL_GIF, media_type="image/gif")

    email = mapping[id]["email"]
    logger.info(f"Email opened: {email} (IP: {ip}, UA: {user_agent})")

    with open(DATA_FILE, "r") as f:
        logs = json.load(f)

    logs.append({
        "id": id,
        "email": email,
        "ip": ip,
        "user_agent": user_agent,
        "timestamp": timestamp
    })

    with open(DATA_FILE, "w") as f:
        json.dump(logs, f, indent=2)

    return Response(content=PIXEL_GIF, media_type="image/gif")


@app.get("/logs", response_class=HTMLResponse)
async def view_logs():
    with open(DATA_FILE, "r") as f:
        data = json.load(f)

    html = "<html><body><h2>Email Open Logs</h2><ul>"
    for entry in data:
        html += f"<li><b>{entry['email']}</b> opened at {entry['timestamp']} from IP {entry['ip']}</li>"
    html += "</ul><p><a href='/'>Back</a></p></body></html>"
    return html


@app.get("/download-logs")
async def download_logs():
    if os.path.exists(DATA_FILE):
        return FileResponse(DATA_FILE, media_type="application/json", filename="email_open_logs.json")
    return {"error": "No log file found."}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
