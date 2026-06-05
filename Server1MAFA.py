# server_ui.py
from flask import Flask, request, jsonify, render_template_string
from collections import deque
import time

app = Flask(__name__)

API_KEY = "iot123"      # Debe coincidir con el del ESP32
MAX_POINTS = 1000       # Tamaño máx. del historial en memoria
data_buffer = deque(maxlen=MAX_POINTS)

HTML = r"""
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Panel Médico - Gabinete Inteligente</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    * { font-family: 'DM Sans', sans-serif; }
    body {
      background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #020617 100%);
      min-height: 100vh;
      color: #f8fafc;
    }
    .mono { font-family: 'Space Mono', monospace; }
 
    .card {
      background: rgba(30, 41, 59, 0.75);
      backdrop-filter: blur(16px);
      border: 1px solid rgba(16, 185, 129, 0.15);
      border-radius: 20px;
      box-shadow: 0 4px 24px rgba(16, 185, 129, 0.05), 0 1px 4px rgba(16, 185, 129, 0.03);
      transition: transform 0.18s, box-shadow 0.18s;
    }
    .card:hover {
      transform: translateY(-3px);
      box-shadow: 0 8px 32px rgba(16, 185, 129, 0.15), 0 2px 8px rgba(16, 185, 129, 0.1);
      border-color: rgba(16, 185, 129, 0.3);
    }
 
    .card-icon {
      width: 44px; height: 44px;
      border-radius: 12px;
      display: flex; align-items: center; justify-content: center;
      font-size: 22px;
    }
 
    .badge-live {
      display: inline-flex; align-items: center; gap: 6px;
      background: rgba(16, 185, 129, 0.15); color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.3);
      padding: 4px 12px; border-radius: 999px; font-size: 13px; font-weight: 500;
    }
    .badge-wait {
      display: inline-flex; align-items: center; gap: 6px;
      background: rgba(148, 163, 184, 0.15); color: #94a3b8;
      border: 1px solid rgba(148, 163, 184, 0.2);
      padding: 4px 12px; border-radius: 999px; font-size: 13px; font-weight: 500;
    }
    .dot { width: 8px; height: 8px; border-radius: 50%; }
    .dot-green { background: #34d399; animation: pulse 1.4s infinite; box-shadow: 0 0 8px #34d399; }
    .dot-gray  { background: #64748b; }
    @keyframes pulse {
      0%,100% { opacity: 1; } 50% { opacity: 0.4; }
    }
 
    .val-big {
      font-family: 'Space Mono', monospace;
      font-size: 1.8rem; font-weight: 700; line-height: 1;
    }
 
    table thead tr th { font-size: 12px; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }
    table tbody tr { transition: background 0.12s; }
    table tbody tr:hover { background: rgba(16, 185, 129, 0.12); }
 
    .chart-wrap { position: relative; }
 
    /* alert bar */
    .alert-bar {
      border-radius: 12px; padding: 10px 16px;
      font-size: 13px; font-weight: 500;
      display: flex; align-items: center; gap: 8px;
      border: 1px solid transparent;
    }
    .alert-red   { background: rgba(239, 68, 68, 0.15); color: #fca5a5; border-color: rgba(239, 68, 68, 0.3); }
    .alert-amber { background: rgba(245, 158, 11, 0.15); color: #fde047; border-color: rgba(245, 158, 11, 0.3); }
    .alert-ok    { background: rgba(16, 185, 129, 0.15); color: #6ee7b7; border-color: rgba(16, 185, 129, 0.3); }
  </style>
</head>
<body>
<div class="max-w-7xl mx-auto px-4 py-8">
 
  <header class="mb-8 flex items-center justify-between flex-wrap gap-3 border-b border-slate-700 pb-5">
    <div>
      <h1 class="text-3xl font-semibold text-emerald-50 tracking-tight flex items-center gap-2">Modulo de almacenamiento farmacológico automatizado</h1>
      <p class="text-emerald-400 text-sm mt-1">ESP32 · Preservación de Medicamentos Sensibles · Desinfección UV-C</p>
    </div>
    <div id="badge-status" class="badge-wait">
      <span class="dot dot-gray"></span> Sondeando conexión…
    </div>
  </header>
 
  <div id="alert-row" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 mb-6 hidden">
    <div id="alert-temp"  class="alert-bar alert-ok">🌡️ Temp OK</div>
    <div id="alert-hum"   class="alert-bar alert-ok">💧 Humedad OK</div>
    <div id="alert-gforce" class="alert-bar alert-ok">🧭 Reposo absoluto</div>
    <div id="alert-puerta" class="alert-bar alert-ok">🚪 Puerta cerrada</div>
  </div>
 
  <div class="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
 
    <div class="card p-4">
      <div class="flex items-center gap-2 mb-3">
        <div class="card-icon" style="background: rgba(244, 63, 94, 0.15); color: #f43f5e;">🌡️</div>
        <span class="text-emerald-300 text-sm font-medium">Temperatura</span>
      </div>
      <div id="card-temp" class="val-big text-rose-400">—</div>
      <div class="text-slate-400 text-xs mt-1">°C (Rango: 18-30)</div>
    </div>
 
    <div class="card p-4">
      <div class="flex items-center gap-2 mb-3">
        <div class="card-icon" style="background: rgba(6, 182, 212, 0.15); color: #06b6d4;">💧</div>
        <span class="text-emerald-300 text-sm font-medium">Humedad</span>
      </div>
      <div id="card-hum" class="val-big text-cyan-400">—</div>
      <div class="text-slate-400 text-xs mt-1">%RH (Máx: 70)</div>
    </div>
 
    <div class="card p-4">
      <div class="flex items-center gap-2 mb-3">
        <div class="card-icon" style="background: rgba(251, 191, 36, 0.15); color: #fbbf24;">💡</div>
        <span class="text-emerald-300 text-sm font-medium">Luz Int.</span>
      </div>
      <div id="card-luz" class="val-big text-amber-400">—</div>
      <div class="text-slate-400 text-xs mt-1">% (Máx: 50)</div>
    </div>

    <div class="card p-4">
      <div class="flex items-center gap-2 mb-3">
        <div class="card-icon" style="background: rgba(16, 185, 129, 0.15); color: #10b981;">🚪</div>
        <span class="text-emerald-300 text-sm font-medium">Proximidad</span>
      </div>
      <div id="card-dist" class="val-big text-emerald-400">—</div>
      <div class="text-slate-400 text-xs mt-1">cm (Puerta)</div>
    </div>

    <div class="card p-4">
      <div class="flex items-center gap-2 mb-3">
        <div class="card-icon" style="background: rgba(168, 85, 247, 0.15); color: #a855f7;">🏃</div>
        <span class="text-emerald-300 text-sm font-medium">Movimiento</span>
      </div>
      <div id="card-gforce" class="val-big text-purple-400">—</div>
      <div class="text-slate-400 text-xs mt-1">g-force</div>
    </div>
 
  </div>
 
  <div class="card px-6 py-4 mb-6 flex items-center justify-between flex-wrap gap-2">
    <div>
      <span class="text-emerald-500 text-xs font-semibold uppercase tracking-widest">Última Sincronización Clínica</span>
      <div id="card-time" class="mono text-slate-300 text-sm mt-1">—</div>
    </div>
    <div id="card-device-full" class="text-slate-400 text-sm">—</div>
  </div>
 
  <div class="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-4 gap-5 mb-6">
 
    <div class="card p-5 chart-wrap">
      <div class="flex items-center gap-2 mb-4">
        <h2 class="font-semibold text-slate-200 text-sm">🌡️ Historial Temperatura</h2>
      </div>
      <canvas id="chartTemp" height="150"></canvas>
    </div>
 
    <div class="card p-5 chart-wrap">
      <div class="flex items-center gap-2 mb-4">
        <h2 class="font-semibold text-slate-200 text-sm">💧 Historial Humedad</h2>
      </div>
      <canvas id="chartHum" height="150"></canvas>
    </div>
 
    <div class="card p-5 chart-wrap">
      <div class="flex items-center gap-2 mb-4">
        <h2 class="font-semibold text-slate-200 text-sm">💡 Entrada de Luz</h2>
      </div>
      <canvas id="chartLuz" height="150"></canvas>
    </div>

    <div class="card p-5 chart-wrap">
      <div class="flex items-center gap-2 mb-4">
        <h2 class="font-semibold text-slate-200 text-sm">🏃 Movimiento de Estructura</h2>
      </div>
      <canvas id="chartG" height="150"></canvas>
    </div>
 
  </div>
 
  <div class="card p-6">
    <h2 class="font-semibold text-slate-200 mb-4 flex items-center gap-2">📋 Registro Detallado de Telemetría</h2>
    <div class="overflow-x-auto">
      <table class="min-w-full text-sm">
        <thead>
          <tr class="text-emerald-400 border-b border-slate-700">
            <th class="py-2 pr-4 text-left">Hora</th>
            <th class="py-2 pr-4 text-left">Temp (°C)</th>
            <th class="py-2 pr-4 text-left">Hum (%)</th>
            <th class="py-2 pr-4 text-left">Luz (%)</th>
            <th class="py-2 pr-4 text-left">Distancia (cm)</th>
            <th class="py-2 pr-4 text-left">Fuerza (g)</th>
          </tr>
        </thead>
        <tbody id="table-body" class="text-slate-300"></tbody>
      </table>
    </div>
  </div>
 
  <footer class="text-center text-xs text-slate-500 mt-8">
    Gabinete Médico IoT · Flask · ESP32 · Tailwind
  </footer>
</div>
 
<script>
const fmtTs = ts => ts ? new Date(ts * 1000).toLocaleString() : "—";
const fmt1   = v  => v != null ? Number(v).toFixed(1) : "—";
const fmt0   = v  => v != null ? Number(v).toFixed(0) : "—";
 
let tempChart, humChart, gChart, luzChart;
 
const chartDefaults = (color) => ({
  responsive: true,
  animation: false,
  plugins: { legend: { display: false } },
  scales: {
    x: { display: false },
    y: { beginAtZero: false, grid: { color: "rgba(16, 185, 129, 0.08)" },
         ticks: { color: "#10b981", font: { family: "Space Mono", size: 10 } } }
  },
  elements: { point: { radius: 0 } }
});
 
function mkDataset(color, fill) {
  return {
    data: [], tension: 0.35,
    borderColor: color, borderWidth: 2,
    backgroundColor: fill,
    fill: true
  };
}
 
function initCharts() {
  tempChart = new Chart(document.getElementById("chartTemp"), {
    type: "line",
    data: { labels: [], datasets: [mkDataset("#f43f5e","rgba(244,63,94,0.05)")] },
    options: chartDefaults("#f43f5e")
  });
  humChart = new Chart(document.getElementById("chartHum"), {
    type: "line",
    data: { labels: [], datasets: [mkDataset("#06b6d4","rgba(6,182,212,0.05)")] },
    options: chartDefaults("#06b6d4")
  });
  luzChart = new Chart(document.getElementById("chartLuz"), {
    type: "line",
    data: { labels: [], datasets: [mkDataset("#fbbf24","rgba(251,191,36,0.05)")] },
    options: chartDefaults("#fbbf24")
  });
  gChart = new Chart(document.getElementById("chartG"), {
    type: "line",
    data: { labels: [], datasets: [mkDataset("#a855f7","rgba(168,85,247,0.05)")] },
    options: chartDefaults("#a855f7")
  });
}
 
function updateAlerts(last) {
  if (!last) return;
  const row = document.getElementById("alert-row");
  row.classList.remove("hidden");
 
  // Alerta de Temperatura (Rango 18 a 30)
  const at = document.getElementById("alert-temp");
  if (last.temp >= 30) {
    at.className = "alert-bar alert-red"; at.textContent = "🌡️ CRÍTICO: Gabinete Caliente (" + fmt1(last.temp) + "°C)";
  } else if (last.temp <= 18) {
    at.className = "alert-bar alert-red"; at.textContent = "🌡️ CRÍTICO: Gabinete muy Frío (" + fmt1(last.temp) + "°C)";
  } else {
    at.className = "alert-bar alert-ok"; at.textContent = "🌡️ Temperatura Óptima (" + fmt1(last.temp) + "°C)";
  }
 
  // Alerta de Humedad (Máx 70)
  const ah = document.getElementById("alert-hum");
  if (last.hum >= 70) {
    ah.className = "alert-bar alert-red"; ah.textContent = "💧 PELIGRO: Exceso Humedad (" + fmt1(last.hum) + "%)";
  } else {
    ah.className = "alert-bar alert-ok"; ah.textContent = "💧 Humedad Estable (" + fmt1(last.hum) + "%)";
  }

  // Alerta de Movimiento (Máx 1.8)
  const ag = document.getElementById("alert-gforce");
  if (last.gforce > 1.8) {
    ag.className = "alert-bar alert-red"; ag.textContent = "⚠️ MOVIMIENTO DETECTADO (" + fmt1(last.gforce) + "g)";
  } else {
    ag.className = "alert-bar alert-ok"; ag.textContent = "🧭 Gabinete Estable";
  }

  // Alerta de Luz / Puerta
  const ap = document.getElementById("alert-puerta");
  if (last.distancia <= 10) {
    ap.className = "alert-bar alert-amber"; ap.textContent = "🚪 ALERTA: Puerta Abierta (" + fmt0(last.distancia) + "cm)";
  } else if (last.luz >= 50) {
    ap.className = "alert-bar alert-amber"; ap.textContent = "💡 ALERTA: Luz interna alta (" + fmt0(last.luz) + "%)";
  } else {
    ap.className = "alert-bar alert-ok"; ap.textContent = "🔒 Puerta cerrada y oscura";
  }
}
 
function updateCards(last) {
  document.getElementById("card-device-full").textContent = "ID Nodo: " + (last?.device ?? "—");
  document.getElementById("card-temp").textContent   = fmt1(last?.temp);
  document.getElementById("card-hum").textContent    = fmt1(last?.hum);
  document.getElementById("card-luz").textContent    = fmt0(last?.luz);
  document.getElementById("card-dist").textContent   = fmt0(last?.distancia);
  document.getElementById("card-gforce").textContent = fmt1(last?.gforce);
  document.getElementById("card-time").textContent   = fmtTs(last?.ts);
 
  const badge = document.getElementById("badge-status");
  badge.className = "badge-live";
  badge.innerHTML = '<span class="dot dot-green"></span> Sensores en línea';
}
 
function repaintTable(rows) {
  const tb = document.getElementById("table-body");
  tb.innerHTML = "";
  for (const r of rows.slice(-15).reverse()) {
    const tr = document.createElement("tr");
    tr.className = "border-b border-slate-700/60";
    tr.innerHTML = `
      <td class="py-2 pr-4 mono text-xs text-emerald-500">${fmtTs(r.ts)}</td>
      <td class="py-2 pr-4 text-rose-400 mono">${fmt1(r.temp)}</td>
      <td class="py-2 pr-4 text-cyan-400 mono">${fmt1(r.hum)}</td>
      <td class="py-2 pr-4 text-amber-400 mono">${fmt0(r.luz)}</td>
      <td class="py-2 pr-4 text-emerald-400 mono">${fmt0(r.distancia)}</td>
      <td class="py-2 pr-4 text-purple-400 mono">${fmt1(r.gforce)}</td>
    `;
    tb.appendChild(tr);
  }
}
 
async function fetchData() {
  const res     = await fetch("/api/last?n=200");
  const payload = await res.json();
  const rows    = payload.rows || [];
 
  const labels = rows.map(r => r.ts);
  tempChart.data.labels = humChart.data.labels = luzChart.data.labels = gChart.data.labels = labels;
  
  tempChart.data.datasets[0].data = rows.map(r => r.temp);
  humChart.data.datasets[0].data  = rows.map(r => r.hum);
  luzChart.data.datasets[0].data  = rows.map(r => r.luz);
  gChart.data.datasets[0].data    = rows.map(r => r.gforce);
  
  tempChart.update(); humChart.update(); luzChart.update(); gChart.update();
 
  repaintTable(rows);
  if (rows.length) {
    const last = rows[rows.length - 1];
    updateCards(last);
    updateAlerts(last);
  }
}
 
window.addEventListener("load", () => {
  initCharts();
  fetchData();
  setInterval(fetchData, 2000);
});
</script>
</body>
</html>
"""

@app.get("/")
def home():
    return render_template_string(HTML)

@app.get("/api/last")
def api_last():
    try:
        n = int(request.args.get("n", 100))
    except:
        n = 100
    rows = list(data_buffer)[-n:]
    return jsonify({"rows": rows, "count": len(rows)})

@app.post("/ingest")
def ingest():
    if request.headers.get("X-API-Key") != API_KEY:
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    
    # Se añadieron 'luz' y 'distancia' al diccionario que se guarda
    row = {
        "device": data.get("device", "esp32"),
        "temp": float(data.get("temp", 0.0)),
        "hum": float(data.get("hum", 0.0)),
        "gforce": float(data.get("gforce", 0.0)),
        "luz": float(data.get("luz", 0.0)),
        "distancia": float(data.get("distancia", 0.0)),
        "ts": float(data.get("ts", time.time()))
    }
    data_buffer.append(row)
    return jsonify({"status": "ok", "stored": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)