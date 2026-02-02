from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import subprocess

app = Flask(__name__)

# SECURITY: Replace with your actual WhatsApp-enabled mobile number
AUTHORIZED_NUMBER = "whatsapp:+447375272694" 

@app.route("/webhook", methods=['POST'])
def whatsapp_bot():
    incoming_msg = request.values.get('Body', '').lower()
    from_number = request.values.get('From', '')
    resp = MessagingResponse()
    msg = resp.message()

    if from_number != AUTHORIZED_NUMBER:
        msg.body("Unauthorized access attempt.")
        return str(resp)

    # COMMAND: Trigger the 1AM Pull manually
    if 'update' in incoming_msg:
        try:
            # Starts the systemd service defined in your gitops-setup.yml
            subprocess.Popen(["sudo", "systemctl", "start", "ansible-pull.service"])
            msg.body("🚀 Update triggered manually! Expect a 'Smooth as butter' message soon.")
        except Exception as e:
            msg.body(f"❌ Error: {str(e)}")

    return str(resp)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
