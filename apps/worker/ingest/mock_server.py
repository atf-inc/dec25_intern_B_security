from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import sys

class SimpleHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        print("\n[MOCK DOWNSTREAM] Received POST request:")
        print(f"Headers: {self.headers}")
        try:
            print(json.dumps(json.loads(post_data), indent=2))
        except:
            print(post_data.decode('utf-8'))
        
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
        
        # Optional: Print separator
        print("-" * 50)

if __name__ == "__main__":
    port = 9000
    print(f"Mock Decision Agent listening on port {port}...")
    try:
        httpd = HTTPServer(('0.0.0.0', port), SimpleHandler)
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping mock server.")
        sys.exit(0)
