import os
import sys
import requests
from flask import Flask, request, jsonify

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import anthropic
from agente import SYSTEM_PROMPT, TOOLS, ejecutar_herramienta, BIENVENIDA

app = Flask(__name__)
client = anthropic.Anthropic()

IG_TOKEN = os.environ.get("IG_TOKEN", "")
VERIFY_TOKEN = "revo_webhook_token"
conversaciones = {}

def procesar_mensaje(sender_id, texto):
    if sender_id not in conversaciones:
        conversaciones[sender_id] = [{"role": "assistant", "content": BIENVENIDA}]
    messages = conversaciones[sender_id]
    messages.append({"role": "user", "content": texto})
    while True:
        respuesta = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=1024,
            system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            tools=TOOLS,
            messages=messages,
        )
        if respuesta.stop_reason == "end_turn":
            texto_respuesta = ""
            for bloque in respuesta.content:
                if bloque.type == "text":
                    texto_respuesta = bloque.text
            messages.append({"role": "assistant", "content": respuesta.content})
            return texto_respuesta
        elif respuesta.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": respuesta.content})
            resultados = []
            for bloque in respuesta.content:
                if bloque.type == "tool_use":
                    resultado = ejecutar_herramienta(bloque.name, bloque.input)
                    resultados.append({"type": "tool_result", "tool_use_id": bloque.id, "content": resultado})
            messages.append({"role": "user", "content": resultados})
        else:
            return "Disculpa, hubo un error."

def enviar_respuesta(recipient_id, texto):
    url = "https://graph.instagram.com/v21.0/me/messages"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": texto}, "messaging_type": "RESPONSE", "access_token": IG_TOKEN}
    requests.post(url, json=payload)

@app.route("/webhook", methods=["GET"])
def verificar_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Token invalido", 403

@app.route("/webhook", methods=["POST"])
def recibir_mensaje():
    data = request.get_json()
    if data.get("object") == "instagram":
        for entry in data.get("entry", []):
            for event in entry.get("messaging", []):
                sender_id = event.get("sender", {}).get("id")
                mensaje = event.get("message", {}).get("text", "")
                if sender_id and mensaje:
                    respuesta = procesar_mensaje(sender_id, mensaje)
                    enviar_respuesta(sender_id, respuesta)
    return jsonify({"status": "ok"}), 200

@app.route("/", methods=["GET"])
def home():
    return "REVO Agente activo", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
