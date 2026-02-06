#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WhatsApp Commander Bot - Minty Server Control via Twilio
Version 0.9.1 - Media Pipeline Integration + Seeds Fix
"""
import subprocess
import os
import logging
import json
import psutil
import re
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

logging.basicConfig(
    filename=os.path.expanduser('~/commander_audit.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)

# --- CONFIGURATION ---
ALLOWED_NUMBERS = [
    os.getenv('ALLOWED_NUMBER', 'whatsapp:+441174632546'),
    'whatsapp:+447375272694'
]
INVENTORY_PATH = os.path.expanduser('~/ansible/inventory.ini')
VAULT_PASS_FILE = os.path.expanduser('~/.vault_pass')
AUTODL_FILTER_PATH = os.path.expanduser('~/.autodl/autodl.cfg')
TORRENT_CLIENT = 'qbittorrent'  # or 'transmission'

def get_dynamic_hosts():
    """Parses inventory.ini for clean hostnames, skipping variables and duplicates."""
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
        logging.error(f"Failed to parse inventory: {e}")
    return hosts

def add_autodl_filter(show_name, filter_type='tv'):
    """Add a new filter to autodl-irssi config"""
    try:
        # Read existing config
        if os.path.exists(AUTODL_FILTER_PATH):
            with open(AUTODL_FILTER_PATH, 'r') as f:
                config = f.read()
        else:
            config = ""
        
        # Generate new filter ID (find highest existing + 1)
        filter_ids = re.findall(r'\[filter (\d+)\]', config)
        next_id = max([int(fid) for fid in filter_ids], default=0) + 1
        
        # Create filter block
        if filter_type == 'tv':
            new_filter = f"""
[filter {next_id}]
enabled = true
match-releases = {show_name}
match-categories = TV/x264,TV/x265,TV/HD
min-size = 100M
max-size = 5G
save-path = ~/Downloads/
"""
        else:  # movie
            new_filter = f"""
[filter {next_id}]
enabled = true
match-releases = {show_name}
match-categories = Movies/x264,Movies/x265,Movies/HD
min-size = 500M
max-size = 15G
save-path = ~/Downloads/
"""
        
        # Append and save
        with open(AUTODL_FILTER_PATH, 'a') as f:
            f.write(new_filter)
        
        # Reload autodl-irssi (if running)
        subprocess.run(['pkill', '-HUP', 'autodl-irssi'], check=False)
        
        return f"✅ Added filter #{next_id}: {show_name}"
    except Exception as e:
        logging.error(f"Failed to add filter: {e}")
        return f"❌ Error adding filter: {str(e)}"

def get_torrent_status():
    """Get current torrent seeding status"""
    try:
        # Try qBittorrent first
        try:
            result = subprocess.run(
                ['qbittorrent-nox', '--version'],
                capture_output=True,
                timeout=5,
                text=True
            )
            if result.returncode == 0:
                return "🌱 qBittorrent running\n📊 Use web UI for details"
        except FileNotFoundError:
            pass
        
        # Try transmission-remote
        try:
            result = subprocess.run(
                ['transmission-remote', '-l'],
                capture_output=True,
                timeout=5,
                text=True
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 2:
                    active = len(lines) - 2
                    return f"🌱 Transmission: {active} torrents"
                return "🌱 Transmission: 0 torrents"
        except FileNotFoundError:
            pass
        
        # Check if any torrent client process is running
        result = subprocess.run(
            ['pgrep', '-l', 'qbittorrent|transmission'],
            capture_output=True,
            text=True
        )
        if result.stdout:
            return f"🌱 Torrent client running:\n{result.stdout.strip()}"
        
        return "❌ No torrent client found"
        
    except Exception as e:
        return f"❌ Error: {str(e)}"

@app.route("/webhook", methods=['POST'])
def whatsapp_bot():
    incoming_msg = request.values.get('Body', '').strip()
    incoming_lower = incoming_msg.lower() 
    from_number = request.values.get('From', '')
    
    resp = MessagingResponse()
    msg = resp.message()

    if from_number not in ALLOWED_NUMBERS:
        msg.body("Unauthorized.")
        return str(resp)

    # 1. Full Fleet Dashboard
    if incoming_lower in ['fleet', 'stats', 'dashboard']:
        hosts = get_dynamic_hosts()
        response = "🌐 *Minty Fleet Dashboard*\n"
        
        for host in hosts:
            try:
                if host == 'localhost':
                    with open('/tmp/fleet_health.json', 'r') as f:
                        raw = f.read()
                else:
                    raw = subprocess.check_output(
                        ["ssh", host, "cat /tmp/fleet_health.json"], 
                        timeout=3
                    ).decode()
                
                data = json.loads(raw)
                response += f"\n{data['net']} *{host.upper()}* {data['docker']}"
                response += f"\n┣ ⏱️ {data['uptime']}"
                response += f"\n┗ 🛡️ {data.get('knocks', '0')} knocks | ⛓️ {data.get('jails', '0')} jailed"
            except Exception:
                response += f"\n🔴 *{host.upper()}* ⚠️ (Offline/Unreachable)"
        msg.body(response)

    # 2. Manual Update Trigger
    elif incoming_lower == 'update':
        subprocess.Popen(["sudo", "systemctl", "start", "ansible-pull.service"])
        msg.body("🚀 Update triggered manually!")

    # 3. Fleet-wide Ping
    elif incoming_lower == 'pingall':
        try:
            output = subprocess.check_output([
                "ansible", "all", "-m", "ping", "-i", INVENTORY_PATH,
                "--vault-password-file", VAULT_PASS_FILE
            ]).decode()
            success_count = output.count('"ping": "pong"')
            total_hosts = output.count('=>')
            msg.body(f"🟢 *Fleet Health*\n✅ Online: {success_count}/{total_hosts}")
        except Exception as e:
            msg.body(f"❌ Error: {str(e)}")

    # 4. System Statistics (Top)
    elif incoming_lower == 'top':
        try:
            cpu = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory().percent
            stats = f"📊 *Local Resources*\n🖥️ *CPU:* {cpu}%\n🧠 *RAM:* {mem}%"
            msg.body(stats)
        except Exception as e:
            msg.body(f"❌ Error: {str(e)}")

    # 5. Add TV Show Filter
    elif incoming_lower.startswith('addtv '):
        show_name = incoming_msg[6:].strip()  # Remove 'addtv '
        if show_name:
            result = add_autodl_filter(show_name, 'tv')
            msg.body(f"📺 *TV Filter*\n{result}")
        else:
            msg.body("Usage: addtv <show name>")

    # 6. Add Movie Filter
    elif incoming_lower.startswith('addmovie '):
        movie_name = incoming_msg[9:].strip()  # Remove 'addmovie '
        if movie_name:
            result = add_autodl_filter(movie_name, 'movie')
            msg.body(f"🎬 *Movie Filter*\n{result}")
        else:
            msg.body("Usage: addmovie <movie name>")

    # 7. Torrent Seed Status
    elif incoming_lower == 'seeds':
        result = get_torrent_status()
        msg.body(result)

    else:
        msg.body("Commands:\nfleet, update, pingall, top\naddtv <n>, addmovie <n>, seeds")

    return str(resp)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
