"""
dashboard_gen.py — Genera dashboard HTML con metricas de leads REVO
Uso: python dashboard_gen.py
Abre dashboard.html en el navegador automaticamente
"""

import json
import os
import webbrowser
from datetime import datetime

_DIR = os.path.dirname(os.path.abspath(__file__))
LEADS_FILE = os.path.join(_DIR, "leads.json")
OUTPUT_FILE = os.path.join(_DIR, "dashboard.html")


def cargar_leads() -> dict:
    if not os.path.exists(LEADS_FILE):
        return {}
    with open(LEADS_FILE, encoding="utf-8") as f:
        return json.load(f)


def calcular_metricas(leads: dict) -> dict:
    total = len(leads)
    if total == 0:
        return {
            "total": 0, "nuevos": 0, "calificando": 0, "cerrando": 0,
            "comprados": 0, "frios": 0, "descartados": 0,
            "tasa_cierre": 0, "mensajes_total": 0, "mensajes_promedio": 0,
            "leads_hoy": 0,
        }

    estados = {"nuevo": 0, "calificando": 0, "presentando": 0, "cerrando": 0,
               "compro": 0, "frio": 0, "descartado": 0}

    mensajes_total = 0
    leads_hoy = 0
    hoy = datetime.now().date().isoformat()

    for lead in leads.values():
        estado = lead.get("estado", "nuevo")
        if estado in estados:
            estados[estado] += 1
        mensajes_total += lead.get("mensajes_total", 0)
        if lead.get("primera_consulta", "")[:10] == hoy:
            leads_hoy += 1

    comprados = estados["compro"]
    tasa_cierre = round((comprados / total) * 100, 1) if total > 0 else 0

    return {
        "total": total,
        "nuevos": estados["nuevo"],
        "calificando": estados["calificando"] + estados["presentando"],
        "cerrando": estados["cerrando"],
        "comprados": comprados,
        "frios": estados["frio"],
        "descartados": estados["descartado"],
        "tasa_cierre": tasa_cierre,
        "mensajes_total": mensajes_total,
        "mensajes_promedio": round(mensajes_total / total, 1) if total > 0 else 0,
        "leads_hoy": leads_hoy,
    }


def generar_filas_leads(leads: dict) -> str:
    if not leads:
        return "<tr><td colspan='7' style='text-align:center;color:#888'>Sin leads todavia</td></tr>"

    colores_estado = {
        "nuevo": "#6c757d",
        "calificando": "#0d6efd",
        "presentando": "#0dcaf0",
        "cerrando": "#ffc107",
        "compro": "#198754",
        "frio": "#dc3545",
        "descartado": "#adb5bd",
    }

    filas = ""
    for lead in sorted(leads.values(), key=lambda x: x.get("ultima_actividad", ""), reverse=True):
        estado = lead.get("estado", "nuevo")
        color = colores_estado.get(estado, "#6c757d")
        nombre = lead.get("nombre") or "—"
        ultima = lead.get("ultima_actividad", "")[:16].replace("T", " ")
        primera = lead.get("primera_consulta", "")[:10]
        compro = "SI" if lead.get("compro") else "no"
        notas = (lead.get("notas") or "").strip().replace("\n", " | ")[:60]

        filas += f"""
        <tr>
            <td><strong>{lead['id']}</strong></td>
            <td>{nombre}</td>
            <td><span class="badge" style="background:{color}">{estado}</span></td>
            <td style="text-align:center">{lead.get('mensajes_total', 0)}</td>
            <td style="text-align:center"><strong style="color:{'#198754' if compro == 'SI' else '#aaa'}">{compro}</strong></td>
            <td>{ultima}</td>
            <td style="font-size:0.8rem;color:#888">{notas or '—'}</td>
        </tr>"""
    return filas


