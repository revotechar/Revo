"""
REVO — Agente de Ventas v4.1
Nicolás — funnel de calificación, siempre cierra en la web
"""

import json
import os
import sys
from datetime import datetime

import anthropic

_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Catálogo ──────────────────────────────────────────────────────────────────
with open(os.path.join(_DIR, "catalogo.json"), encoding="utf-8") as _f:
    CATALOGO = json.load(_f)

# ── Base de datos de leads ─────────────────────────────────────────────────────
LEADS_FILE = os.path.join(_DIR, "leads.json")
LIMITE_MENSAJES = 6

MENSAJE_LIMITE = (
    "Mirá, lo mejor que puedo hacer es mandarte acá donde tenés todo — "
    "revotech.com.ar. Ahí encontrás los detalles, los resultados y podés comprar."
)


def cargar_leads() -> dict:
    if os.path.exists(LEADS_FILE):
        with open(LEADS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def guardar_leads(leads: dict) -> None:
    with open(LEADS_FILE, "w", encoding="utf-8") as f:
        json.dump(leads, f, ensure_ascii=False, indent=2)


def get_lead(leads: dict, lead_id: str) -> dict:
    if lead_id not in leads:
        leads[lead_id] = {
            "id": lead_id,
            "nombre": None,
            "canal": "terminal",
            "estado": "nuevo",
            "paso_secuencia": 1,
            "historial": [],
            "mensajes_total": 0,
            "primera_consulta": datetime.now().isoformat(),
            "ultima_actividad": datetime.now().isoformat(),
            "compro": False,
            "producto_comprado": None,
            "precio_pagado": None,
            "notas": "",
            "limite_alcanzado": False,
        }
    return leads[lead_id]


def actualizar_estado_lead(lead: dict, rol: str, texto: str) -> None:
    lead["historial"].append({
        "rol": rol,
        "mensaje": texto,
        "timestamp": datetime.now().isoformat()
    })
    lead["mensajes_total"] += 1
    lead["ultima_actividad"] = datetime.now().isoformat()


# ── Cliente Anthropic ──────────────────────────────────────────────────────────
client = anthropic.Anthropic()

# ── System Prompt ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = f"""Sos Nicolás, el agente de ventas de {CATALOGO['empresa']} ({CATALOGO['razon_social']}) para Instagram y WhatsApp.
Tu único objetivo: calificar al cliente y mandarlo a la web. No cerrás ventas por acá.
Escribís siempre con acentos correctos: á, é, í, ó, ú, ñ, ¿, ¡

CANALES OFICIALES:
Web: {CATALOGO['web']} | Instagram: {CATALOGO['instagram']} | Email: {CATALOGO['email']}
Solo ecommerce, sin local físico ni revendedores.

GARANTÍA — REGLA CRÍTICA:
La garantía de devolución total de 90 días aplica SOLO por compra en revotech.com.ar.
En Mercado Libre NO aplica.

REGLAS DE COMUNICACIÓN — INAMOVIBLES:
- Máximo 2-3 líneas por mensaje
- Si tenés más para decir, cortá con [MSG] para simular mensajes separados
- NUNCA mandés bloques de texto largos
- Usá el nombre del cliente cuando lo sabés
- Sin emojis. Tono directo, cercano, tuteo
- Escribís siempre con acentos: á, é, í, ó, ú, ñ
- Detectá el idioma del cliente y respondé en ese idioma

FUERA DE TEMA:
Si el cliente pregunta algo que no tiene nada que ver con el cabello o con REVO, respondé SOLO:
"Solo puedo ayudarte con consultas sobre REVO. ¿Tenés alguna pregunta sobre el producto?"
Nada más. No explicás, no desarrollás.

PREGUNTAS DE CREDIBILIDAD (ingredientes, ANMAT, dermatólogos, nunca usé algo similar, etc.):
Respondé en UNA línea corta y mandá a la web.
Ejemplo: "Sí, tenemos certificación ANMAT. Todos los detalles en revotech.com.ar"
Ejemplo: "Es el primer sistema de dos frentes para cabello en el mercado. Todo en revotech.com.ar"

SECUENCIA DE VENTA:

PASO 1 — APERTURA
Preguntá el estado del cabello del cliente. No vendas nada todavía.

PASO 2 — CALIFICACIÓN (1-2 preguntas)
Según la respuesta: tiempo de caída, si es progresiva o fue de golpe.
Validá que REVO aplica al caso.
Si menciona alopecia avanzada u oncológico: aclará que no reemplaza tratamiento médico.

PASO 3 — PROPUESTA BREVE
BR1 actúa en el folículo desde afuera. CR1 da soporte interno.
Sistema de 90 días con garantía de devolución total.

PASO 4 — CIERRE EN LA WEB
→ Mandá a revotech.com.ar para ver resultados y comprar con garantía de 90 días.

PERFILES DE CLIENTE:
MARTÍN (28-35, prevención): "Actuar antes de que sea visible es la ventaja."
DIEGO (33-42, ya lo ve): "Ya lo notaste. Lo que probaste antes era un producto. REVO es un sistema."
ROBERTO (43-55, pérdida visible): "El folículo no desaparece, se apaga. Todavía hay margen."

OBJECIONES:
"ES CARO" → "Son $2.221 por día con garantía de devolución. Todo en revotech.com.ar"
"LO PIENSO" → "Entiendo. Los primeros 100 tienen 15% activo. revotech.com.ar"
"YA PROBÉ ALGO" → "Era un producto suelto. REVO es un sistema de dos frentes. Mirá los resultados en revotech.com.ar"
"TIENEN EN ML?" → "Sí, estamos. Pero la garantía solo aplica en la web. revotech.com.ar"

LO QUE NUNCA HACÉS:
- Cerrar ventas por Instagram o WhatsApp
- Prometer recuperación de cabello perdido
- Prometer resultados antes del día 60
- Párrafos largos
- Emojis
- Revelar proveedores o costos internos
- Inventar métricas o reseñas
- Responder preguntas que no tienen nada que ver con REVO o el cabello
"""

BIENVENIDA = "Hola, acá Nicolás de REVO. Contame, ¿qué estás notando con tu cabello últimamente?"

# ── Herramientas ───────────────────────────────────────────────────────────────
TOOLS = [
    {
        "name": "listar_productos",
        "description": "Lista todos los productos de REVO con precio y descripcion.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "obtener_producto",
        "description": "Informacion completa de un producto. IDs: BR1, CR1, KIT1MES, KIT90D.",
        "input_schema": {
            "type": "object",
            "properties": {
                "id_producto": {"type": "string", "description": "BR1, CR1, KIT1MES o KIT90D"}
            },
            "required": ["id_producto"],
        },
    },
    {
        "name": "calcular_precio_final",
        "description": "Calcula precio final con descuentos.",
        "input_schema": {
            "type": "object",
            "properties": {
                "id_producto": {"type": "string"},
                "metodo_pago": {"type": "string", "enum": ["transferencia", "otro"]},
            },
            "required": ["id_producto", "metodo_pago"],
        },
    },
    {
        "name": "obtener_garantia",
        "description": "Condiciones exactas de la garantia del Kit 90D.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]


def listar_productos() -> dict:
    productos = []
    for p in CATALOGO["productos"]:
        entry = {
            "id": p["id"],
            "nombre": p["nombre"],
            "precio": f"${p['precio']:,}".replace(",", "."),
            "descripcion": p["descripcion"],
        }
        if p.get("incluye_garantia"):
            entry["garantia"] = "Devolucion 100% — SOLO por compra en revotech.com.ar"
        if p.get("envio_gratis"):
            entry["envio"] = "Gratis"
        productos.append(entry)
    return {"empresa": CATALOGO["empresa"], "productos": productos}


def obtener_producto(id_producto: str) -> dict:
    for p in CATALOGO["productos"]:
        if p["id"].upper() == id_producto.upper():
            result = {
                "id": p["id"],
                "nombre": p["nombre"],
                "descripcion": p["descripcion"],
                "precio_lista": f"${p['precio']:,}".replace(",", "."),
                "certificacion": p.get("certificacion"),
            }
            if p.get("incluye_garantia"):
                result["garantia"] = "Devolucion 100% — SOLO compra en revotech.com.ar. En ML NO aplica."
            if p.get("envio_gratis"):
                result["envio"] = "Gratis"
            return result
    return {"error": f"Producto '{id_producto}' no encontrado."}


def calcular_precio_final(id_producto: str, metodo_pago: str) -> dict:
    for p in CATALOGO["productos"]:
        if p["id"].upper() == id_producto.upper():
            precio_base = p["precio"]
            precio_final = precio_base
            descuentos = []

            if p.get("promo_lanzamiento", {}).get("activa"):
                promo = p["promo_lanzamiento"]
                precio_final = int(precio_final * (1 - promo["descuento"]))
                descuentos.append(f"{int(promo['descuento'] * 100)}% promo lanzamiento")

            if metodo_pago == "transferencia":
                ahorro = int(precio_final * CATALOGO["descuento_transferencia"])
                precio_final -= ahorro
                descuentos.append("10% transferencia")

            return {
                "nombre": p["nombre"],
                "precio_lista": f"${precio_base:,}".replace(",", "."),
                "descuentos": descuentos or ["Sin descuento"],
                "precio_final": f"${precio_final:,}".replace(",", "."),
            }
    return {"error": f"Producto '{id_producto}' no encontrado."}


def obtener_garantia() -> dict:
    g = CATALOGO["garantia_kit90d"]
    return {
        "producto": "Kit 90 Dias",
        "cobertura": g["cobertura"],
        "condiciones": g["condiciones"],
        "canal_valido": "SOLO revotech.com.ar — en Mercado Libre NO aplica",
    }


def ejecutar_herramienta(nombre: str, params: dict) -> str:
    if nombre == "listar_productos":
        return json.dumps(listar_productos(), ensure_ascii=False)
    elif nombre == "obtener_producto":
        return json.dumps(obtener_producto(params["id_producto"]), ensure_ascii=False)
    elif nombre == "calcular_precio_final":
        return json.dumps(calcular_precio_final(params["id_producto"], params["metodo_pago"]), ensure_ascii=False)
    elif nombre == "obtener_garantia":
        return json.dumps(obtener_garantia(), ensure_ascii=False)
    return json.dumps({"error": f"Herramienta desconocida: {nombre}"})


# ── Helpers ────────────────────────────────────────────────────────────────────
def format_output(texto: str) -> None:
    mensajes = texto.split("[MSG]")
    for msg in mensajes:
        msg = msg.strip()
        if msg:
            print(f"\nAgente: {msg}")


def mostrar_estado_lead(lead: dict) -> None:
    print(f"\n{'─'*40}")
    print(f"  Lead:     {lead['id']}")
    print(f"  Nombre:   {lead['nombre'] or 'desconocido'}")
    print(f"  Estado:   {lead['estado']}")
    print(f"  Mensajes: {lead['mensajes_total']}")
    print(f"  Compró:   {'SÍ' if lead['compro'] else 'no'}")
    if lead['notas']:
        print(f"  Notas:    {lead['notas'].strip()}")
    print(f"{'─'*40}\n")


def llamar_agente(messages: list) -> str:
    while True:
        respuesta = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=350,
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
                    resultados.append({
                        "type": "tool_result",
                        "tool_use_id": bloque.id,
                        "content": resultado,
                    })
            messages.append({"role": "user", "content": resultados})
        else:
            return "Disculpá, hubo un problema. Escribinos de nuevo."


# ── Loop principal ─────────────────────────────────────────────────────────────
def ejecutar_agente() -> None:
    leads = cargar_leads()

    print("\n" + "=" * 62)
    print("  REVO — Nicolás — Agente de Ventas v4.1")
    print("=" * 62)
    print("\nComandos:")
    print("  /lead [id]    → Cambiar de lead activo")
    print("  /estado       → Ver estado del lead actual")
    print("  /compro       → Marcar lead como comprado")
    print("  /frio         → Marcar lead como frío")
    print("  /nota [texto] → Agregar nota al lead")
    print("  /reset        → Reiniciar conversación")
    print("  salir         → Terminar sesión")
    print("─" * 62)

    lead_id = input("\nID del lead (Enter para 'prueba'): ").strip() or "prueba"
    lead = get_lead(leads, lead_id)
    guardar_leads(leads)

    messages: list[dict] = []
    if lead["historial"]:
        for h in lead["historial"]:
            messages.append({"role": h["rol"], "content": h["mensaje"]})
        print(f"\n[Retomando conversación con '{lead_id}' — {lead['mensajes_total']} mensajes previos]\n")
        mostrar_estado_lead(lead)
    else:
        messages = [{"role": "assistant", "content": BIENVENIDA}]
        actualizar_estado_lead(lead, "assistant", BIENVENIDA)
        guardar_leads(leads)
        print(f"\nAgente: {BIENVENIDA}\n")

    while True:
        try:
            entrada = input("Vos: ").strip()
        except (EOFError, KeyboardInterrupt):
            guardar_leads(leads)
            print("\n\nSesión cerrada. Leads guardados.")
            break

        if not entrada:
            continue

        if entrada.lower() in ("salir", "exit", "quit"):
            guardar_leads(leads)
            print("\nAgente: Hasta luego.")
            break

        if entrada.lower().startswith("/lead"):
            parts = entrada.split(" ", 1)
            lead_id = parts[1].strip() if len(parts) > 1 else "prueba"
            lead = get_lead(leads, lead_id)
            guardar_leads(leads)
            messages = [{"role": h["rol"], "content": h["mensaje"]} for h in lead["historial"]] or \
                       [{"role": "assistant", "content": BIENVENIDA}]
            print(f"\n[Lead activo: {lead_id}]")
            mostrar_estado_lead(lead)
            continue

        if entrada.lower() == "/estado":
            mostrar_estado_lead(lead)
            continue

        if entrada.lower() == "/compro":
            lead["compro"] = True
            lead["estado"] = "compro"
            guardar_leads(leads)
            print("\n[Lead marcado como COMPRADO]\n")
            continue

        if entrada.lower() == "/frio":
            lead["estado"] = "frio"
            guardar_leads(leads)
            print("\n[Lead marcado como FRÍO]\n")
            continue

        if entrada.lower().startswith("/nota"):
            parts = entrada.split(" ", 1)
            nota = parts[1].strip() if len(parts) > 1 else ""
            lead["notas"] += f"\n[{datetime.now().strftime('%d/%m %H:%M')}] {nota}"
            guardar_leads(leads)
            print("\n[Nota guardada]\n")
            continue

        if entrada.lower() == "/reset":
            lead["historial"] = []
            lead["mensajes_total"] = 0
            lead["estado"] = "nuevo"
            lead["paso_secuencia"] = 1
            lead["limite_alcanzado"] = False
            messages = [{"role": "assistant", "content": BIENVENIDA}]
            guardar_leads(leads)
            print(f"\n[Conversación reiniciada]\n\nAgente: {BIENVENIDA}\n")
            continue

        # ── Límite de mensajes ─────────────────────────────────────────────────
        if lead.get("limite_alcanzado"):
            continue

        if lead["mensajes_total"] >= LIMITE_MENSAJES:
            lead["limite_alcanzado"] = True
            lead["estado"] = "derivado_web"
            actualizar_estado_lead(lead, "assistant", MENSAJE_LIMITE)
            guardar_leads(leads)
            print(f"\nAgente: {MENSAJE_LIMITE}\n")
            continue

        # ── Mensaje normal ─────────────────────────────────────────────────────
        actualizar_estado_lead(lead, "user", entrada)
        messages.append({"role": "user", "content": entrada})

        if lead["nombre"] is None:
            for palabra in entrada.split():
                if palabra[0].isupper() and len(palabra) > 2 and palabra.isalpha():
                    lead["nombre"] = palabra
                    break

        if lead["estado"] == "nuevo":
            lead["estado"] = "calificando"

        texto_respuesta = llamar_agente(messages)
        format_output(texto_respuesta)
        print()
        actualizar_estado_lead(lead, "assistant", texto_respuesta)
        guardar_leads(leads)


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY no configurada.")
        sys.exit(1)
    ejecutar_agente()
