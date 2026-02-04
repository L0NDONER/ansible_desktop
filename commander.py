#!/usr/bin/env python3
"""
WhatsApp Commander Bot - Minty Server Control via Twilio

Version History:
0.1 - Initial TV/Movie filter management
0.2 - Added manual update trigger
0.3 - Added seeding status integration
0.4 - Added VPN healing and system stats commands

Commands:
- update: Trigger ansible-pull manually
- healvpn/fixvpn: Restart VPN infrastructure
- addtv <name>: Add TV show filter to autodl
- addmovie <name>: Add movie filter to autodl
- seeding/status: Check seeding ratios
- stats/system: System resource usage
"""
import subprocess
import os
import re
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# Configuration - get from environment or use defaults
ALLOWED_NUMBER = os.getenv('ALLOWED_NUMBER', 'whatsapp:+44XXXXXXXXXX')
DOWNLOADS_PATH = os.getenv('DOWNLOADS_PATH', '/home/martin/downloads')
AUTODL_CONFIG = os.path.expanduser('~/.autodl/autodl.cfg')

def sanitize_filter_name(name):
    """Convert show/movie name to valid filter name"""
    return re.sub(r'[^a-z0-9_]', '_', name.lower())

def add_tv_filter(show_name):
    """Add a TV show filter to autodl.cfg"""
    filter_name = sanitize_filter_name(show_name)
    
    filter_config = f"""
[filter {filter_name}]
enabled=true
match-releases=*{show_name}*
match-sites=ipt,tl
resolutions=1080p,2160p
min-size=500MB
"""
    
    try:
        # Check if filter already exists
        with open(AUTODL_CONFIG, 'r') as f:
            content = f.read()
            if f'[filter {filter_name}]' in content:
                return f"❌ Filter '{show_name}' already exists!"
        
        # Append new filter
        with open(AUTODL_CONFIG, 'a') as f:
            f.write(filter_config)
        
        # Reload autodl-irssi by sending command to screen session
        subprocess.run(
            ['screen', '-S', 'irssi', '-X', 'stuff', '/autodl update\n'],
            check=False
        )
        
        return f"✅ Added TV show: {show_name}"
    except Exception as e:
        return f"❌ Error adding filter: {str(e)}"

def add_movie_filter(movie_name):
    """Add a movie filter to autodl.cfg"""
    filter_name = sanitize_filter_name(movie_name)
    
    filter_config = f"""
[filter {filter_name}]
enabled=true
match-releases=*{movie_name}*
match-sites=ipt,tl
resolutions=1080p,2160p
min-size=1GB
max-size=30GB
"""
    
    try:
        # Check if filter already exists
        with open(AUTODL_CONFIG, 'r') as f:
            content = f.read()
            if f'[filter {filter_name}]' in content:
                return f"❌ Filter '{movie_name}' already exists!"
        
        # Append new filter
        with open(AUTODL_CONFIG, 'a') as f:
            f.write(filter_config)
        
        # Reload autodl-irssi by sending command to screen session
        subprocess.run(
            ['screen', '-S', 'irssi', '-X', 'stuff', '/autodl update\n'],
            check=False
        )
        
        return f"✅ Added movie: {movie_name}"
    except Exception as e:
        return f"❌ Error adding filter: {str(e)}"

@app.route("/webhook", methods=['POST'])
def whatsapp_bot():
    incoming_msg = request.values.get('Body', '').strip()
    from_number = request.values.get('From', '')
    resp = MessagingResponse()
    msg = resp.message()

    if from_number != ALLOWED_NUMBER:
        msg.body("Unauthorized access attempt.")
        return str(resp)

    # Parse command
    incoming_lower = incoming_msg.lower()

    # Manual Update Trigger
    if incoming_lower == 'update':
        try:
            subprocess.Popen(["sudo", "systemctl", "start", "ansible-pull.service"])
            msg.body("🚀 Update triggered manually! Expect a 'Smooth as butter' message soon.")
        except Exception as e:
            msg.body(f"❌ Error: {str(e)}")

    # VPN Restart/Heal
    elif incoming_lower == 'healvpn' or incoming_lower == 'fixvpn':
        try:
            subprocess.Popen([
                "ansible-playbook", 
                os.path.expanduser("~/ansible/aws.yml"), 
                "--tags", "wireguard",
                "-i", os.path.expanduser("~/ansible/inventory.ini"),
                "--vault-password-file", os.path.expanduser("~/.vault_pass")
            ])
            msg.body("🔧 VPN healing initiated! Check status in 30 seconds.")
        except Exception as e:
            msg.body(f"❌ Error: {str(e)}")

    # Add TV Show
    elif incoming_lower.startswith('addtv '):
        show_name = incoming_msg[6:].strip()
        if show_name:
            result = add_tv_filter(show_name)
            msg.body(result)
        else:
            msg.body("❌ Usage: addtv <show name>")

    # Add Movie
    elif incoming_lower.startswith('addmovie '):
        movie_name = incoming_msg[9:].strip()
        if movie_name:
            result = add_movie_filter(movie_name)
            msg.body(result)
        else:
            msg.body("❌ Usage: addmovie <movie name>")

    # Seeding Status Summary
    elif 'seeding' in incoming_lower or 'status' in incoming_lower:
        try:
            from dashboard import get_seeding_status
            data, _ = get_seeding_status(DOWNLOADS_PATH)
            safe_count = sum(1 for f in data if f["IsSafe"])
            
            response = f"🌱 *Minty Seeding Status*\n"
            response += f"📦 Total Files: {len(data)}\n"
            response += f"✅ Ready for Cleanup: {safe_count}\n"
            
            if safe_count > 0:
                response += "\n*Safe to remove:* " + ", ".join([f["File"] for f in data if f["IsSafe"]][:3])
            msg.body(response)
        except Exception as e:
            msg.body(f"⚠️ Dashboard error: {str(e)}")

    # System Stats
    elif incoming_lower == 'stats' or incoming_lower == 'system':
        try:
            # Get uptime
            uptime = subprocess.check_output(['uptime', '-p']).decode().strip()
            # Get disk usage
            df = subprocess.check_output(['df', '-h', '/']).decode().split('\n')[1].split()
            disk_used = df[4]
            # Get memory
            mem = subprocess.check_output(['free', '-h']).decode().split('\n')[1].split()
            mem_used = f"{mem[2]}/{mem[1]}"
            
            response = f"💻 *Minty System Stats*\n"
            response += f"⏰ {uptime}\n"
            response += f"💾 Disk: {disk_used} used\n"
            response += f"🧠 RAM: {mem_used}\n"
            msg.body(response)
        except Exception as e:
            msg.body(f"❌ Error: {str(e)}")

    else:
        msg.body("Hi Martin! Commands:\n• update\n• healvpn / fixvpn\n• addtv <show name>\n• addmovie <movie name>\n• seeding / status\n• stats / system")

    return str(resp)

@app.route("/", methods=['GET'])
def health_check():
    return "Commander Bot is running! 🚀", 200

if __name__ == "__main__":
    # Run Flask app
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
