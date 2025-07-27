from fastapi import FastAPI, Request, Form
from fastapi.responses import Response, HTMLResponse
from pydantic import EmailStr
from datetime import datetime
import base64
import json
import os
import smtplib
from email.message import EmailMessage
import logging
import uvicorn

app = FastAPI()

DATA_FILE = "data.json"

PIXEL_GIF_BASE64 = "R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw=="
PIXEL_GIF = base64.b64decode(PIXEL_GIF_BASE64)

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "yaswanthkumarch2001@gmail.com"  # Replace with your Gmail address
SMTP_PASSWORD = "wxsy qntv rwny zjgp"             # Replace with your Gmail App Password

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Ensure data file exists
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump([], f)

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <html>
      <head>
        <title>Email Tracker</title>
        <style>
          body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f9fafb;
            margin: 0;
            padding: 20px;
            color: #333;
          }
          h1 {
            color: #4a90e2;
          }
          form {
            background: white;
            padding: 20px;
            border-radius: 8px;
            max-width: 400px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
          }
          label {
            font-weight: 600;
          }
          input[type=email] {
            width: 100%;
            padding: 10px;
            margin-top: 6px;
            margin-bottom: 20px;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-size: 1rem;
          }
          button {
            background-color: #4a90e2;
            border: none;
            color: white;
            padding: 12px 20px;
            font-size: 1rem;
            border-radius: 4px;
            cursor: pointer;
          }
          button:hover {
            background-color: #357ABD;
          }
          p {
            margin-top: 20px;
          }
          a {
            color: #4a90e2;
            text-decoration: none;
          }
          a:hover {
            text-decoration: underline;
          }
        </style>
      </head>
      <body>
        <h1>Email Tracker</h1>
        <form action="/send-email" method="post">
          <label for="recipient_email">Recipient Email:</label><br>
          <input type="email" id="recipient_email" name="recipient_email" required><br>
          <button type="submit">Send Tracked Email</button>
        </form>
        <p>Check <a href="/logs">Logs</a> to see who opened emails.</p>
      </body>
    </html>
    """

@app.post("/send-email", response_class=HTMLResponse)
async def send_email(recipient_email: str = Form(...)):
    tracking_url = f"http://127.0.0.1:8000/track?email={recipient_email}"
    html_content = f"""
    <html>
      <body>
        <p>Hello,</p>
        <p>This is a test email with tracking.</p>
        <img src="{tracking_url}" width="1" height="1" alt="" />
      </body>
    </html>
    """

    msg = EmailMessage()
    msg["Subject"] = "Test Email with Tracking Pixel"
    msg["From"] = SMTP_USERNAME
    msg["To"] = recipient_email
    msg.set_content("This is a test email with tracking (HTML not supported).")
    msg.add_alternative(html_content, subtype="html")

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        logger.info(f"Email sent successfully to {recipient_email}")
        return f"""
        <html>
          <head>
            <style>
              body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: #f9fafb;
                padding: 20px;
                color: #333;
              }}
              h3 {{
                color: #4a90e2;
              }}
              a {{
                color: #4a90e2;
                text-decoration: none;
                margin-right: 10px;
              }}
              a:hover {{
                text-decoration: underline;
              }}
            </style>
          </head>
          <body>
            <h3>Email sent to {recipient_email} successfully!</h3>
            <p><a href='/'>Send another</a> | <a href='/logs'>View logs</a></p>
          </body>
        </html>
        """
    except Exception as e:
        logger.error(f"Failed to send email to {recipient_email}: {e}")
        return f"""
        <html>
          <head>
            <style>
              body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: #f9fafb;
                padding: 20px;
                color: #c0392b;
              }}
              h3 {{
                color: #c0392b;
              }}
              a {{
                color: #4a90e2;
                text-decoration: none;
              }}
              a:hover {{
                text-decoration: underline;
              }}
            </style>
          </head>
          <body>
            <h3>Error sending email: {e}</h3>
            <p><a href='/'>Try again</a></p>
          </body>
        </html>
        """

@app.get("/track")
async def track_email(request: Request, email: EmailStr):
    user_agent = request.headers.get("user-agent", "")
    ip = request.client.host
    timestamp = datetime.utcnow().isoformat()

    logger.info(f"Email opened by {email} from IP {ip} with UA {user_agent}")

    with open(DATA_FILE, "r") as f:
        data = json.load(f)

    data.append({
        "email": email,
        "ip": ip,
        "user_agent": user_agent,
        "timestamp": timestamp
    })

    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

    return Response(content=PIXEL_GIF, media_type="image/gif")

@app.get("/logs", response_class=HTMLResponse)
async def view_logs():
    logger.info("Logs page viewed")
    with open(DATA_FILE, "r") as f:
        data = json.load(f)

    html = """
    <html>
      <head>
        <title>Email Open Logs</title>
        <style>
          body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f9fafb;
            margin: 20px;
            color: #333;
          }
          h2 {
            color: #4a90e2;
          }
          ul {
            list-style-type: none;
            padding: 0;
            max-width: 700px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
          }
          li {
            padding: 12px 15px;
            border-bottom: 1px solid #ddd;
            font-size: 1rem;
          }
          li:last-child {
            border-bottom: none;
          }
          strong {
            color: #2c3e50;
          }
          a {
            color: #4a90e2;
            text-decoration: none;
          }
          a:hover {
            text-decoration: underline;
          }
          p {
            margin-top: 20px;
          }
        </style>
      </head>
      <body>
        <h2>Email Open Logs</h2>
        <ul>
    """

    for entry in data:
        html += (
            f"<li><strong>{entry['email']}</strong> opened at {entry['timestamp']} "
            f"from IP {entry['ip']} (User-Agent: {entry['user_agent']})</li>"
        )
    html += """
        </ul>
        <p><a href='/'>Back to Send Email</a></p>
      </body>
    </html>
    """
    return html


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
