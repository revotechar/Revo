"""
REVO — Agente de Ventas v3.0
Con memoria de leads, estado de conversacion y herramientas de catalogo
"""

import json
import os
import sys
from datetime import datetime

import anthropic

_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Catalogo ──────────────────────────────────────────────────────────────────
with open(os.path.join(_DIR, "catalogo.json"), encoding="utf-8") as _f:
    CATALOGO = json.load(_f)

# ── Base de datos de leads ────────────────────────────────────────────────────
LEADS_FILE = os.path.join(_DIR, "leads.json")


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


# ── Cliente Anthropic ─────────────────────────────────────────────────────────
client = anthropic.Anthropic()

# ── System Prompt ─────────────────────────────────────────────────────────────
_MODO_TEXTO = """
=== MODO PRELANZAMIENTO ACTIVO ===
El producto todavía NO está disponible para compra. Sale en aproximadamente {fecha_lanzamiento}.
Hay unidades limitadas para los primeros clientes.

TU OBJETIVO EN ESTE MODO:
1. Entender el caso del cliente (caída, tiempo, situación)
2. Generarle interés y mostrarle que REVO aplica a su caso
3. Pedirle el número de WhatsApp para anotarlo en la lista de espera
4. O redirigirlo a {web} para que se anote ahí

SCRIPT DE CIERRE PRELANZAMIENTO:
"Todavía no salió a la venta, pero estamos armando la lista de espera para los primeros — van a tener prioridad y el mejor precio. ¿Me pasás tu WhatsApp y te anoto?"

Si prefiere la web: "También podés anotarte en {web} — ahí dejás tu mail y te avisamos antes que nadie."

NUNCA digas que pueden comprar ahora. NUNCA mandes links de compra.
El único link válido es {web} para registrarse en la lista.
""" if MODO_PRELANZAMIENTO else ""

SYSTEM_PROMPT = f"""Sos el agente de ventas de {CATALOGO['empresa']} ({CATALOGO['razon_social']}) para WhatsApp e Instagram DM.
Tu único objetivo: convertir. Sos un vendedor nato, no un bot de respuestas automáticas.
Escribís siempre con acentos correctos: á, é, í, ó, ú, ñ, ¿, ¡

{_MODO_TEXTO.format(fecha_lanzamiento=FECHA_LANZAMIENTO, web=WEB_LISTA_ESPERA) if MODO_PRELANZAMIENTO else ""}

CANALES OFICIALES:
Web: {CATALOGO['web']} | Instagram: {CATALOGO['instagram']} | Mercado Libre: buscar "REVO Revotech" | Email: {CATALOGO['email']}
Solo ecommerce, sin local físico ni revendedores. Directo de fábrica al cliente.

GARANTÍA — REGLA CRÍTICA:
La garantía de devolución total de 90 días aplica SOLO por compra en revotech.com.ar.
En Mercado Libre NO aplica la garantía por políticas de la plataforma.
Ante consulta sobre ML: "En ML nos encontrás, pero la garantía de 90 días solo aplica en revotech.com.ar. Para el respaldo completo, conviene la web."

REGLAS DE COMUNICACIÓN — INAMOVIBLES:
- Máximo 2-3 líneas por mensaje
- Si tenés más para decir, cortá con [MSG] para simular mensajes separados de WhatsApp
- NUNCA mandés bloques de texto largos
- Usá el nombre del cliente cuando lo sabés
- Sin emojis. Tono directo, cercano, tuteo
- Cuando el cliente esté listo: cerrá. No sigas explicando
- No insistas más de una vez por objeción
- Detectá el idioma del cliente y respondé en ese idioma

SECUENCIA DE VENTA:

PASO 1 — ENTENDER EL CASO
Preguntá: tiempo de caída, tipo (progresiva o de golpe), diagnóstico médico previo.
No vendas nada todavía.

PASO 2 — VALIDAR QUE REVO APLICA
Si menciona alopecia avanzada, tratamiento oncológico o autoinmune: aclarar que REVO no reemplaza tratamiento médico.

PASO 3 — EXPLICAR EL SISTEMA (máximo 3 líneas)
BR1 actúa en el folículo desde afuera. CR1 da soporte interno desde adentro.
Es un sistema de 90 días, no un producto suelto.

PASO 4 — GARANTÍA + FRICCIÓN POSITIVA
Explicá la garantía del Kit 90D con las 3 condiciones.
Luego preguntá SIEMPRE: "Una pregunta: ¿hace cuánto notás la caída? ¿Es progresiva o fue de golpe?"

PASO 5 — CIERRE
{"→ MODO PRELANZAMIENTO: Pedí el WhatsApp o redirigí a " + WEB_LISTA_ESPERA + " para la lista de espera." if MODO_PRELANZAMIENTO else "Kit 90D como opción más inteligente. 15% primeros 100 clientes + 10% transferencia. Link: " + CATALOGO['web']}

PASO 6 — LEAD FRÍO
Si el cliente dejó de responder, el operador usa /lf para generar el mensaje de seguimiento.

PERFILES DE CLIENTE:
MARTÍN (28-35, prevención): "Actuar antes de que sea visible es la ventaja."
DIEGO (33-42, ya lo ve): "Ya lo notaste. Lo que probaste antes era un producto. REVO es un sistema."
ROBERTO (43-55, pérdida visible): "El folículo no desaparece, se apaga. Todavía hay margen."

OBJECIONES:
{"CUANDO SALE / CUÁNDO PUEDO COMPRAR → Decí la fecha aproximada y pedí el WhatsApp para la lista de espera." if MODO_PRELANZAMIENTO else ""}
"ES CARO" → "Son $2.221 por día con garantía de devolución. Una sola vez."
"LO PIENSO" → "Entiendo. Los primeros 100 tienen 15% activo. Quedan pocos lugares."
"YA PROBÉ ALGO" → "Era un producto suelto. REVO es un sistema de dos frentes simultáneos."
"TIENEN EN ML?" → "Sí, estamos. Pero la garantía solo aplica en la web. Para el respaldo completo, revotech.com.ar"

{"" if MODO_PRELANZAMIENTO else """PROCESO POST-PAGO TRANSFERENCIA:
Pedí de a uno, confirmá antes de seguir:
1. Comprobante de pago
2. Nombre completo
3. Mail
4. Provincia / Ciudad / CP / Calle y número
Al final resumir y confirmar pedido."""}

CLIENTES QUE YA COMPRARON:
"Dame tu nombre o número de orden y te busco el estado."

LO QUE NUNCA HACÉS:
- Prometer recuperación de cabello perdido
- Prometer resultados antes del día 60
- Urgencias falsas (solo el descuento 100 clientes es real)
- Párrafos largos
- Emojis
- Revelar proveedores o costos internos
- Inventar métricas o reseñas
{"- Decir que el producto está disponible para compra ahora (MODO PRELANZAMIENTO)" if MODO_PRELANZAMIENTO else ""}
"""

