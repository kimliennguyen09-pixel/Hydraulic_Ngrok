from __future__ import annotations

import csv
import json
import mimetypes
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "Bang thong ke.csv"

NUMERIC_COLUMNS = {
    "Elevation (Ground) (m)", "Elevation (Rim) (m)", "Elevation (Invert) (m)",
    "Flow (Total In) (L/s)", "Flow (Total Out) (L/s)", "Depth (Out) (m)",
    "Depth (Flooding) (m)", "Depth (Surcharged) (m)",
    "Hydraulic Grade Line (Out) (m)", "Hydraulic Grade Line (In) (m)",
}


def load_nodes():
    with DATA_FILE.open(encoding="utf-8-sig", newline="") as handle:
        nodes = list(csv.DictReader(handle))
    for row in nodes:
        for key in NUMERIC_COLUMNS:
            try:
                row[key] = float(row[key])
            except (TypeError, ValueError):
                row[key] = 0.0
        row["Is Overflowing?"] = str(row["Is Overflowing?"]).strip().lower() == "true"
        rim = row["Elevation (Rim) (m)"]
        invert = row["Elevation (Invert) (m)"]
        hgl = max(row["Hydraulic Grade Line (In) (m)"], row["Hydraulic Grade Line (Out) (m)"])
        row["Available Depth (m)"] = round(rim - invert, 3)
        row["HGL Margin (m)"] = round(rim - hgl, 3)
        row["Fill Ratio (%)"] = round(
            100 * row["Depth (Out) (m)"] / max(row["Available Depth (m)"], 0.001), 1
        )
        flooding = row["Depth (Flooding) (m)"]
        if flooding <= 0:
            flood_level = "None"
        elif flooding <= 0.10:
            flood_level = "Low"
        elif flooding <= 0.30:
            flood_level = "Moderate"
        elif flooding <= 0.50:
            flood_level = "High"
        else:
            flood_level = "Very High"
        row["Flood Level"] = flood_level

        warning_reasons = []
        if flooding > 0:
            warning_reasons.append(f"Ngập sâu {flooding:.2f} m")
        if row["Is Overflowing?"]:
            warning_reasons.append("Nút đang tràn")
        if row["HGL Margin (m)"] <= 0:
            warning_reasons.append("HGL bằng/vượt cao độ nắp")
        elif row["HGL Margin (m)"] < 0.5:
            warning_reasons.append("Biên an toàn HGL dưới 0,50 m")
        if row["Fill Ratio (%)"] >= 100:
            warning_reasons.append("Nút đầy hoặc quá tải")
        elif row["Fill Ratio (%)"] >= 75:
            warning_reasons.append("Tỷ lệ đầy từ 75%")
        row["Warning Reasons"] = warning_reasons
        if row["Is Overflowing?"] or flooding > 0 or row["HGL Margin (m)"] <= 0:
            risk = "Critical"
        elif row["HGL Margin (m)"] < 0.5 or row["Fill Ratio (%)"] >= 75:
            risk = "Warning"
        else:
            risk = "Normal"
        row["Risk"] = risk
    return nodes


NODES = load_nodes()


def summary():
    total = len(NODES)
    flows = [n["Flow (Total Out) (L/s)"] for n in NODES]
    margins = [n["HGL Margin (m)"] for n in NODES]
    risks = {key: sum(n["Risk"] == key for n in NODES) for key in ("Critical", "Warning", "Normal")}
    flood_levels = {key: sum(n["Flood Level"] == key for n in NODES) for key in ("Very High", "High", "Moderate", "Low", "None")}
    flooded = [n for n in NODES if n["Depth (Flooding) (m)"] > 0]
    return {
        "total_nodes": total,
        "overflowing": sum(n["Is Overflowing?"] for n in NODES),
        "max_flow": round(max(flows, default=0), 2),
        "avg_flow": round(sum(flows) / total, 2) if total else 0,
        "max_depth_out": round(max((n["Depth (Out) (m)"] for n in NODES), default=0), 2),
        "min_hgl_margin": round(min(margins, default=0), 2),
        "flooded_nodes": len(flooded),
        "max_flood_depth": round(max((n["Depth (Flooding) (m)"] for n in flooded), default=0), 2),
        "avg_flood_depth": round(sum(n["Depth (Flooding) (m)"] for n in flooded) / len(flooded), 2) if flooded else 0,
        "flood_levels": flood_levels,
        "risks": risks,
    }


class DashboardHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        clean = urlparse(path).path.lstrip("/")
        if not clean:
            clean = "templates/index.html"
        elif clean == "node":
            clean = "templates/node-detail.html"
        return str(BASE_DIR / clean)

    def log_message(self, fmt, *args):
        print(f"[dashboard] {self.address_string()} - {fmt % args}")

    def send_json(self, payload, status=200):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            return self.send_json({"status": "ok", "records": len(NODES)})
            
        if parsed.path == "/api/summary":
            return self.send_json(summary())
        if parsed.path == "/api/nodes":
            query = parse_qs(parsed.query)
            risk = query.get("risk", ["all"])[0]
            search = query.get("q", [""])[0].casefold().strip()
            rows = [n for n in NODES if (risk == "all" or n["Risk"] == risk)]
            if search:
                rows = [n for n in rows if search in str(n["Label"]).casefold() or search in str(n["ID"]).casefold()]
            return self.send_json({"count": len(rows), "items": rows})
        if parsed.path.startswith("/api/nodes/"):
            node_id = parsed.path.rsplit("/", 1)[-1]
            node = next((n for n in NODES if str(n["ID"]) == node_id), None)
            return self.send_json(node or {"error": "Không tìm thấy nút"}, 200 if node else 404)
        if parsed.path == "/api/charts":
            top_flow = sorted(NODES, key=lambda n: n["Flow (Total Out) (L/s)"], reverse=True)[:12]
            hgl = sorted(NODES, key=lambda n: n["HGL Margin (m)"])[:12]
            flood_depth = sorted((n for n in NODES if n["Depth (Flooding) (m)"] > 0), key=lambda n: n["Depth (Flooding) (m)"], reverse=True)[:12]
            return self.send_json({"top_flow": top_flow, "lowest_hgl_margin": hgl, "flood_depth": flood_depth})
        return super().do_GET()


def main():
    host = os.getenv("DASHBOARD_HOST", "127.0.0.1")
    port = int(os.getenv("DASHBOARD_PORT", "8000"))
    mimetypes.add_type("text/javascript", ".js")
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    print(f"GeoAI Hydraulic Dashboard (local): http://{host}:{port}")

   
    ngrok_token = os.getenv("NGROK_AUTHTOKEN", "3IE2kT6G690UGhl6IcW3w6ZoXVQ_5do9TK4828d8uUSQYWZVG")
    if ngrok_token:
        try:
            from pyngrok import conf, ngrok as _ngrok
            conf.get_default().auth_token = ngrok_token
            tunnel = _ngrok.connect(port, "http")
            print(f"GeoAI Hydraulic Dashboard (ngrok):  {tunnel.public_url}")
        except ImportError:
            print("[warn] pyngrok chưa được cài. Chạy: pip install pyngrok")
        except Exception as exc:
            print(f"[warn] Không mở được ngrok tunnel: {exc}")
    else:
        print("[info] Đặt biến NGROK_AUTHTOKEN=<token> để bật ngrok tunnel tự động.")
    # --------------------------------

    server.serve_forever()


if __name__ == "__main__":
    main()

