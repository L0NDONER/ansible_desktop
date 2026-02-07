#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WhatsApp Commander Bot - Minty Server Control via Twilio
Version 1.1 - Added natural language + voice support via Ollama & faster-whisper
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

# New imports for natural language & voice
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
    ]  # Fallback only

TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
if not TWILIO_AUTH_TOKEN:
    raise ValueError("TWILIO_AUTH_TOKEN environment variable is required")

TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
if not TWILIO_ACCOUNT_SID:
    raise ValueError("TWILIO_ACCOUNT_SID environment variable is required")

INVENTORY_PATH = os.path.expanduser(
    os.getenv('INVENTORY_PATH', '~/ansible/inventory.ini')
)
VAULT_PASS_FILE = os.path.expanduser(
    os.getenv('VAULT_PASS_FILE', '~/.vault_pass')
)
AUTODL_FILTER_PATH = os.path.expanduser(
    os.getenv('AUTODL_FILTER_PATH', '~/.autodl/autodl.cfg')
)
JELLYLINK_DB_PATH = os.path.expanduser(
    os.getenv('JELLYLINK_DB_PATH', '~/jellylink/jellylink.db')
)
DOWNLOAD_DIR = os.path.expanduser(
    os.getenv('DOWNLOAD_DIR', '~/Downloads')
)

TORRENT_CLIENT = os.getenv('TORRENT_CLIENT', 'qbittorrent')  # or 'transmission'