BIENVENIDA = "Hola! ¿Qué te trae por acá? ¿Estás buscando frenar la caída o ya la venís notando hace rato?"

# ── Modo prelanzamiento ───────────────────────────────────────────────────────
MODO_PRELANZAMIENTO = True
FECHA_LANZAMIENTO = "60 días"
WEB_LISTA_ESPERA = "revotech.com.ar"

# ── Herramientas ──────────────────────────────────────────────────────────────
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
        "description": "Calcula precio final con descuentos. Usar cuando el cliente pregunta cuanto pagaria.",
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
            entry["garantia"] = "Devolucion 100% — SOLO por compra en revotech.com.ar (no aplica en ML)"
        if p.get("envio_gratis"):
            entry["envio"] = "Gratis"
        if p.get("promo_lanzamiento", {}).get("activa"):
            entry["promo"] = p["promo_lanzamiento"]["descripcion"]
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
                "aprobado_dermatologos": p.get("aprobado_dermatologos"),
            }
            if "ingredientes" in p:
                result["ingredientes"] = p["ingredientes"]
            if "contenido" in p:
                result["contenido"] = p["contenido"]
            if p.get("precio_por_dia"):
                result["costo_por_dia"] = f"${p['precio_por_dia']:,}".replace(",", ".")
            if p.get("incluye_garantia"):
                result["garantia"] = "Devolucion 100% — SOLO compra en revotech.com.ar. En ML NO aplica."
            if p.get("envio_gratis"):
                result["envio"] = "Gratis"
            if p.get("promo_lanzamiento", {}).get("activa"):
                promo = p["promo_lanzamiento"]
                precio_promo = int(p["precio"] * (1 - promo["descuento"]))
                result["promo_lanzamiento"] = {
                    "descripcion": promo["descripcion"],
                    "precio_con_promo": f"${precio_promo:,}".replace(",", "."),
                }
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
                descuentos.append(f"10% transferencia (ahorras ${ahorro:,})".replace(",", "."))

            ahorro_total = precio_base - precio_final
            result = {
                "nombre": p["nombre"],
                "precio_lista": f"${precio_base:,}".replace(",", "."),
                "descuentos": descuentos or ["Sin descuento"],
                "precio_final": f"${precio_final:,}".replace(",", "."),
                "ahorro_total": f"${ahorro_total:,}".replace(",", "."),
            }
            if p.get("envio_gratis") or precio_final >= CATALOGO["envio_gratis_desde"]:
                result["envio"] = "Gratis"
            else:
                result["envio"] = f"${CATALOGO['costo_envio']:,}".replace(",", ".")
            return result
    return {"error": f"Producto '{id_producto}' no encontrado."}


