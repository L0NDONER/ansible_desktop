#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WhatsApp Commander Bot - Minty Server Control
Cleaned & Path-Resilient Version
"""
import subprocess
import psutil
import os
import logging
import json
import re
import shutil
import sqlite3
from functools import wraps
from flask import Flask, request, abort
from twilio.twiml.messaging_response import MessagingResponse
from twilio.request_validator import RequestValidator

import ollama
from faster_whisper import WhisperModel
import requests

# =============================================================================
# CONFIGURATION (Using Absolute Paths for Stability)
# =============================================================================

# Security
ALLOWED_NUMBERS = os.getenv('ALLOWED_WHATSAPP_NUMBERS', 'whatsapp:+441174632546,whatsapp:+447375272694').split(',')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')

# Paths - Adjusted for your new subfolder organization
BASE_DIR = os.path.expanduser('~/ansible')
INVENTORY_PATH = os.path.join(BASE_DIR, 'inventory')
VAULT_PASS_FILE = os.path.join(BASE_DIR, '.vault_pass')
AUTODL_FILTER_PATH = os.path.expanduser('~/.autodl/autodl.cfg')
JELLYLINK_DB_PATH = os.path.expanduser('~/jellylink/jellylink.db')
DOWNLOAD_DIR = os.path.expanduser('~/Downloads')

# Logging
logging.basicConfig(
    filename=os.path.expanduser('~/commander_audit.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)
validator = RequestValidator(TWILIO_AUTH_TOKEN)
WHISPER_MODEL = None

def get_whisper_model():
    global WHISPER_MODEL
    if WHISPER_MODEL is None:
        # Optimized for CPU usage on home-lab hardware
        WHISPER_MODEL = WhisperModel("tiny.en", device="cpu", compute_type="int8")
    return WHISPER_MODEL

# =============================================================================
# SECURITY DECORATOR
# =============================================================================

def validate_twilio_request(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        signature = request.headers.get('X-Twilio-Signature', '')
        url = request.url.replace('http://', 'https://')
        post_vars = request.form.to_dict()
        if not validator.validate(url, post_vars, signature):
            if request.values.get('From', '') not in ALLOWED_NUMBERS:
                logging.warning(f"Unauthorized access attempt from: {request.values.get('From')}")
                abort(403)
        return f(*args, **kwargs)
    return decorated

# =============================================================================
# SYSTEM ACTION HANDLERS
# =============================================================================

def handle_disk_command():
    try:
        usage = psutil.disk_usage('/')
        percent = usage.percent
        status = "🚨" if percent > 90 else "⚠️" if percent > 75 else "✅"
        return (
            f"💽 *Disk Usage (Root)*\n"
            f"Used: {usage.used // (2**30)}GB / {usage.total // (2**30)}GB ({percent}%)\n"
            f"Status: {status}"
        )
    except Exception as e:
        return f"❌ Disk check error: {str(e)}"

def handle_fleet_command():
    hosts = []
    if os.path.exists(INVENTORY_PATH):
        with open(INVENTORY_PATH, 'r') as f:
            for line in f:
                if line.strip() and not line.strip().startswith(('[', '#', ';')):
                    h = line.split()[0]
                    if '=' not in h and h.upper() != 'MINTY': hosts.append(h)
    
    response = "🌐 *Minty Fleet Dashboard*"
    for host in (['localhost'] + hosts):
        try:
            if host == 'localhost':
                with open('/tmp/fleet_health.json', 'r') as f: data = json.load(f)
            else:
                raw = subprocess.check_output(["ssh", "-o", "ConnectTimeout=2", host, "cat /tmp/fleet_health.json"], timeout=3).decode()
                data = json.loads(raw)
            response += f"\n\n*{host.upper()}*\n┣ ⏱️ {data.get('uptime','n/a')}\n┣ 🛡️ {data.get('knocks','0')} hits"
        except:
            response += f"\n\n🔴 *{host.upper()}* (down)"
    return response

def handle_pingall_command():
    try:
        # Uses absolute paths for inventory and vault to ensure success 
        out = subprocess.check_output([
            "ansible", "all", "-m", "ping", "-i", INVENTORY_PATH, "--vault-password-file", VAULT_PASS_FILE
        ], timeout=15).decode()
        pong_count = out.count('"ping": "pong"')
        total_count = out.count('SUCCESS') + out.count('UNREACHABLE')
        return f"🟢 Fleet ping\n✅ Online: {pong_count}/{total_count}"
    except Exception as e: 
        return f"❌ Ping failed: {str(e)}"

def get_recent_media(limit=5):
    if not os.path.exists(JELLYLINK_DB_PATH): return "❌ Media DB not found"
    conn = sqlite3.connect(JELLYLINK_DB_PATH)
    rows = conn.execute("SELECT title, media_type, strftime('%d/%m %H:%M', processed_date) FROM processed_media ORDER BY processed_date DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    if not rows: return "📭 No recent media found."
    res = "📺 *Recent Media*\n"
    for t, m, d in rows:
        res += f"\n{'📺' if m=='TV' else '🎬'} {t}\n   └ {d}"
    return res

# =============================================================================
# AI PROCESSING & WEBHOOK
# =============================================================================

def parse_with_ollama(text):
    prompt = """
    You are Minty, a chill home-lab commander bot. Use emojis and a friendly vibe.
    Start every response with "Minty: ".
    Actions: uptime, top, disk, fleet, pingall, update, seeds, recent.
    If an action is needed, include "ACTION: <command>".
    """
    try:
        resp = ollama.chat(model='llama3.2:3b', messages=[{'role': 'system', 'content': prompt}, {'role': 'user', 'content': text}])
        return resp['message']['content'].strip()
    except:
        return "Minty: Brain fog... give me a second! 🧠"

@app.route("/webhook", methods=['POST'])
@validate_twilio_request
def whatsapp_bot():
    body = (request.values.get('Body') or '').strip()
    media_url = request.values.get('MediaUrl0')
    
    # Audio Handling (Whisper) 
    if media_url and 'audio' in request.values.get('MediaContentType0', '').lower():
        r = requests.get(media_url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
        if r.status_code == 200:
            with open('/tmp/voice.ogg', 'wb') as f: f.write(r.content)
            segments, _ = get_whisper_model().transcribe('/tmp/voice.ogg')
            body = ' '.join([s.text for s in segments]).strip()

    if not body:
        return str(MessagingResponse().message("Minty: I'm listening! 🔊"))

    ai_reply = parse_with_ollama(body)
    reply_text = ai_reply
    
    # Command Routing
    if "ACTION:" in ai_reply:
        act = ai_reply.split("ACTION:")[1].strip().lower()
        res = ""
        if "uptime" in act: res = subprocess.run(['uptime'], capture_output=True, text=True).stdout.strip()
        elif "disk" in act: res = handle_disk_command()
        elif "fleet" in act: res = handle_fleet_command()
        elif "pingall" in act: res = handle_pingall_command()
        elif "recent" in act: res = get_recent_media()
        
        if res: reply_text += f"\n\n{res}"

    resp = MessagingResponse()
    resp.message(reply_text)
    return str(resp)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
