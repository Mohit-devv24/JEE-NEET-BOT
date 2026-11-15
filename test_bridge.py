from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time
import subprocess

received = []

class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        data = self.rfile.read(length)
        received.append(data.decode("utf-8", errors="ignore"))
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(b"OK")

server = HTTPServer(("127.0.0.1", 8899), Handler)
t = threading.Thread(target=server.serve_forever)
t.daemon = True
t.start()

print("Server started on 127.0.0.1:8899")

from chrome_bridge import run_js_in_drive_tab
js = """
fetch('http://127.0.0.1:8899', {
    method: 'POST',
    body: 'HELLO_FROM_CHROME_TAB'
}).then(r => r.text()).catch(e => e.toString())
"""
res = run_js_in_drive_tab(js)
print("JS result:", res)
time.sleep(1)
print("Received on server:", received)
server.shutdown()