logging.basicConfig(
    filename=os.path.expanduser('~/commander_audit.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)
validator = RequestValidator(TWILIO_AUTH_TOKEN)

# Whisper model (lazy-loaded on first voice note)
WHISPER_MODEL = None


def get_whisper_model():
    """Lazy-load Whisper model on first use."""
    global WHISPER_MODEL
    if WHISPER_MODEL is None:
        try:
            WHISPER_MODEL = WhisperModel("tiny.en", device="cpu", compute_type="int8")
            logging.info("Whisper model loaded successfully")
        except Exception as e:
            logging.error(f"Whisper model load failed: {e}")
            raise
    return WHISPER_MODEL


# =============================================================================
# SECURITY & VALIDATION
# =============================================================================

def validate_twilio_request(f):
    """Validate Twilio webhook signature with Tailscale proxy support."""
    @wraps(f)
    def decorated(*args, **kwargs):
        signature = request.headers.get('X-Twilio-Signature', '')
        url = request.url.replace('http://', 'https://')
        post_vars = request.form.to_dict()

        if not validator.validate(url, post_vars, signature):
            logging.warning(f"Invalid Twilio signature from {request.remote_addr}")
            from_number = request.values.get('From', '')
            if from_number not in ALLOWED_NUMBERS:
                abort(403, "Invalid request signature and unauthorized number")
            logging.info(f"Signature validation failed but number whitelisted: {from_number}")

        return f(*args, **kwargs)
    return decorated


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_dynamic_hosts():
    """Parse Ansible inventory for clean hostnames."""
    hosts = ['localhost']
    if not os.path.exists(INVENTORY_PATH):
        return hosts

    try:
        with open(INVENTORY_PATH, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith(('[', '#', ';')):
                    continue
                hostname = line.split()[0]
                if '=' not in hostname and hostname.upper() != 'MINTY' and hostname not in hosts:
                    hosts.append(hostname)
    except Exception as e:
        logging.error(f"Inventory parse failed: {e}")

    return hosts


def filter_exists(show_name: str, filter_type: str = 'tv') -> bool:
    """Check if a filter section already exists to avoid duplicates."""
    if not os.path.exists(AUTODL_FILTER_PATH):
        return False

    filter_id = show_name.lower().replace(" ", "")
    try:
        with open(AUTODL_FILTER_PATH, 'r') as f:
            return bool(re.search(
                rf'^\[filter {re.escape(filter_id)}\]',
                f.read(),
                re.MULTILINE
            ))
    except Exception:
        return False


def add_autodl_filter(show_name: str, filter_type: str = 'tv') -> str:
    """Add filter only if it doesn't exist; reload irssi on success."""
    if filter_exists(show_name, filter_type):
        return f"⚠️ Filter for '{show_name}' already exists."

    try:
        filter_id = show_name.lower().replace(" ", "")

        if filter_type == 'tv':
            new_filter = f"""
[filter {filter_id}]
enabled=1
match-sites=tl
shows={show_name}
match-categories=TV - HD,TV
resolutions=720p,1080p,2160p
sources=WEB-DL,WEBDL,WEB,HDTV,BluRay
min-size=200MB
max-size=25GB
upload-watch-dir={DOWNLOAD_DIR}
"""
        else:  # movie
            new_filter = f"""
[filter {filter_id}]
enabled=1
match-sites=tl
match-releases=*{show_name}*
match-categories=Movies - HD,Movies
resolutions=1080p,2160p
min-size=1GB
max-size=40GB
upload-watch-dir={DOWNLOAD_DIR}
"""

        with open(AUTODL_FILTER_PATH, 'a') as f:
            f.write(new_filter + "\n")

        subprocess.run(['pkill', '-HUP', 'irssi'], check=False, timeout=5)

        logging.info(f"Added {filter_type} filter: {show_name}")
        return f"✅ Added '{filter_id}' for {show_name}"

    except Exception as e:
        logging.error(f"Filter add failed for {show_name}: {e}")
        return f"❌ Failed: {str(e)}"


def get_torrent_status() -> str:
    """Detect and report active torrent clients."""
    lines = []

    if shutil.which('qbittorrent-nox'):
        try:
            result = subprocess.run(
                ['pgrep', 'qbittorrent-nox'],
                capture_output=True,
                timeout=3
            )
            if result.returncode == 0:
                lines.append("🌱 qBittorrent is running")
        except Exception:
            pass

    if shutil.which('transmission-remote'):
        try:
            result = subprocess.run(
                ['transmission-remote', '-l'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                count = len([
                    l for l in result.stdout.splitlines()
                    if l.strip() and not l.startswith('Sum')
                ])
                lines.append(f"🌱 Transmission: {max(0, count-2)} torrents")
        except Exception:
            pass

    return "\n".join(lines) or "❌ No active torrent client found."


def get_recent_media(limit: int = 5) -> str:
    """Query JellyLink database for recently processed media."""
    if not os.path.exists(JELLYLINK_DB_PATH):
        return "❌ JellyLink database not found"

    try:
        conn = sqlite3.connect(JELLYLINK_DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT title, media_type, season, episode, year,
                   strftime('%d/%m %H:%M', processed_date) as proc_date
            FROM processed_media
            ORDER BY processed_date DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return "📭 No recent media found"

        response = f"📺 *Recent Media (last {len(rows)})*\n"
        for title, mtype, season, episode, year, proc_date in rows:
            if mtype == 'TV':
                response += f"\n📺 {title} S{season:02d}E{episode:02d}"
            else:
                year_str = f" ({year})" if year else ""
                response += f"\n🎬 {title}{year_str}"
            response += f"\n   └ {proc_date}"

        return response

    except Exception as e:
        logging.error(f"JellyLink DB query failed: {e}")
        return f"❌ Database error: {str(e)}"


# =============================================================================
# COMMAND HANDLERS
# =============================================================================

def handle_fleet_command():
    """Generate fleet dashboard with health status for all hosts."""
    hosts = get_dynamic_hosts()
    response = "🌐 *Minty Fleet Dashboard*"

    for host in hosts:
        try:
            if host == 'localhost':
                with open('/tmp/fleet_health.json', 'r') as f:
                    data = json.load(f)
            else:
                raw = subprocess.check_output(
                    ["ssh", "-o", "ConnectTimeout=3", host, "cat /tmp/fleet_health.json"],
                    timeout=4
                ).decode()
                data = json.loads(raw)

            response += f"\n\n*{host.upper()}*"
            response += f"\n┣ ⏱️ {data.get('uptime', 'n/a')}"
            response += f"\n┣ {data.get('net', 'n/a')}  {data.get('docker', 'n/a')}"
            response += f"\n┗ 🛡️ {data.get('knocks', '0')} knocks | ⛓️ {data.get('jails', '0')} jailed"

        except Exception:
            response += f"\n\n🔴 *{host.upper()}*  (unreachable)"

    return response or "No hosts found."


def handle_update_command():
    """Trigger manual ansible-pull update."""
    try:
        subprocess.Popen(["sudo", "systemctl", "start", "ansible-pull.service"])
        return "🚀 Manual update triggered!"
    except Exception as e:
        return f"❌ Update trigger failed: {str(e)}"


def handle_pingall_command():
    """Ping all hosts in Ansible inventory."""
    try:
        out = subprocess.check_output(
            [
                "ansible", "all", "-m", "ping",
                "-i", INVENTORY_PATH,
                "--vault-password-file", VAULT_PASS_FILE
            ],
            timeout=10
        ).decode()

        success = out.count('"ping": "pong"')
        total = out.count('SUCCESS') + out.count('UNREACHABLE')
        return f"🟢 Fleet ping\n✅ Online: {success}/{total}"

    except Exception as e:
        return f"❌ Ping failed: {str(e)}"


def handle_top_command():
    """Get local system resource usage."""
    try:
        cpu = f"{psutil.cpu_percent(interval=1.2):.1f}%"
        mem = f"{psutil.virtual_memory().percent:.1f}%"
        return f"📊 Local stats\n🖥️ CPU: {cpu}\n🧠 RAM: {mem}"
    except Exception as e:
        return f"❌ Stats error: {str(e)}"


def handle_uptime_command():
    """Get real system uptime."""
    try:
        result = subprocess.run(['uptime'], capture_output=True, text=True, timeout=5).stdout.strip()
        return f"⏱️ {result}"
    except Exception as e:
        return f"❌ Uptime check failed: {str(e)}"


def get_help_text():
    """Return help text with available commands."""
    return (
        "Available commands:\n"
        "• fleet / stats / dashboard\n"
        "• update\n"
        "• pingall\n"
        "• top\n"
        "• uptime\n"
        "• addtv <show>\n"
        "• addmovie <title>\n"
        "• seeds\n"
        "• recent\n\n"
        "You can also speak or write naturally (e.g. 'whats my uptime' or 'add tv the office')"
    )


# =============================================================================
# NATURAL LANGUAGE PARSING WITH OLLAMA
# =============================================================================

def parse_with_ollama(text: str) -> str:
    """Send text to Ollama and return its response."""
    try:
        system_prompt = """
You are Minty, a chill home-lab commander bot. Understand casual language, typos, slang.
Available actions:
- uptime → show system uptime
- top → CPU/RAM stats
- fleet / dashboard / stats → fleet health overview
- pingall → ping all hosts
- update → trigger ansible-pull
- addtv <show> → add TV filter
- addmovie <title> → add movie filter
- seeds → torrent status
- recent → last 5 media items

Rules:
- Reply short, fun, with emojis.
- If action needed, start with "ACTION: command args" then friendly text.
- If unclear, ask nicely.
- No long explanations unless asked.
"""

        response = ollama.chat(model='llama3.2:3b', messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': text}
        ])
        return response['message']['content'].strip()

    except Exception as e:
        logging.error(f"Ollama failed: {e}")
        return ""


# =============================================================================
# WEBHOOK ENDPOINT
# =============================================================================

@app.route("/webhook", methods=['POST'])
@validate_twilio_request
def whatsapp_bot():
    """Main webhook handler for WhatsApp messages."""
    incoming_msg = (request.values.get('Body') or '').strip()
    from_number = request.values.get('From', '')
    media_url = request.values.get('MediaUrl0')
    media_type = request.values.get('MediaContentType0', '')

    resp = MessagingResponse()
    msg = resp.message()

    if from_number not in ALLOWED_NUMBERS:
        msg.body("Unauthorized number.")
        logging.warning(f"Unauthorized access attempt from {from_number}")
        return str(resp)

    logging.info(f"Command from {from_number}: {incoming_msg}")

    # Handle voice note if present
    audio_path = None
    if media_url and 'audio' in media_type.lower():
        logging.info(f"Voice note detected: {media_url}")
        try:
            logging.info("Downloading audio from Twilio...")
            r = requests.get(media_url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
            logging.info(f"Audio download status: {r.status_code}, size: {len(r.content)} bytes")
            
            if r.status_code == 200:
                audio_path = '/tmp/whatsapp_voice.ogg'
                with open(audio_path, 'wb') as f:
                    f.write(r.content)
                logging.info(f"Audio saved to {audio_path}")

                logging.info("Loading Whisper model...")
                model = get_whisper_model()
                logging.info("Transcribing audio...")
                segments, _ = model.transcribe(audio_path, beam_size=5)
                incoming_msg = ' '.join([s.text for s in segments]).strip()

                logging.info(f"Transcribed voice: '{incoming_msg}' (length: {len(incoming_msg)})")
            else:
                logging.error(f"Failed to download audio: HTTP {r.status_code}")
                incoming_msg = ""
        except Exception as e:
            logging.error(f"Voice processing failed: {e}", exc_info=True)
            incoming_msg = ""
        finally:
            if audio_path and os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                    logging.info(f"Cleaned up {audio_path}")
                except Exception:
                    pass

    if not incoming_msg:
        msg.body("Couldn't understand the message or voice note.")
        return str(resp)

    incoming_lower = incoming_msg.lower()

    # Try natural language via Ollama first
    ollama_reply = parse_with_ollama(incoming_msg)
    
    reply_text = None
    executed = False

    # Parse for ACTION: and execute real handler
    if ollama_reply and ollama_reply.startswith("ACTION:"):
        action_part = ollama_reply.split("ACTION:", 1)[1].strip().lower()

        if "uptime" in action_part:
            reply_text = handle_uptime_command()
            executed = True
        elif any(x in action_part for x in ['fleet', 'dashboard', 'stats']):
            reply_text = handle_fleet_command()
            executed = True
        elif "update" in action_part:
            reply_text = handle_update_command()
            executed = True
        elif "pingall" in action_part:
            reply_text = handle_pingall_command()
            executed = True
        elif "top" in action_part:
            reply_text = handle_top_command()
            executed = True
        elif action_part.startswith("addtv "):
            show = action_part[6:].strip()
            if show:
                reply_text = f"📺 TV filter\n{add_autodl_filter(show, 'tv')}"
                executed = True
        elif action_part.startswith("addmovie "):
            movie = action_part[9:].strip()
            if movie:
                reply_text = f"🎬 Movie filter\n{add_autodl_filter(movie, 'movie')}"
                executed = True
        elif "seeds" in action_part:
            reply_text = get_torrent_status()
            executed = True
        elif "recent" in action_part:
            reply_text = get_recent_media(5)
            executed = True

        if executed:
            reply_text += "\n\n(Minty AI parsed your request 😎)"

    # Fallback to exact string matching if Ollama didn't handle it
    if not executed:
        if incoming_lower in ['fleet', 'stats', 'dashboard']:
            reply_text = handle_fleet_command()
        elif incoming_lower == 'update':
            reply_text = handle_update_command()
        elif incoming_lower == 'pingall':
            reply_text = handle_pingall_command()
        elif incoming_lower == 'top':
            reply_text = handle_top_command()
        elif incoming_lower == 'uptime':
            reply_text = handle_uptime_command()
        elif incoming_lower.startswith('addtv '):
            show = incoming_msg[6:].strip()
            if show:
                reply_text = f"📺 TV filter\n{add_autodl_filter(show, 'tv')}"
            else:
                reply_text = "Usage: addtv Show Name"
        elif incoming_lower.startswith('addmovie '):
            movie = incoming_msg[9:].strip()
            if movie:
                reply_text = f"🎬 Movie filter\n{add_autodl_filter(movie, 'movie')}"
            else:
                reply_text = "Usage: addmovie Movie Name"
        elif incoming_lower == 'seeds':
            reply_text = get_torrent_status()
        elif incoming_lower == 'recent':
            reply_text = get_recent_media(5)
        elif ollama_reply:
            reply_text = ollama_reply
        else:
            reply_text = get_help_text()

    msg.body(reply_text)
    return str(resp)


# =============================================================================
# APPLICATION ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    # For production use gunicorn + nginx reverse proxy with HTTPS
    app.run(host='0.0.0.0', port=5000, debug=False)
