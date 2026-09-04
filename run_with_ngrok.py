"""Khởi chạy dashboard và tạo public URL bằng ngrok."""
import os
import subprocess
import sys
import time


def main():
    try:
        from pyngrok import ngrok
    except ImportError:
        raise SystemExit("Thiếu pyngrok. Chạy: python -m pip install -r requirements.txt")

    port = int(os.getenv("DASHBOARD_PORT", "8000"))
    token = os.getenv("NGROK_AUTHTOKEN", "").strip()
    if token:
        ngrok.set_auth_token(token)
    process = subprocess.Popen([sys.executable, "api.py"], cwd=os.path.dirname(__file__))
    try:
        time.sleep(1)
        tunnel = ngrok.connect(port, bind_tls=True)
        print(f"\nDashboard local: http://127.0.0.1:{port}")
        print(f"Dashboard ngrok: {tunnel.public_url}\n")
        process.wait()
    except KeyboardInterrupt:
        pass
    finally:
        ngrok.kill()
        process.terminate()


if __name__ == "__main__":
    main()
