"""
instagram_bridge.py — Webhook Flask para recibir DMs de Instagram
"""
import os
import sys
import json
import requests
from flask import Flask, request, jsonify, Response

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import anthropic
from agente import SYSTEM_PROMPT, TOOLS, ejecutar_herramienta, BIENVENIDA

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # Fix acentos en respuestas JSON
client = anthropic.Anthropic()

IG_TOKEN = os.environ.get("IG_TOKEN", "")
VERIFY_TOKEN = "revo_webhook_token"
conversaciones: dict = {}

def procesar_mensaje(sender_id: str, texto: str) -> list[str]:
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
            # Separar en múltiples mensajes por [MSG]
            partes = [p.strip() for p in texto_respuesta.split("[MSG]") if p.strip()]
            return partes if partes else [texto_respuesta]
        elif respuesta.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": respuesta.content})
            resultados = []
            for bloque in respuesta.content:
                if bloque.type == "tool_use":
                    resultado = ejecutar_herramienta(bloque.name, bloque.input)
                    resultados.append({"type": "tool_result", "tool_use_id": bloque.id, "content": resultado})
            messages.append({"role": "user", "content": resultados})
        else:
            return ["Disculpá, hubo un error. Por favor escribinos de nuevo."]

def enviar_respuesta(recipient_id: str, texto: str):
    url = f"https://graph.instagram.com/v21.0/me/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": texto},
        "messaging_type": "RESPONSE",
        "access_token": IG_TOKEN
    }
    requests.post(url, json=payload, headers={"Content-Type": "application/json; charset=utf-8"})

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
                    respuestas = procesar_mensaje(sender_id, mensaje)
                    for parte in respuestas:
                        enviar_respuesta(sender_id, parte)
    return jsonify({"status": "ok"}), 200
@app.route("/privacy", methods=["GET"])
def privacy():
    return """
    <h1>Política de Privacidad — REVO Agente</h1>
    <p>Revotech SRL opera este servicio de mensajería automatizada.</p>
    <p>Los mensajes enviados a través de Instagram son procesados para brindar atención al cliente.</p>
    <p>No compartimos datos personales con terceros.</p>
    <p>Para consultas: revotech.ar@gmail.com</p>
    """, 200
@app.route("/", methods=["GET"])
def home():
    return "REVO Agente activo", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
