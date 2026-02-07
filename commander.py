#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WhatsApp Commander Bot - Minty Server Control via Twilio
Version 1.2 - Identity update + Disk monitoring
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

# Natural language & voice processing
import ollama
from faster_whisper import WhisperModel
import requests

# =============================================================================
# CONFIGURATION
# =============================================================================

ALLOWED_NUMBERS = os.getenv('ALLOWED_WHATSAPP_NUMBERS', '').split(',')
if not ALLOWED_NUMBERS:
    ALLOWED_NUMBERS = [
        'whatsapp:+441174632546',
        'whatsapp:+447375272694'
    ]

TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')

if not TWILIO_AUTH_TOKEN or not TWILIO_ACCOUNT_SID:
    raise ValueError("Twilio credentials missing from environment")

INVENTORY_PATH = os.path.expanduser(os.getenv('INVENTORY_PATH', '~/ansible/inventory.ini'))
VAULT_PASS_FILE = os.path.expanduser(os.getenv('VAULT_PASS_FILE', '~/.vault_pass'))
AUTODL_FILTER_PATH = os.path.expanduser(os.getenv('AUTODL_FILTER_PATH', '~/.autodl/autodl.cfg'))
JELLYLINK_DB_PATH = os.path.expanduser(os.getenv('JELLYLINK_DB_PATH', '~/jellylink/jellylink.db'))
DOWNLOAD_DIR = os.path.expanduser(os.getenv('DOWNLOAD_DIR', '~/Downloads'))

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
        WHISPER_MODEL = WhisperModel("tiny.en", device="cpu", compute_type="int8")
    return WHISPER_MODEL

# =============================================================================
# SECURITY
# =============================================================================

