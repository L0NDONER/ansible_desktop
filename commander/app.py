import os
import logging
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from groq import Groq

from . import config
from . import actions

app = Flask(__name__)

# Command Registry: maps keywords to handler functions
KEYWORD_COMMANDS = {
    'inspect': (actions.handle_inspect_command, ['inspect', 'motherboard', 'cpu', 'chip']),
    'weather': (actions.handle_weather_command, ['weather']),
    'disk': (actions.handle_disk_command, ['disk']),
    'pingall': (actions.handle_pingall_command, ['pingall']),
    'fleet': (actions.handle_fleet_command, ['fleet']),
    'seed': (actions.handle_seed_command, ['seed']),
}

# Prefix Commands: require arguments after the command
PREFIX_COMMANDS = {
    'addtv': actions.handle_addtv_command,
    'addmovies': actions.handle_addmovies_command,
}


def route_command(body):
    """Route incoming message to appropriate command handler"""
    
    # Check prefix commands first (addtv, addmovies, etc.)
    for prefix, handler in PREFIX_COMMANDS.items():
        if body.startswith(f"{prefix} "):
            argument = body.replace(f"{prefix} ", "", 1).strip()
            return handler(argument)
    
    # Check keyword commands (weather, disk, etc.)
    for cmd_name, (handler, keywords) in KEYWORD_COMMANDS.items():
        if any(keyword in body for keyword in keywords):
            # Special case: seed command needs the full body
            if cmd_name == 'seed':
                return handler(body)
            return handler()
    
    # No command matched
    return None


def get_ai_fallback(body):
    """Get AI response from Groq when no command matches"""
    try:
        client = Groq(api_key=config.GROQ_API_KEY)
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "system",
                    "content": "You are Minty, a chill home-lab commander. Keep responses concise and start with 'Minty: '."
                },
                {"role": "user", "content": body}
            ],
            max_tokens=300,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"Groq error: {e}")
        return "Minty: Brain overclocked, give me a sec! 🧠⚡"


@app.route("/webhook", methods=['POST'])
def whatsapp_bot():
    """Main webhook handler for incoming WhatsApp messages"""
    
    # Get incoming message
    body = (request.values.get('Body') or '').strip().lower()
    
    # Route to command or fallback to AI
    reply_text = route_command(body) or get_ai_fallback(body)
    
    # Send response via Twilio
    twiml = MessagingResponse()
    twiml.message(reply_text)
    return str(twiml)


if __name__ == "__main__":
    app.run(port=5000)
