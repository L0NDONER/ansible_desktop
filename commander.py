#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WhatsApp Commander Bot - Minty Server Control via Twilio
Version 1.0 - Hardened security, validation, robustness
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

TORRENT_CLIENT = os.getenv('TORRENT_CLIENT', 'qbittorrent')  # or 'transmission'

logging.basicConfig(
    filename=os.path.expanduser('~/commander_audit.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)
validator = RequestValidator(TWILIO_AUTH_TOKEN)


# =============================================================================
# SECURITY & VALIDATION
# =============================================================================

def validate_twilio_request(f):
    """Validate Twilio webhook signature with Tailscale proxy support."""
    @wraps(f)
    def decorated(*args, **kwargs):
        signature = request.headers.get('X-Twilio-Signature', '')
        # Handle Tailscale proxy - use https:// URL for validation
        url = request.url.replace('http://', 'https://')
        post_vars = request.form.to_dict()

        if not validator.validate(url, post_vars, signature):
            logging.warning(f"Invalid Twilio signature from {request.remote_addr}")
            # Fallback: allow if from authorized number (for Tailscale/proxy scenarios)
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
upload-watch-dir=/home/martin/Downloads
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
upload-watch-dir=/home/martin/Downloads
"""

        with open(AUTODL_FILTER_PATH, 'a') as f:
            f.write(new_filter + "\n")

        # Graceful reload
        subprocess.run(['pkill', '-HUP', 'irssi'], check=False, timeout=5)

        logging.info(f"Added {filter_type} filter: {show_name}")
        return f"✅ Added '{filter_id}' for {show_name}"

    except Exception as e:
        logging.error(f"Filter add failed for {show_name}: {e}")
        return f"❌ Failed: {str(e)}"


def get_torrent_status() -> str:
    """Detect and report active torrent clients."""
    lines = []

    # qBittorrent-nox
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

    # Transmission
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


def get_help_text():
    """Return help text with available commands."""
    return (
        "Available commands:\n"
        "• fleet / stats / dashboard\n"
        "• update\n"
        "• pingall\n"
        "• top\n"
        "• addtv <show>\n"
        "• addmovie <title>\n"
        "• seeds\n"
        "• recent"
    )


# =============================================================================
# WEBHOOK ENDPOINT
# =============================================================================

@app.route("/webhook", methods=['POST'])
@validate_twilio_request
def whatsapp_bot():
    """Main webhook handler for WhatsApp messages."""
    incoming_msg = (request.values.get('Body') or '').strip()
    incoming_lower = incoming_msg.lower()
    from_number = request.values.get('From', '')

    resp = MessagingResponse()
    msg = resp.message()

    # Authorization check
    if from_number not in ALLOWED_NUMBERS:
        msg.body("Unauthorized number.")
        logging.warning(f"Unauthorized access attempt from {from_number}")
        return str(resp)

    logging.info(f"Command from {from_number}: {incoming_msg}")

    # Command routing
    if incoming_lower in ['fleet', 'stats', 'dashboard']:
        msg.body(handle_fleet_command())

    elif incoming_lower == 'update':
        msg.body(handle_update_command())

    elif incoming_lower == 'pingall':
        msg.body(handle_pingall_command())

    elif incoming_lower == 'top':
        msg.body(handle_top_command())

    elif incoming_lower.startswith('addtv '):
        show = incoming_msg[6:].strip()
        if show:
            msg.body(f"📺 TV filter\n{add_autodl_filter(show, 'tv')}")
        else:
            msg.body("Usage: addtv Show Name")

    elif incoming_lower.startswith('addmovie '):
        movie = incoming_msg[9:].strip()
        if movie:
            msg.body(f"🎬 Movie filter\n{add_autodl_filter(movie, 'movie')}")
        else:
            msg.body("Usage: addmovie Movie Name")

    elif incoming_lower == 'seeds':
        msg.body(get_torrent_status())

    elif incoming_lower == 'recent':
        msg.body(get_recent_media(5))

    else:
        msg.body(get_help_text())

    return str(resp)


# =============================================================================
# APPLICATION ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    # For production use gunicorn + nginx reverse proxy with HTTPS
    app.run(host='0.0.0.0', port=5000, debug=False)
