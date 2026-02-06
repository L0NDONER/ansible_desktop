#!/usr/bin/env python3
"""
WhatsApp Commander Bot - Minty Server Control via Twilio
Version 0.8.2 - Refined Inventory Parsing & Display
"""
import subprocess
import os
import logging
import json
import psutil
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
    os.getenv('ALLOWED_NUMBER', 'whatsapp:+441174632546'), # Primary Number
    'whatsapp:+447375272694'                              # Your EE Number
]
INVENTORY_PATH = os.path.expanduser('~/ansible/inventory.ini')
VAULT_PASS_FILE = os.path.expanduser('~/.vault_pass')

def get_dynamic_hosts():
    """Parses inventory.ini to return clean hostnames, skipping variables and headers."""
    hosts = ['localhost']
    if not os.path.exists(INVENTORY_PATH):
        return hosts
    try:
        with open(INVENTORY_PATH, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip comments, empty lines, and group headers
                if not line or line.startswith(('[', '#', ';')):
                    continue
                # Extract the hostname, ignore everything after the first space (variables)
                hostname = line.split()[0]
                # Filter out specific Ansible variables if they appear as lines
                if '=' not in hostname and hostname not in hosts:
                    hosts.append(hostname)
    except Exception as e:
        logging.error(f"Failed to parse inventory: {e}")
    return hosts

@app.route("/webhook", methods=['POST'])
def whatsapp_bot():
    incoming_msg = request.values.get('Body', '').strip()
    incoming_lower = incoming_msg.lower() 
    from_number = request.values.get('From', '')
    
    resp = MessagingResponse()
    msg = resp.message()

    if from_number not in ALLOWED_NUMBERS:
        logging.warning(f"Unauthorized access from {from_number}")
        msg.body("Unauthorized access attempt.")
        return str(resp)

    # 1. Full Fleet Dashboard
    if incoming_lower in ['fleet', 'stats', 'dashboard']:
        hosts = get_dynamic_hosts()
        response = "🌐 *Minty Fleet Dashboard*\n"
        
        for host in hosts:
            # Skip aliases that cause duplicates or noise in the screenshot
            if host.upper() in ['MINTY']: 
                continue
                
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
                response += f"\n┗ 🛡️ {data.get('knocks', '0')} knocks blocked"
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
            status_emoji = "🟢" if success_count == total_hosts else "🟡"
            msg.body(f"{status_emoji} *Fleet Health*\n✅ Online: {success_count}/{total_hosts}")
        except Exception as e:
            msg.body(f"❌ Error: {str(e)}")

    # 4. System Statistics (Top)
    elif incoming_lower == 'top':
        try:
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            stats = (
                "📊 *Local System Resources*\n"
                f"🖥️ *CPU:* {cpu_usage}%\n"
                f"🧠 *RAM:* {memory.percent}% ({memory.available // (1024**2)}MB free)\n"
                f"💾 *Disk:* {disk.percent}% usage"
            )
            if os.path.exists("/sys/class/thermal/thermal_zone0/temp"):
                with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                    temp = int(f.read()) / 1000
                    stats += f"\n🌡️ *Temp:* {temp:.1f}°C"
            msg.body(stats)
        except Exception as e:
            msg.body(f"❌ Error fetching stats: {str(e)}")

    else:
        msg.body("Valid commands: fleet, update, pingall, top")

    return str(resp)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
