import http.server
import socketserver
import os

PORT = 3000
DIRECTORY = "dist"

class SPAHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
    
    def do_GET(self):
        # 如果请求的是API路径，直接返回404
        if self.path.startswith('/api/'):
            self.send_error(404)
            return
        
        # 检查文件是否存在
        file_path = os.path.join(DIRECTORY, self.path.lstrip('/'))
        if self.path != '/' and not os.path.exists(file_path):
            # 对于不存在的路径，返回index.html（SPA路由）
            self.path = '/'
        
        return super().do_GET()

os.chdir('/Users/gamidy/plm-system/frontend')
with socketserver.TCPServer(("", PORT), SPAHandler) as httpd:
    print(f"Serving SPA at http://localhost:{PORT}")
    httpd.serve_forever()
