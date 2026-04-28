"""
instagram_bridge.py — Puente entre Instagram DMs y el agente REVO
Uso: python instagram_bridge.py
Requiere: pip install requests
"""

import os
import json
import requests

# ===================== CONFIGURACION =====================
IG_TOKEN = "IGAANsZBzucAyNBZAFlrbHdZARUwwaHdmUUIwbE1hRmg1c1U2SXFQa05HdExKOHBCalJ0YUQ5dkxFQVVBQ0hZAYm1oZAEZAJeDBsN1pJeFRrTmZA4SUg5a3FJM3RQQ1FiNG1SMDR3aWhhejdiZAVVPSmZARRWJvNHlaWE5oZAVltOXBrdjJWRQZDZD"
IG_USER_ID = "178414441771258381"
API_URL = f"https://graph.instagram.com/v21.0/{IG_USER_ID}/messages"
# =========================================================

# Importar el agente REVO
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import anthropic
from agente import SYSTEM_PROMPT, TOOLS, ejecutar_herramienta, BIENVENIDA

client = anthropic.Anthropic()

# Historial de conversaciones por usuario de Instagram
conversaciones: dict = {}


def obtener_mensajes_nuevos() -> list:
    """Obtiene los DMs nuevos de Instagram."""
    url = f"https://graph.instagram.com/v21.0/{IG_USER_ID}/conversations"
    params = {
        "fields": "messages{message,from,created_time}",
        "access_token": IG_TOKEN,
        "platform": "instagram"
    }
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        print(f"Error al obtener mensajes: {resp.text}")
        return []
    data = resp.json()
    mensajes = []
    for conv in data.get("data", []):
        msgs = conv.get("messages", {}).get("data", [])
        for msg in msgs:
            sender = msg.get("from", {})
            # Solo procesar mensajes de clientes (no los propios)
            if str(sender.get("id")) != str(IG_USER_ID):
                mensajes.append({
                    "sender_id": sender.get("id"),
                    "sender_name": sender.get("name", "Cliente"),
                    "text": msg.get("message", ""),
                    "time": msg.get("created_time")
                })
    return mensajes


def enviar_respuesta(recipient_id: str, texto: str) -> bool:
    """Envía una respuesta al usuario de Instagram."""
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": texto},
        "messaging_type": "RESPONSE",
        "access_token": IG_TOKEN
    }
    resp = requests.post(API_URL, json=payload)
    if resp.status_code == 200:
        print(f"  [OK] Respuesta enviada a {recipient_id}")
        return True
    else:
        print(f"  [ERROR] No se pudo enviar: {resp.text}")
        return False


def procesar_mensaje(sender_id: str, texto: str) -> str:
    """Procesa un mensaje con el agente REVO y devuelve la respuesta."""
    # Inicializar conversacion si es nuevo usuario
    if sender_id not in conversaciones:
        conversaciones[sender_id] = [
            {"role": "assistant", "content": BIENVENIDA}
        ]

    messages = conversaciones[sender_id]
    messages.append({"role": "user", "content": texto})

    # Loop del agente (igual que en agente.py)
    while True:
        respuesta = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=1024,
            system=[{
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"}
            }],
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
                    resultados.append({
                        "type": "tool_result",
                        "tool_use_id": bloque.id,
                        "content": resultado,
                    })
            messages.append({"role": "user", "content": resultados})
        else:
            return "Disculpa, hubo un error. Por favor escribinos de nuevo."


def modo_prueba():
    """
    Modo de prueba: simula mensajes de Instagram sin necesitar webhook.
    Util para probar antes de publicar la app.
    """
    print("\n" + "=" * 62)
    print("  REVO — Bridge Instagram (MODO PRUEBA)")
    print("=" * 62)
    print("Simulando conversacion como si viniese de Instagram.")
    print("Escribi tu consulta. Para salir escribi 'salir'.\n")

    sender_id_prueba = "usuario_prueba_123"
    print(f"Agente: {BIENVENIDA}\n")

    while True:
        try:
            entrada = input("Vos (simulando DM): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSaliendo...")
            break

        if not entrada:
            continue
        if entrada.lower() in ("salir", "exit", "quit"):
            break

        print("\nAgente procesando...", end="", flush=True)
        respuesta = procesar_mensaje(sender_id_prueba, entrada)
        print(f"\rAgente: {respuesta}\n")


if __name__ == "__main__":
    # Verificar que la API key de Anthropic este configurada
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY no esta configurada.")
        sys.exit(1)

    print("Iniciando REVO Instagram Bridge...")
    print(f"Token cargado: {IG_TOKEN[:20]}...")
    print(f"Instagram User ID: {IG_USER_ID}")
    print()

    # Por ahora corremos en modo prueba
    # Cuando el servidor este en Railway, esto se reemplaza por el webhook
    modo_prueba()
