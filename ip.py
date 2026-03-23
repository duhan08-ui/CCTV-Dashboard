import threading
import time
import os
import socket
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from scapy.all import sniff, IP, DNS, DNSQR

# --- 데이터 저장소 ---
# { "IP주소": ["접속한 사이트1", "사이트2", ...] }
traffic_log = {}
device_names = {
    "127.0.0.1": "내 PC",
    "192.168.0.5": "아빠 아이폰",
    "192.168.0.10": "거실 태블릿"
}

def packet_callback(pkt):
    """네트워크 패킷을 가로채서 DNS 요청(사이트 접속) 기록"""
    if pkt.haslayer(DNS) and pkt.getlayer(DNS).qr == 0:
        ip = pkt[IP].src
        domain = pkt[DNSQR].qname.decode('utf-8').strip('.')
        
        # 무시할 도메인 (광고, 시스템 통신 등) 제외 로직 추가 가능
        if ip not in traffic_log:
            traffic_log[ip] = []
        
        if domain not in traffic_log[ip]:
            traffic_log[ip].insert(0, f"[{time.strftime('%H:%M:%S')}] {domain}")
            # 너무 쌓이지 않게 최근 20개만 유지
            traffic_log[ip] = traffic_log[ip][:20]

# --- 웹 대시보드 ---
HTML_TEMPLATE = """<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <title>우리집 네트워크 모니터링</title>
    <style>
        body { background: #1a202c; color: white; font-family: sans-serif; padding: 20px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
        .card { background: #2d3748; padding: 15px; border-radius: 10px; border: 1px solid #4a5568; }
        h2 { color: #63b3ed; border-bottom: 2px solid #4a5568; padding-bottom: 10px; }
        ul { list-style: none; padding: 0; font-size: 13px; }
        li { padding: 5px 0; border-bottom: 1px solid #3d4957; color: #cbd5e0; }
        header { display: flex; justify-content: space-between; margin-bottom: 30px; }
        .exit-btn { background: #f56565; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; }
    </style>
    <script>
        setInterval(() => location.reload(), 5000); // 5초마다 자동 갱신
    </script>
</head>
<body>
    <header>
        <h1>🏠 우리집 실시간 접속 리포트 (Beta)</h1>
        <button class="exit-btn" onclick="fetch('/api/exit').then(()=>window.close())">프로그램 종료</button>
    </header>
    <div class="grid">
        {%CONTENT%}
    </div>
</body>
</html>"""

class MonitorHandler(BaseHTTPRequestHandler):
    def log_message(self, *args): return
    def do_GET(self):
        if self.path == "/":
            content = ""
            for ip, sites in traffic_log.items():
                name = device_names.get(ip, ip)
                site_list = "".join([f"<li>{s}</li>" for s in sites])
                content += f'<div class="card"><h2>📱 {name}</h2><ul>{site_list}</ul></div>'
            
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers()
            self.wfile.write(HTML_TEMPLATE.replace("{%CONTENT%}", content).encode())
            
        elif self.path == "/api/exit":
            self.send_response(200); self.end_headers()
            os._exit(0)

def start_sniffing():
    """패킷 감시 시작 (관리자 권한 필요할 수 있음)"""
    print("📡 네트워크 감시 중... (사이트 접속 시 기록됩니다)")
    sniff(prn=packet_callback, store=0)

def main():
    # 1. 패킷 감시 스레드 시작
    t = threading.Thread(target=start_sniffing, daemon=True)
    t.start()
    
    # 2. 웹 서버 시작
    server = ThreadingHTTPServer(('127.0.0.1', 8888), MonitorHandler)
    print("✅ 대시보드 실행: http://127.0.0.1:8888")
    webbrowser.open("http://127.0.0.1:8888")
    server.serve_forever()

if __name__ == "__main__":
    main()