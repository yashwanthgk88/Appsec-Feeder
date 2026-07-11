import json, os, sys, re
sys.path.insert(0, '.')
os.environ['DB_PATH']='/tmp/demo.db'
import config; config.DB_PATH='/tmp/demo.db'
import store, settings as S
from http.server import BaseHTTPRequestHandler, HTTPServer

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        if ctype == "text/html": data = body.encode()
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data))); self.end_headers()
        self.wfile.write(data)
    def do_GET(self):
        if self.path == "/healthz": return self._send(200, {"ok": True})
        if self.path == "/admin": return self._send(200, open("admin.html").read(), "text/html")
        if self.path == "/": return self._send(200, open("app.html").read(), "text/html")
        m = re.match(r"/api/feeds/(\w+)/index", self.path)
        if m:
            if self.headers.get("x-api-token") != "demo-token": return self._send(401, {"error":"Invalid token"})
            d = store.get_index(m.group(1))
            return self._send(200, d) if d else self._send(404, {"error":"no index"})
        m = re.match(r"/api/briefings/(\d+)", self.path)
        if m:
            if self.headers.get("x-api-token") != "demo-token": return self._send(401, {"error":"Invalid token"})
            b = store.get_briefing(int(m.group(1)))
            return self._send(200, b) if b else self._send(404, {"error":"not found"})
        if self.path == "/api/admin/config":
            if self.headers.get("x-admin-token") != "demo-admin": return self._send(401, {"error":"Invalid admin token"})
            return self._send(200, {"llm": S.get_llm(), "dials": S.get_dials(),
                                    "prompts": {k: S.get_prompt(k) for k in S.DEFAULT_PROMPTS},
                                    "note": "keys are env-only"})
        self._send(404, {"error": "not found"})

HTTPServer(("127.0.0.1", 8000), H).serve_forever()
