#!/usr/bin/env python3
"""
WhatsApp Commander Bot - Minty Server Control via Twilio

Version History:
0.1 - 0.5: Filter management, pingall, reboots, and basic stats
0.6 - Added Fleet Dashboard integration
0.7 - Integrated remote uptime parsing for Dashboard
"""
import subprocess
import os
import re
import logging
import json
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

# --- LOGGING SETUP ---
logging.basicConfig(
    filename=os.path.expanduser('~/commander_audit.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)

# --- CONFIGURATION ---
ALLOWED_NUMBER = os.getenv('ALLOWED_NUMBER', 'whatsapp:+44XXXXXXXXXX')
AUTODL_CONFIG = os.path.expanduser('~/.autodl/autodl.cfg')
INVENTORY_PATH = os.path.expanduser('~/ansible/inventory.ini')

@app.route("/webhook", methods=['POST'])
def whatsapp_bot():
    incoming_msg = request.values.get('Body', '').strip()
    from_number = request.values.get('From', '')
    resp = MessagingResponse()
    msg = resp.message()

    if from_number != ALLOWED_NUMBER:
        logging.warning(f"Unauthorized access attempt from {from_number}")
        msg.body("Unauthorized access attempt.")
        return str(resp)

    logging.info(f"Command received: {incoming_msg}")
    incoming_lower = incoming_msg.lower()

    # 1. Full Fleet Dashboard (v0.7)
    if incoming_lower in ['stats', 'fleet', 'dashboard']:
        hosts = ['localhost', 'aws', 'az', 'pi']
        response = "🌍 *Minty Fleet Dashboard*\n"
        
        for host in hosts:
            try:
                # Read localhost directly, SSH to remote hosts
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
                response += f"\n└ ⏱️ {data['uptime']} (at {data['time']})"
            except Exception:
                response += f"\n🔴 *{host.upper()}* ⚠️ (Offline/Unreachable)"
        
        msg.body(response)

    # 2. Fleet-wide Ping
    elif incoming_lower == 'pingall':
        try:
            output = subprocess.check_output(["ansible", "all", "-m", "ping", "-i", INVENTORY_PATH]).decode()
            success_count = output.count('"ping": "pong"')
            total_hosts = output.count('=>')
            status_emoji = "🟢" if success_count == total_hosts else "🟡"
            msg.body(f"{status_emoji} *Fleet Health*\n✅ Online: {success_count}/{total_hosts}")
        except Exception as e:
            msg.body(f"❌ Error: {str(e)}")

    # 3. Targeted Reboot
    elif incoming_lower.startswith('reboot '):
        target_host = incoming_msg[7:].strip().lower()
        subprocess.Popen(["ansible", target_host, "-a", "/sbin/reboot", "-i", INVENTORY_PATH, "--become"])
        msg.body(f"🌀 Reboot command sent to: *{target_host}*")

    # 4. Manual Update Trigger
    elif incoming_lower == 'update':
        subprocess.Popen(["sudo", "systemctl", "start", "ansible-pull.service"])
        msg.body("🚀 Update triggered manually!")

    # 5. VPN Restart/Heal
    elif incoming_lower in ['healvpn', 'fixvpn']:
        subprocess.Popen([
            "ansible-playbook", os.path.expanduser("~/ansible/aws.yml"), 
            "--tags", "wireguard", "-i", INVENTORY_PATH,
            "--vault-password-file", os.path.expanduser("~/.vault_pass")
        ])
        msg.body("🔧 VPN healing initiated!")

    # Default Help Menu
    else:
        msg.body("Hi Martin! Commands:\n• *fleet*: Full Dashboard\n• *pingall*: Connectivity check\n• *reboot <host>*\n• *update*: Run ansible-pull")

    return str(resp)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
