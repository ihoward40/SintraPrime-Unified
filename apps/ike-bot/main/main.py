# main.py (IKE Bot Trust Automation Engine)
from flask import Flask, request, jsonify, render_template
import os
import subprocess
import json
import requests
from fpdf import FPDF
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import smtplib
from email.message import EmailMessage
from datetime import datetime

app = Flask(__name__)

NOTION_LOG_DB = os.getenv("NOTION_ACTIVITY_LOG")
NOTION_ARCHIVE_DB = os.getenv("NOTION_FILINGS_DB")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
SINTRA_WEBHOOK_URL = os.getenv("SINTRA_WEBHOOK_URL")
SEND_TO_EMAIL = os.getenv("SEND_TO_GMAIL")
GDRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
GOOGLE_CREDS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
DAILY_DIGEST_EMAIL = os.getenv("DAILY_DIGEST_EMAIL")

def log_to_notion(title, body, archive=False):
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    db_id = NOTION_ARCHIVE_DB if archive else NOTION_LOG_DB
    data = {
        "parent": {"database_id": db_id},
        "properties": {
            "Title": {"title": [{"text": {"content": title}}]},
            "Details": {"rich_text": [{"text": {"content": body}}]}
        }
    }
    requests.post("https://api.notion.com/v1/pages", headers=headers, data=json.dumps(data))

def notify_sintra(event_type, payload):
    if SINTRA_WEBHOOK_URL:
        requests.post(SINTRA_WEBHOOK_URL, json={"type": event_type, "payload": payload})

def send_to_gmail(subject, body, filepath):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SEND_TO_EMAIL
    msg["To"] = SEND_TO_EMAIL
    msg.set_content(body)
    with open(filepath, "rb") as f:
        file_data = f.read()
        file_name = os.path.basename(filepath)
    msg.add_attachment(file_data, maintype="application", subtype="pdf", filename=file_name)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(SEND_TO_EMAIL, os.getenv("EMAIL_PASSWORD"))
        smtp.send_message(msg)

def upload_to_drive(filepath):
    creds = service_account.Credentials.from_service_account_file(GOOGLE_CREDS_PATH, scopes=["https://www.googleapis.com/auth/drive"])
    service = build("drive", "v3", credentials=creds)
    file_metadata = {"name": os.path.basename(filepath), "parents": [GDRIVE_FOLDER_ID]}
    media = MediaFileUpload(filepath, mimetype="application/pdf")
    file = service.files().create(body=file_metadata, media_body=media, fields="id,webViewLink").execute()
    return file.get("id"), file.get("webViewLink")

def generate_pdf(content, filename):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in content.split("\n"):
        pdf.cell(200, 10, txt=line, ln=True)
    filepath = f"output/{filename}.pdf"
    pdf.output(filepath)
    return filepath

def send_daily_digest():
    log_path = "output/trust_minutes.log"
    today = datetime.now().strftime("%Y-%m-%d")
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            content = f.read()
        digest = EmailMessage()
        digest["Subject"] = f"Daily Filing Digest - {today}"
        digest["From"] = SEND_TO_EMAIL
        digest["To"] = DAILY_DIGEST_EMAIL
        digest.set_content(f"Daily Digest of Trust Filing Logs:\n\n{content}")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(SEND_TO_EMAIL, os.getenv("EMAIL_PASSWORD"))
            smtp.send_message(digest)

@app.route("/run-agent", methods=["POST"])
def run_agent():
    data = request.json
    agent = data.get("agent")
    payload = data.get("payload", {})
    if agent not in AGENTS:
        return jsonify({"error": "Invalid agent name."}), 400
    try:
        result = AGENTS[agent](payload)
        return jsonify({"result": result}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/intake", methods=["GET", "POST"])
def form_intake():
    if request.method == "POST":
        return run_agent()
    return '''
        <form method="POST">
            Agent:<br><input name="agent" value="affidavit_bot"><br>
            Statement:<br><textarea name="statement"></textarea><br>
            IRS Notice ID:<br><input name="notice_id"><br>
            IRS Response:<br><textarea name="response"></textarea><br>
            <input type="submit" value="Submit">
        </form>
    '''

@app.route("/digest", methods=["POST"])
def trigger_digest():
    send_daily_digest()
    return jsonify({"status": "Daily digest sent"})

def affidavit_bot(payload):
    content = payload.get("statement", "Affidavit content not provided.")
    filepath = generate_pdf(content, "affidavit")
    log_to_notion("Affidavit Created", content)
    log_to_notion("Affidavit Filed", content, archive=True)
    notify_sintra("affidavit_created", payload)
    send_to_gmail("Affidavit Created", content, filepath)
    _, link = upload_to_drive(filepath)
    return {"file": filepath, "status": "Generated", "drive_link": link}

AGENTS = {"affidavit_bot": affidavit_bot}

if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    app.run(debug=True, port=5000)
