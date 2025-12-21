from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class SimpleHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        print("\n[MOCK FINAL AGENT] Received Decision:")
        try:
            print(json.dumps(json.loads(post_data), indent=2))
        except json.JSONDecodeError:
            print(post_data.decode('utf-8'))
        
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"status":"received"}')

if __name__ == '__main__':
    port = 9001
    httpd = HTTPServer(('0.0.0.0', port), SimpleHandler)
    print(f"Mock Final Agent listening on port {port}...")
    httpd.serve_forever()
