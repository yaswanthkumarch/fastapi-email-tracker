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
from collections import Counter

app = FastAPI()

# Constants
DATA_FILE = "/tmp/data.json"
MAPPING_FILE = "/tmp/mapping.json"
FAILED_FILE = "/tmp/failed.json"  # Track failed sends (optional)
PIXEL_GIF_BASE64 = "R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw=="
PIXEL_GIF = base64.b64decode(PIXEL_GIF_BASE64)

# SMTP Config (Use environment variables in production!)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "yaswanthkumarch2001@gmail.com"
SMTP_PASSWORD = "wxsy qntv rwny zjgp"  # Keep secure!

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Helper function to safely load JSON or create default
def load_json_file(path, default):
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump(default, f)
        return default
    with open(path, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return default

# Ensure JSON files exist at startup
mapping = load_json_file(MAPPING_FILE, {})
logs = load_json_file(DATA_FILE, [])
failed_sends = load_json_file(FAILED_FILE, [])


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
        <p><a href="/logs">View Logs</a> | <a href="/analytics">View Analytics</a> | <a href="/download-logs">Download Logs</a></p>
    </body>
    </html>
    """


@app.post("/send-email", response_class=HTMLResponse)
async def send_email(
    recipient_emails: str = Form(...),
    subject: str = Form(...),
    body: str = Form(...)
):
    global mapping, failed_sends

    recipients = [email.strip() for email in recipient_emails.split(",") if email.strip()]
    sent, failed = [], []

    for recipient in recipients:
        uid = str(uuid.uuid4())
        # Replace this URL with your deployment or localhost URL
        tracking_url = f"https://fastapi-email-tracker.onrender.com/track?id={uid}"

        # Embed tracking pixel
        html_content = f"""
        <html><body>{body}<img src="{tracking_url}" width="1" height="1" style="display:none;" /></body></html>
        """

        # Store tracking ID mapping
        mapping[uid] = {
            "email": recipient,
            "subject": subject,
            "sent_at": datetime.utcnow().isoformat()
        }

        # Setup email
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

    # Update mapping file
    with open(MAPPING_FILE, "w") as f:
        json.dump(mapping, f, indent=2)

    # Update failed sends log file
    if failed:
        failed_sends.extend([{"email": r, "error": err, "timestamp": datetime.utcnow().isoformat()} for r, err in failed])
        with open(FAILED_FILE, "w") as f:
            json.dump(failed_sends, f, indent=2)

    # Show results
    html = "<h2>Send Results</h2>"
    if sent:
        html += "<h3>Success:</h3><ul>" + "".join(f"<li>{r}</li>" for r in sent) + "</ul>"
    if failed:
        html += "<h3>Failed:</h3><ul>" + "".join(f"<li>{r}: {e}</li>" for r, e in failed) + "</ul>"

    html += "<p><a href='/'>Send Another</a> | <a href='/logs'>View Logs</a> | <a href='/analytics'>View Analytics</a></p>"
    return html


@app.get("/track")
async def track_email(request: Request, id: str):
    user_agent = request.headers.get("user-agent", "").lower()
    ip = request.client.host
    timestamp = datetime.utcnow().isoformat()

    KNOWN_BOTS = [
        "googleimageproxy", "outlook", "yahoo", "bingbot", "facebookexternalhit",
        "twitterbot", "linkedinbot", "slackbot", "telegrambot", "applebot",
        "discordbot", "bot", "spider", "crawl", "curl", "wget", "python",
        "java", "httpclient", "fetch", "postman", "monitor", "scan",
        "validator", "scrapy", "php", "axios"
    ]

    if any(bot in user_agent for bot in KNOWN_BOTS):
        logger.info(f"Ignored bot access: {user_agent}")
        return Response(content=PIXEL_GIF, media_type="image/gif")

    # Reload mapping on each request to stay fresh
    mapping = load_json_file(MAPPING_FILE, {})

    if id not in mapping:
        logger.warning(f"Unknown tracking ID: {id}")
        return Response(content=PIXEL_GIF, media_type="image/gif")

    email = mapping[id]["email"]
    logger.info(f"Email opened: {email} (IP: {ip}, UA: {user_agent})")

    logs = load_json_file(DATA_FILE, [])
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
    data = load_json_file(DATA_FILE, [])

    html = "<html><body><h2>Email Open Logs</h2><ul>"
    for entry in data:
        html += f"<li><b>{entry['email']}</b> opened at {entry['timestamp']} from IP {entry['ip']}</li>"
    html += "</ul><p><a href='/'>Back</a></p></body></html>"
    return html


@app.get("/analytics", response_class=HTMLResponse)
async def analytics():
    mapping = load_json_file(MAPPING_FILE, {})
    logs = load_json_file(DATA_FILE, [])
    failed_sends = load_json_file(FAILED_FILE, [])

    total_emails_sent = len(mapping)
    total_opens = len(logs)
    unique_opens_per_email = {}

    # Calculate unique opens per email (unique IPs per email)
    email_open_ips = {}
    for entry in logs:
        email = entry['email']
        ip = entry['ip']
        email_open_ips.setdefault(email, set()).add(ip)
    for email, ips in email_open_ips.items():
        unique_opens_per_email[email] = len(ips)

    # Top clients summary
    user_agents = [entry['user_agent'] for entry in logs]
    ua_counts = Counter(user_agents).most_common(10)

    html = f"""
    <html><body>
    <h2>Email Tracker Analytics</h2>
    <p><b>Total Emails Sent:</b> {total_emails_sent}</p>
    <p><b>Total Opens (all):</b> {total_opens}</p>
    <h3>Unique Opens Per Email (by IP):</h3>
    <ul>
    """
    for email, count in unique_opens_per_email.items():
        html += f"<li>{email}: {count} unique open(s)</li>"
    html += "</ul>"

    html += "<h3>Top 10 User Agents:</h3><ul>"
    for ua, count in ua_counts:
        html += f"<li>{ua} — {count} opens</li>"
    html += "</ul>"

    if failed_sends:
        html += "<h3>Failed Email Sends:</h3><ul>"
        for fail in failed_sends[-10:]:  # Show last 10 failed attempts
            html += f"<li>{fail['email']} at {fail['timestamp']} — {fail['error']}</li>"
        html += "</ul>"

    html += "<p><a href='/'>Back</a></p></body></html>"
    return html


@app.get("/download-logs")
async def download_logs():
    if os.path.exists(DATA_FILE):
        return FileResponse(DATA_FILE, media_type="application/json", filename="email_open_logs.json")
    return {"error": "No log file found."}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
