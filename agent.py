import subprocess
import sys
import os
import http.client
import json

# 🔑 GitHub Secrets에서 가져오기
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def ask_gemini_to_fix(filename, error_msg):
    # 🔍 API 키 전달 여부 확인 (보안상 앞 3자리만 출력)
    if not GEMINI_API_KEY or len(GEMINI_API_KEY) < 5:
        print("❌ [환경변수 에러] API 키가 전달되지 않았습니다. check-code.yml 설정을 확인하세요.")
        sys.exit(1)
    
    print(f"🔑 API 인증 시도 중... (Key: {GEMINI_API_KEY[:3]}***)")
    print("🤖 Gemini AI에게 수리를 요청하는 중...")
    
    with open(filename, 'r', encoding='utf-8') as f:
        code = f.read()

    prompt = f"Fix the Python error below. Output ONLY the fixed code without any explanation.\nError: {error_msg}\nCode: {code}"
    
    host = "generativelanguage.googleapis.com"
    # 🎯 우리가 직접 확인한 정확한 타겟 모델명 사용
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
            # 마크다운 제거
            return fixed_code.replace("```python", "").replace("```", "").strip()
        else:
            print(f"❌ API 응답 실패: {response_text}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ 통신 오류 발생: {e}")
        sys.exit(1)

def run_and_fix(filename):
    print(f"🚀 [{filename}] 실행 시도...")
    # 테스트용 에러 코드 생성
    with open(filename, "w", encoding='utf-8') as f:
        f.write("print(10 / 0)")
        
    result = subprocess.run([sys.executable, filename], capture_output=True, text=True)

    if result.returncode == 0:
        print("✅ 성공! 결과:\n", result.stdout)
    else:
        print("❌ 에러 발생! AI 분석 시작.")
        fixed_code = ask_gemini_to_fix(filename, result.stderr)
        
        with open(filename, "w", encoding='utf-8') as f:
            f.write(fixed_code)
            
        print(f"🛠️ 자가 수리 완료. 재검증 중...")
        final_res = subprocess.run([sys.executable, filename], capture_output=True, text=True)
        print(f"✅ 최종 결과: {final_res.stdout}")

if __name__ == "__main__":
    run_and_fix("happy.py")
