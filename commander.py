#!/usr/bin/env python3
"""
WhatsApp Commander Bot - Minty Server Control via Twilio
"""
import subprocess
import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# Configuration - get from environment or use defaults
AUTHORIZED_NUMBER = os.getenv('AUTHORIZED_NUMBER', 'whatsapp:+447375272694')
DOWNLOADS_PATH = os.getenv('DOWNLOADS_PATH', '/home/martin/downloads')

@app.route("/webhook", methods=['POST'])
def whatsapp_bot():
    incoming_msg = request.values.get('Body', '').lower()
    from_number = request.values.get('From', '')
    resp = MessagingResponse()
    msg = resp.message()

    if from_number != AUTHORIZED_NUMBER:
        msg.body("Unauthorized access attempt.")
        return str(resp)

    # Manual Update Trigger
    if 'update' in incoming_msg:
        try:
            subprocess.Popen(["sudo", "systemctl", "start", "ansible-pull.service"])
            msg.body("🚀 Update triggered manually! Expect a 'Smooth as butter' message soon.")
        except Exception as e:
            msg.body(f"❌ Error: {str(e)}")

    # Seeding Status Summary
    elif 'seeding' in incoming_msg or 'status' in incoming_msg:
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

    else:
        msg.body("Hi Martin! Commands: 'update', 'seeding', or 'status'.")

    return str(resp)

@app.route("/", methods=['GET'])
def health_check():
    return "Commander Bot is running! 🚀", 200

if __name__ == "__main__":
    # Run Flask app
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
