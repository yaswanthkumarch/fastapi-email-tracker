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

DATA_FILE = "/tmp/data.json"

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
            max-width: 600px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
          }
          label {
            font-weight: 600;
            display: block;
            margin-top: 15px;
          }
          input[type=text], textarea {
            width: 100%;
            padding: 10px;
            margin-top: 6px;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-size: 1rem;
            resize: vertical;
          }
          button {
            margin-top: 20px;
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
          <label for="recipient_emails">Recipient Emails (comma separated):</label>
          <textarea id="recipient_emails" name="recipient_emails" required rows="3" placeholder="e.g. alice@example.com, bob@example.com"></textarea>
          
          <label for="subject">Subject:</label>
          <input type="text" id="subject" name="subject" required placeholder="Email subject here">
          
          <label for="body">Body (HTML allowed):</label>
          <textarea id="body" name="body" required rows="8" placeholder="Write your email body here..."></textarea>
          
          <button type="submit">Send Tracked Email</button>
        </form>
        <p>Check <a href="/logs">Logs</a> to see who opened emails.</p>
        <p><a href="/download-logs" download>Download Logs JSON</a></p>

      </body>
    </html>
    """

@app.post("/send-email", response_class=HTMLResponse)
async def send_email(
    recipient_emails: str = Form(...),  # comma separated emails
    subject: str = Form(...),
    body: str = Form(...)
):
    recipients = [email.strip() for email in recipient_emails.split(",") if email.strip()]
    sent_to = []
    errors = []

    for recipient_email in recipients:
        tracking_url = f"https://fastapi-email-tracker.onrender.com/track?email={recipient_email}"

        # Append tracking pixel to body
        html_content = f"""
        <html>
          <body>
            {body}
            <img src="{tracking_url}" width="1" height="1" alt="" style="display:none;" />
          </body>
        </html>
        """

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = SMTP_USERNAME
        msg["To"] = recipient_email
        msg.set_content("This email requires an HTML-capable client.")
        msg.add_alternative(html_content, subtype="html")

        try:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)
            logger.info(f"Email sent successfully to {recipient_email}")
            sent_to.append(recipient_email)
        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {e}")
            errors.append((recipient_email, str(e)))

    success_html = ""
    if sent_to:
        success_html += "<h3>Emails sent successfully to:</h3><ul>"
        for s in sent_to:
            success_html += f"<li>{s}</li>"
        success_html += "</ul>"

    error_html = ""
    if errors:
        error_html += "<h3 style='color:#c0392b;'>Errors sending to:</h3><ul>"
        for e_mail, err_msg in errors:
            error_html += f"<li>{e_mail}: {err_msg}</li>"
        error_html += "</ul>"

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
          ul {{
            max-width: 400px;
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
          }}
          li {{
            margin-bottom: 5px;
          }}
        </style>
      </head>
      <body>
        {success_html}
        {error_html}
        <p><a href='/'>Send another</a> | <a href='/logs'>View logs</a></p>
       
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
from fastapi.responses import FileResponse

@app.get("/download-logs")
async def download_logs():
    if os.path.exists(DATA_FILE):
        return FileResponse(DATA_FILE, media_type="application/json", filename="email_open_logs.json")
    return {"error": "Log file not found."}


import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