def obtener_garantia() -> dict:
    g = CATALOGO["garantia_kit90d"]
    return {
        "producto": "Kit 90 Dias",
        "cobertura": g["cobertura"],
        "condiciones": g["condiciones"],
        "exclusiones": g["exclusiones"],
        "canal_valido": "SOLO revotech.com.ar — en Mercado Libre NO aplica",
        "nota": "Cumplidas las 3 condiciones: devolucion total sin cuestionamientos.",
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


# ── Helpers ───────────────────────────────────────────────────────────────────
def get_lead_frio(nombre: str = "") -> str:
    n = f"Hola {nombre}." if nombre else "Hola."
    return (
        f"{n} Quedo pendiente tu consulta sobre REVO. "
        "Los primeros 100 clientes tienen 15% de descuento activo "
        "— quedan pocos lugares con ese precio. "
        "Seguis evaluando o te quedo alguna duda puntual?"
    )


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
    print(f"  Compro:   {'SI' if lead['compro'] else 'no'}")
    if lead['notas']:
        print(f"  Notas:    {lead['notas'].strip()}")
    print(f"{'─'*40}\n")


# ── Loop principal ────────────────────────────────────────────────────────────
def ejecutar_agente() -> None:
    leads = cargar_leads()

    print("\n" + "=" * 62)
    print("  REVO — Agente de Ventas v3.0")
    print("=" * 62)
    print("\nComandos:")
    print("  /lead [id]    → Cambiar de lead activo")
    print("  /estado       → Ver estado del lead actual")
    print("  /compro       → Marcar lead como comprado")
    print("  /frio         → Marcar lead como frio")
    print("  /lf [nombre]  → Generar mensaje de lead frio")
    print("  /nota [texto] → Agregar nota al lead")
    print("  /reset        → Reiniciar conversacion")
    print("  salir         → Terminar sesion")
    print("─" * 62)

    lead_id = input("\nID del lead (Enter para 'prueba'): ").strip() or "prueba"
    lead = get_lead(leads, lead_id)
    guardar_leads(leads)

    messages: list[dict] = []
    if lead["historial"]:
        for h in lead["historial"]:
            messages.append({"role": h["rol"], "content": h["mensaje"]})
        print(f"\n[Retomando conversacion con '{lead_id}' — {lead['mensajes_total']} mensajes previos]\n")
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
            print("\n\nSesion cerrada. Leads guardados.")
            break

        if not entrada:
            continue

        if entrada.lower() in ("salir", "exit", "quit"):
            guardar_leads(leads)
            print("\nAgente: Hasta luego. Empeza a ocuparte.")
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
            print("\n[Lead marcado como FRIO]\n")
            continue

        if entrada.lower().startswith("/nota"):
            parts = entrada.split(" ", 1)
            nota = parts[1].strip() if len(parts) > 1 else ""
            lead["notas"] += f"\n[{datetime.now().strftime('%d/%m %H:%M')}] {nota}"
            guardar_leads(leads)
            print("\n[Nota guardada]\n")
            continue

        if entrada.lower().startswith("/lf"):
            parts = entrada.split(" ", 1)
            nombre = parts[1].strip() if len(parts) > 1 else (lead["nombre"] or "")
            msg = get_lead_frio(nombre)
            lead["estado"] = "frio"
            guardar_leads(leads)
            print(f"\n--- MENSAJE LEAD FRIO ---\n{msg}\n─────────────────────────\n")
            continue

        if entrada.lower() == "/reset":
            lead["historial"] = []
            lead["mensajes_total"] = 0
            lead["estado"] = "nuevo"
            lead["paso_secuencia"] = 1
            messages = [{"role": "assistant", "content": BIENVENIDA}]
            guardar_leads(leads)
            print(f"\n[Conversacion reiniciada]\n\nAgente: {BIENVENIDA}\n")
            continue

        # Mensaje normal
        actualizar_estado_lead(lead, "user", entrada)
        messages.append({"role": "user", "content": entrada})

        # Detectar nombre simple
        if lead["nombre"] is None:
            for palabra in entrada.split():
                if palabra[0].isupper() and len(palabra) > 2 and palabra.isalpha():
                    lead["nombre"] = palabra
                    break

        if lead["estado"] == "nuevo":
            lead["estado"] = "calificando"

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
                format_output(texto_respuesta)
                print()
                messages.append({"role": "assistant", "content": respuesta.content})
                actualizar_estado_lead(lead, "assistant", texto_respuesta)
                guardar_leads(leads)
                break

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
                print(f"\n[stop_reason: {respuesta.stop_reason}]\n")
                break


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY no configurada.")
        sys.exit(1)
    ejecutar_agente()
