import subprocess
import sys
import os
import http.client
import json

# 🔒 GitHub Secrets에서 가져오기
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def ask_gemini_to_fix(filename, error_msg):
    # 🔍 키가 들어왔는지 확인하는 로그 (보안을 위해 앞 3자리만 출력)
    if not GEMINI_API_KEY:
        print("❌ [환경변수 에러] GEMINI_API_KEY가 비어있습니다. check-code.yml의 env 설정을 확인하세요.")
        sys.exit(1)
    else:
        print(f"🔑 API 키 로드 성공 (앞 3자리: {GEMINI_API_KEY[:3]}...)")

    print("🤖 Gemini AI에게 수리를 요청하는 중...")
    
    # ... (나머지 코드는 성공했던 코드와 동일) ...
    
    with open(filename, 'r', encoding='utf-8') as f:
        code = f.read()

    prompt = f"Fix the Python error below. Output ONLY the fixed code.\nError: {error_msg}\nCode: {code}"
    
    host = "generativelanguage.googleapis.com"
    # ⭐ 우리 계정에서 확인된 최신 모델명입니다.
    endpoint = f"/v1beta/models/gemini-3.1-flash-lite-preview:generateContent?key={GEMINI_API_KEY}"

    conn = http.client.HTTPSConnection(host)
    payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]})
    headers = {'Content-Type': 'application/json'}

    try:
        conn.request("POST", endpoint, payload, headers)
        res = conn.getresponse()
        response_text = res.read().decode("utf-8")
        data = json.loads(response_text)

        if 'candidates' in data:
            fixed_code = data['candidates'][0]['content']['parts'][0]['text']
            return fixed_code.replace("```python", "").replace("```", "").strip()
        else:
            print(f"❌ API 실패 상세: {response_text}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ 통신 오류: {e}")
        sys.exit(1)

def run_and_fix(filename):
    print(f"🚀 [{filename}] 실행 시도...")
    result = subprocess.run([sys.executable, filename], capture_output=True, text=True)

    if result.returncode == 0:
        print("✅ 성공! 결과:\n", result.stdout)
    else:
        print("❌ 에러 발생! AI 분석 시작.")
        fixed_code = ask_gemini_to_fix(filename, result.stderr)
        
        with open(filename, "w", encoding='utf-8') as f:
            f.write(fixed_code)
            
        print(f"🛠️ 자가 수리 완료. 재검증...")
        final_res = subprocess.run([sys.executable, filename], capture_output=True, text=True)
        print(f"✅ 최종 결과: {final_res.stdout if final_res.returncode == 0 else final_res.stderr}")

if __name__ == "__main__":
    with open("happy.py", "w", encoding='utf-8') as f:
        f.write("print(10 / 0)")
    run_and_fix("happy.py")