def validate_twilio_request(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        signature = request.headers.get('X-Twilio-Signature', '')
        url = request.url.replace('http://', 'https://')
        post_vars = request.form.to_dict()
        if not validator.validate(url, post_vars, signature):
            if request.values.get('From', '') not in ALLOWED_NUMBERS:
                abort(403)
        return f(*args, **kwargs)
    return decorated

# =============================================================================
# COMMAND HANDLERS
# =============================================================================

def handle_disk_command():
    """Returns the current disk usage of the root partition."""
    try:
        usage = psutil.disk_usage('/')
        percent = usage.percent
        status = "🚨" if percent > 90 else "⚠️" if percent > 75 else "✅"
        return (
            f"💽 *Disk Usage (Root)*\n"
            f"Used: {usage.used // (2**30)}GB / {usage.total // (2**30)}GB ({percent}%)\n"
            f"Free: {usage.free // (2**30)}GB\n"
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
            response += f"\n\n*{host.upper()}*\n┣ ⏱️ {data.get('uptime','n/a')}\n┣ {data.get('net','n/a')} {data.get('docker','n/a')}\n┗ 🛡️ {data.get('knocks','0')} hits | ⛓️ {data.get('jails','0')} jails"
        except:
            response += f"\n\n🔴 *{host.upper()}* (down)"
    return response

def handle_update_command():
    subprocess.Popen(["sudo", "systemctl", "start", "ansible-pull.service"])
    return "🚀 Manual update triggered!"

def handle_pingall_command():
    try:
        out = subprocess.check_output(["ansible", "all", "-m", "ping", "-i", INVENTORY_PATH, "--vault-password-file", VAULT_PASS_FILE], timeout=10).decode()
        return f"🟢 Fleet ping\n✅ Online: {out.count('\"ping\": \"pong\"')}/{out.count('SUCCESS') + out.count('UNREACHABLE')}"
    except Exception as e: return f"❌ Ping failed: {str(e)}"

def handle_top_command():
    return f"📊 Local stats\n🖥️ CPU: {psutil.cpu_percent(interval=1):.1f}%\n🧠 RAM: {psutil.virtual_memory().percent:.1f}%"

def handle_uptime_command():
    res = subprocess.run(['uptime'], capture_output=True, text=True).stdout.strip()
    return f"⏱️ {res}"

def get_torrent_status():
    lines = []
    if shutil.which('qbittorrent-nox'):
        if subprocess.run(['pgrep', 'qbittorrent-nox'], capture_output=True).returncode == 0:
            lines.append("🌱 qBittorrent: Running")
    if shutil.which('transmission-remote'):
        res = subprocess.run(['transmission-remote', '-l'], capture_output=True, text=True).stdout
        count = len([l for l in res.splitlines() if l.strip() and not l.startswith('Sum')])
        lines.append(f"🌱 Transmission: {max(0, count-2)} torrents")
    return "\n".join(lines) or "❌ No torrent clients active."

def get_recent_media(limit=5):
    if not os.path.exists(JELLYLINK_DB_PATH): return "❌ DB not found"
    conn = sqlite3.connect(JELLYLINK_DB_PATH)
    rows = conn.execute("SELECT title, media_type, season, episode, strftime('%d/%m %H:%M', processed_date) FROM processed_media ORDER BY processed_date DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    if not rows: return "📭 No recent media"
    res = "📺 *Recent Media*\n"
    for t, m, s, e, d in rows:
        res += f"\n{'📺' if m=='TV' else '🎬'} {t}" + (f" S{s:02d}E{e:02d}" if m=='TV' else "") + f"\n   └ {d}"
    return res

def add_autodl_filter(name, ftype):
    fid = name.lower().replace(" ", "")
    if os.path.exists(AUTODL_FILTER_PATH):
        with open(AUTODL_FILTER_PATH, 'r') as f:
            if f"[filter {fid}]" in f.read(): return f"⚠️ Filter '{name}' exists."
    
    cfg = f"\n[filter {fid}]\nenabled=1\nmatch-sites=tl\n"
    cfg += f"shows={name}\nmatch-categories=TV - HD,TV\n" if ftype=='tv' else f"match-releases=*{name}*\nmatch-categories=Movies - HD,Movies\n"
    cfg += f"upload-watch-dir={DOWNLOAD_DIR}\n"
    
    with open(AUTODL_FILTER_PATH, 'a') as f: f.write(cfg)
    subprocess.run(['pkill', '-HUP', 'irssi'])
    return f"✅ Added '{fid}' for {name}"

# =============================================================================
# OLLAMA & WEBHOOK
# =============================================================================

def parse_with_ollama(text):
    """Refined system prompt to ensure Minty's identity and action mapping."""
    prompt = """
You are Minty, a chill home-lab commander bot. Use emojis, slang, and a friendly vibe.

Rules:
1. ALWAYS start every response with "Minty: "
2. If action is needed, include "ACTION: <command>" (e.g., ACTION: uptime).
3. Keep it short and fun.

Available actions: uptime, top, disk, fleet, pingall, update, seeds, recent, addtv <name>, addmovie <name>.
"""
    try:
        resp = ollama.chat(model='llama3.2:3b', messages=[{'role': 'system', 'content': prompt}, {'role': 'user', 'content': text}])
        return resp['message']['content'].strip()
    except: return ""

@app.route("/webhook", methods=['POST'])
@validate_twilio_request
def whatsapp_bot():
    body = (request.values.get('Body') or '').strip()
    media_url = request.values.get('MediaUrl0')
    
    # Process Voice
    if media_url and 'audio' in request.values.get('MediaContentType0', '').lower():
        r = requests.get(media_url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
        if r.status_code == 200:
            with open('/tmp/voice.ogg', 'wb') as f: f.write(r.content)
            segments, _ = get_whisper_model().transcribe('/tmp/voice.ogg')
            body = ' '.join([s.text for s in segments]).strip()

    if not body: return str(MessagingResponse().message("Minty: I didn't catch that! 🔊"))

    # AI Interpretation
    ai_reply = parse_with_ollama(body)
    reply_text = ai_reply or "Minty: Something went wrong with my brain! 🧠"
    
    # Action Execution
    if "ACTION:" in ai_reply:
        act = ai_reply.split("ACTION:")[1].strip().lower()
        res = ""
        if "uptime" in act: res = handle_uptime_command()
        elif any(x in act for x in ['fleet','stats','dashboard']): res = handle_fleet_command()
        elif "disk" in act: res = handle_disk_command()
        elif "update" in act: res = handle_update_command()
        elif "pingall" in act: res = handle_pingall_command()
        elif "top" in act: res = handle_top_command()
        elif "seeds" in act: res = get_torrent_status()
        elif "recent" in act: res = get_recent_media()
        elif "addtv" in act: res = add_autodl_filter(act.replace("addtv","").strip(), "tv")
        elif "addmovie" in act: res = add_autodl_filter(act.replace("addmovie","").strip(), "movie")
        
        if res: reply_text += f"\n\n{res}"

    resp = MessagingResponse()
    resp.message(reply_text)
    return str(resp)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
