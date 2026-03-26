import os
import google.generativeai as genai

# 환경 변수 읽기 (GitHub Actions의 env 설정과 이름이 같아야 함)
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    # 키가 없을 경우 에러 메시지를 출력하게 하여 디버깅을 돕습니다.
    raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다. GitHub Secrets를 확인하세요.")

# API 키 설정
genai.configure(api_key=api_key)