def generar_html(metricas: dict, leads: dict) -> str:
    ahora = datetime.now().strftime("%d/%m/%Y %H:%M")
    filas = generar_filas_leads(leads)

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>REVO — Dashboard de Ventas</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f7; color: #1d1d1f; }}
  header {{ background: #1d1d1f; color: white; padding: 20px 32px; display: flex; justify-content: space-between; align-items: center; }}
  header h1 {{ font-size: 1.4rem; font-weight: 600; letter-spacing: -0.5px; }}
  header span {{ font-size: 0.85rem; color: #888; }}
  .container {{ max-width: 1200px; margin: 0 auto; padding: 28px 24px; }}
  .kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; margin-bottom: 28px; }}
  .kpi {{ background: white; border-radius: 14px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,.07); }}
  .kpi .valor {{ font-size: 2.2rem; font-weight: 700; line-height: 1; }}
  .kpi .label {{ font-size: 0.8rem; color: #888; margin-top: 6px; text-transform: uppercase; letter-spacing: .5px; }}
  .kpi.verde .valor {{ color: #198754; }}
  .kpi.rojo .valor {{ color: #dc3545; }}
  .kpi.azul .valor {{ color: #0d6efd; }}
  .kpi.naranja .valor {{ color: #fd7e14; }}
  .seccion {{ background: white; border-radius: 14px; padding: 24px; box-shadow: 0 1px 4px rgba(0,0,0,.07); margin-bottom: 24px; }}
  .seccion h2 {{ font-size: 1rem; font-weight: 600; margin-bottom: 18px; color: #333; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
  th {{ text-align: left; padding: 10px 12px; border-bottom: 2px solid #f0f0f0; font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: .5px; }}
  td {{ padding: 12px; border-bottom: 1px solid #f8f8f8; vertical-align: middle; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: #fafafa; }}
  .badge {{ display: inline-block; padding: 3px 10px; border-radius: 20px; color: white; font-size: 0.78rem; font-weight: 500; }}
  .funnel {{ display: flex; gap: 12px; flex-wrap: wrap; }}
  .funnel-item {{ flex: 1; min-width: 100px; background: #f8f9fa; border-radius: 10px; padding: 14px; text-align: center; }}
  .funnel-item .fn {{ font-size: 1.6rem; font-weight: 700; }}
  .funnel-item .fl {{ font-size: 0.75rem; color: #888; margin-top: 4px; }}
  .refresh {{ display: inline-block; margin-top: 8px; font-size: 0.8rem; color: #0d6efd; cursor: pointer; text-decoration: underline; }}
</style>
</head>
<body>

<header>
  <h1>REVO — Dashboard de Ventas</h1>
  <span>Actualizado: {ahora}</span>
</header>

<div class="container">

  <!-- KPIs principales -->
  <div class="kpis">
    <div class="kpi azul">
      <div class="valor">{metricas['total']}</div>
      <div class="label">Leads totales</div>
    </div>
    <div class="kpi">
      <div class="valor">{metricas['leads_hoy']}</div>
      <div class="label">Leads hoy</div>
    </div>
    <div class="kpi verde">
      <div class="valor">{metricas['comprados']}</div>
      <div class="label">Compraron</div>
    </div>
    <div class="kpi naranja">
      <div class="valor">{metricas['tasa_cierre']}%</div>
      <div class="label">Tasa de cierre</div>
    </div>
    <div class="kpi rojo">
      <div class="valor">{metricas['frios']}</div>
      <div class="label">Leads frios</div>
    </div>
    <div class="kpi">
      <div class="valor">{metricas['mensajes_total']}</div>
      <div class="label">Mensajes totales</div>
    </div>
    <div class="kpi">
      <div class="valor">{metricas['mensajes_promedio']}</div>
      <div class="label">Mensajes/lead</div>
    </div>
  </div>

  <!-- Funnel -->
  <div class="seccion">
    <h2>Funnel de conversion</h2>
    <div class="funnel">
      <div class="funnel-item">
        <div class="fn" style="color:#6c757d">{metricas['nuevos']}</div>
        <div class="fl">Nuevos</div>
      </div>
      <div class="funnel-item">
        <div class="fn" style="color:#0d6efd">{metricas['calificando']}</div>
        <div class="fl">Calificando</div>
      </div>
      <div class="funnel-item">
        <div class="fn" style="color:#ffc107">{metricas['cerrando']}</div>
        <div class="fl">Cerrando</div>
      </div>
      <div class="funnel-item">
        <div class="fn" style="color:#198754">{metricas['comprados']}</div>
        <div class="fl">Compraron</div>
      </div>
      <div class="funnel-item">
        <div class="fn" style="color:#dc3545">{metricas['frios']}</div>
        <div class="fl">Frios</div>
      </div>
    </div>
  </div>

  <!-- Tabla de leads -->
  <div class="seccion">
    <h2>Todos los leads</h2>
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>Nombre</th>
          <th>Estado</th>
          <th>Mensajes</th>
          <th>Compro</th>
          <th>Ultima actividad</th>
          <th>Notas</th>
        </tr>
      </thead>
      <tbody>
        {filas}
      </tbody>
    </table>
    <p style="margin-top:16px;font-size:0.8rem;color:#aaa">
      Para actualizar: correr <code>python dashboard_gen.py</code> de nuevo.
    </p>
  </div>

</div>
</body>
</html>"""


def main():
    leads = cargar_leads()
    metricas = calcular_metricas(leads)
    html = generar_html(metricas, leads)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n[OK] Dashboard generado: {OUTPUT_FILE}")
    print(f"     Leads totales:  {metricas['total']}")
    print(f"     Compraron:      {metricas['comprados']}")
    print(f"     Tasa de cierre: {metricas['tasa_cierre']}%")
    print(f"     Mensajes total: {metricas['mensajes_total']}\n")

    webbrowser.open(f"file:///{OUTPUT_FILE.replace(os.sep, '/')}")


if __name__ == "__main__":
    main()
