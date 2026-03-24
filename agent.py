import subprocess
import sys
import os
import http.client
import json

# 🔑 환경변수에서 API 키 로드 (GitHub Secrets 또는 Docker -e 옵션)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def ask_gemini_to_fix(filename, error_msg):
    """Gemini API에 에러 수리를 요청하고 수정된 코드를 반환합니다."""
    
    if not GEMINI_API_KEY:
        print("❌ [에러] GEMINI_API_KEY가 설정되지 않았습니다.")
        sys.exit(1)

    print(f"🔑 API 인증 시도 중... (Key: {GEMINI_API_KEY[:4]}***)")
    
    # 수리할 파일 내용 읽기
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            original_code = f.read()
    except FileNotFoundError:
        original_code = "# 파일이 없어 새로 생성되었습니다."

    # AI에게 보낼 프롬프트 구성
    prompt = (
        f"Fix the Python error below. Output ONLY the fixed code without any explanation or markdown backticks.\n"
        f"Error: {error_msg}\n"
        f"Original Code:\n{original_code}"
    )
    
    # Google Gemini API 설정
    host = "generativelanguage.googleapis.com"
    # 타겟 모델: gemini-3.1-flash-lite-preview
    endpoint = f"/v1beta/models/gemini-3.1-flash-lite-preview:generateContent?key={GEMINI_API_KEY}"

    conn = http.client.HTTPSConnection(host)
    payload = json.dumps({
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    })
    headers = {'Content-Type': 'application/json'}

    try:
        conn.request("POST", endpoint, payload, headers)
        res = conn.getresponse()
        response_data = res.read().decode("utf-8")
        data = json.loads(response_data)

        if 'candidates' in data:
            fixed_code = data['candidates'][0]['content']['parts'][0]['text']
            # 마크다운 기호(```python 등)가 포함된 경우 제거
            clean_code = fixed_code.replace("```python", "").replace("```", "").strip()
            return clean_code
        else:
            print(f"❌ API 응답 실패: {response_data}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ 통신 중 오류 발생: {e}")
        sys.exit(1)

def run_and_fix(target_file):
    """파일을 실행하고 에러 발생 시 자동 수리합니다."""
    
    # 테스트용: happy.py가 없거나 내용이 비어있으면 에러 코드 삽입
    if not os.path.exists(target_file) or os.stat(target_file).st_size == 0:
        with open(target_file, "w", encoding='utf-8') as f:
            f.write("print(10 / 0)  # 의도적인 ZeroDivisionError")

    print(f"🚀 [{target_file}] 실행 시도 중...")
    
    # 🎯 핵심: 현재 환경의 파이썬(sys.executable)으로 실행하여 도커 내 에러 방지
    result = subprocess.run(
        [sys.executable, target_file], 
        capture_output=True, 
        text=True
    )

    if result.returncode == 0:
        print("✅ 성공! 결과:\n", result.stdout)
    else:
        print("❌ 에러 발생! AI 분석 및 수리 시작.")
        print(f"상세 에러:\n{result.stderr}")
        
        # 1. Gemini에게 수리 요청
        fixed_code = ask_gemini_to_fix(target_file, result.stderr)
        
        # 2. 수리된 코드로 파일 덮어쓰기
        with open(target_file, "w", encoding='utf-8') as f:
            f.write(fixed_code)
        print(f"🛠️ [{target_file}] 자가 수리 완료.")

        # 3. 재검증 실행
        print(f"🔄 수리된 코드 재검증 중...")
        final_res = subprocess.run([sys.executable, target_file], capture_output=True, text=True)
        
        if final_res.returncode == 0:
            print(f"✅ 최종 검증 성공! 출력 결과:\n{final_res.stdout}")
        else:
            print(f"⚠️ 재검증 실패. 추가 수리가 필요할 수 있습니다.")
            print(f"최종 에러:\n{final_res.stderr}")

if __name__ == "__main__":
    # 감시 및 수리할 파일 지정
    run_and_fix("happy.py")
