"""HTTP echo server - logs all incoming requests."""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class EchoHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._respond("GET")
    def do_POST(self):
        self._respond("POST")
    def do_PUT(self):
        self._respond("PUT")
    def do_DELETE(self):
        self._respond("DELETE")

    def _respond(self, method):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode() if length else ""

        info = {
            "method": method,
            "path": self.path,
            "headers": dict(self.headers),
            "body": body,
            "client": self.client_address,
        }
        response = json.dumps(info, indent=2)
        print(f"\n[{method}] {self.path}")
        for k, v in self.headers.items():
            print(f"  {k}: {v}")
        if body:
            print(f"  BODY: {body}")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(response.encode())

print("Echo server on http://localhost:8003")
HTTPServer(("127.0.0.1", 8003), EchoHandler).serve_forever()
