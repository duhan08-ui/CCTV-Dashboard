import json
import re
import socket
import threading
import urllib.parse
import urllib3
import webbrowser
import time
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 올림픽대로 핵심 지점 ID
DEFAULT_CAMERA_IDS = ["1013", "261", "301", "100", "36", "192", "531", "234", "243"]
TOPIS_INFO_URL = "https://topis.seoul.go.kr/map/selectCctvInfo.do"

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://topis.seoul.go.kr/map/openCctv.do"
})

def rewrite_m3u8(content, base_url):
    """M3U8 파일 내의 모든 경로를 우리 프록시 주소로 강제 변환 (재생 해결 핵심)"""
    lines = []
    for line in content.splitlines():
        line = line.strip()
        if not line: continue
        if line.startswith("#"):
            if "URI=" in line:
                line = re.sub(r'URI="([^"]+)"', lambda m: f'URI="/proxy?url={urllib.parse.quote(urllib.parse.urljoin(base_url, m.group(1)))}"', line)
            lines.append(line)
        else:
            full_url = urllib.parse.urljoin(base_url, line)
            lines.append(f"/proxy?url={urllib.parse.quote(full_url)}")
    return "\n".join(lines)

class ProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): return
    
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        
        if parsed.path == "/":
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode())
            
        elif parsed.path == "/api/exit":
            self.send_response(200); self.end_headers()
            print("👋 서버를 종료합니다...")
            threading.Thread(target=lambda: (time.sleep(0.5), os._exit(0))).start()
            
        elif parsed.path == "/api/cameras":
            cams = []
            for cid in DEFAULT_CAMERA_IDS:
                try:
                    r = SESSION.post(TOPIS_INFO_URL, data={"camId": cid, "cctvSourceCd": "HP"}, timeout=5).json()
                    row = r['rows'][0]
                    row['proxyUrl'] = f"/proxy?url={urllib.parse.quote(row['hlsUrl'])}"
                    cams.append(row)
                except: pass
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
            self.wfile.write(json.dumps(cams).encode())
            
        elif parsed.path == "/proxy":
            query = urllib.parse.parse_qs(parsed.query)
            target_url = query.get("url", [None])[0]
            if target_url:
                try:
                    resp = SESSION.get(target_url, timeout=10, verify=False)
                    content = resp.content
                    if ".m3u8" in target_url.lower() or b"#EXTM3U" in content:
                        content = rewrite_m3u8(content.decode(errors='ignore'), target_url).encode()
                    
                    self.send_response(200)
                    self.send_header("Content-Type", resp.headers.get("Content-Type", "application/octet-stream"))
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(content)
                except:
                    self.send_response(404); self.end_headers()

HTML_TEMPLATE = """<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <title>올림픽대로 실시간 CCTV</title>
    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
    <style>
        body { margin: 0; background: #0f172a; color: white; font-family: sans-serif; }
        header { padding: 15px 25px; background: #1e293b; display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #3b82f6; position: sticky; top:0; z-index:100; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap: 20px; padding: 20px; }
        .card { background: #1e293b; border-radius: 12px; overflow: hidden; border: 1px solid #334155; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        video { width: 100%; aspect-ratio: 16/9; background: black; display: block; }
        .title { padding: 12px; font-weight: bold; font-size: 14px; background: #334155; }
        .btn-group { display: flex; gap: 10px; }
        button { padding: 8px 16px; border-radius: 6px; border: none; cursor: pointer; font-weight: bold; transition: 0.2s; }
        .btn-refresh { background: #3b82f6; color: white; }
        .btn-refresh:hover { background: #2563eb; }
        .btn-exit { background: #ef4444; color: white; }
        .btn-exit:hover { background: #dc2626; }
    </style>
</head>
<body>
    <header>
        <h2 style="margin:0;">🚗 실시간 올림픽대로 CCTV</h2>
        <div class="btn-group">
            <button class="btn-refresh" onclick="location.reload()">새로고침</button>
            <button class="btn-exit" onclick="if(confirm('프로그램을 완전히 종료할까요?')) fetch('/api/exit').then(()=>window.close())">서버 종료</button>
        </div>
    </header>
    <div class="grid" id="grid"></div>
    <script>
        async function start() {
            try {
                const res = await fetch('/api/cameras');
                const cams = await res.json();
                const grid = document.getElementById('grid');
                grid.innerHTML = '';
                cams.forEach(cam => {
                    const div = document.createElement('div');
                    div.className = 'card';
                    div.innerHTML = `<div class="title">${cam.cctvName}</div><video id="v-${cam.cctvId}" controls autoplay muted playsinline></video>`;
                    grid.appendChild(div);
                    if (Hls.isSupported()) {
                        const hls = new Hls({ lowLatencyMode: true });
                        hls.loadSource(cam.proxyUrl);
                        hls.attachMedia(document.getElementById('v-' + cam.cctvId));
                    }
                });
            } catch(e) { console.error("로드 실패", e); }
        }
        start();
    </script>
</body>
</html>"""

def main():
    # 빈 포트 자동 할당
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]
        
    server = ThreadingHTTPServer(('127.0.0.1', port), ProxyHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    
    url = f"http://127.0.0.1:{port}"
    print(f"✅ 서버 실행 중: {url}")
    webbrowser.open(url)
    
    try:
        while True: time.sleep(1)
    except: os._exit(0)

if __name__ == "__main__":
    main()