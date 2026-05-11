#!/usr/bin/env python3
"""Serve the stock correlation dashboard, auto-selecting a free port."""
import http.server
import os
import socket
import subprocess
import sys
import webbrowser

PREFERRED_PORTS = [8080, 8081, 8082, 8888, 9000, 9001]
DOCS_DIR = os.path.join(os.path.dirname(__file__), "docs")


def find_free_port(candidates):
    for port in candidates:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("", port))
            return port
        except OSError:
            print(f"Port {port} is in use, trying next…")
    raise RuntimeError("No free port found in candidates: " + str(candidates))


def refresh_data():
    script = os.path.join(os.path.dirname(__file__), "fetch_stats.py")
    if not os.path.exists(script):
        return
    print("Refreshing live stock data…")
    try:
        result = subprocess.run(
            ["uv", "run", script],
            capture_output=True, text=True, timeout=120,
            cwd=os.path.dirname(__file__)
        )
        if result.returncode == 0:
            print(result.stdout.strip())
        else:
            print("Warning: data refresh failed, using cached data.")
            print(result.stderr[-500:] if result.stderr else "")
    except Exception as e:
        print(f"Warning: could not refresh data ({e}), using cached data.")


if __name__ == "__main__":
    refresh_data()

    port = find_free_port(PREFERRED_PORTS)
    os.chdir(DOCS_DIR)

    url = f"http://localhost:{port}/"
    print(f"\nServing ETF Correlation Dashboard at {url}")
    print("Press Ctrl+C to stop.\n")

    try:
        webbrowser.open(url)
    except Exception:
        pass

    handler = http.server.SimpleHTTPRequestHandler
    handler.log_message = lambda self, fmt, *args: None  # quiet logs
    with http.server.HTTPServer(("", port), handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
