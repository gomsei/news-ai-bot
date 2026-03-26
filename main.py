import os
test_key = os.getenv("GEMINI_API_KEY")
if test_key:
    print(f"API 키 로드 성공! 앞글자: {test_key[:4]}****")
else:
    print("API 키 로드 실패: 환경 변수가 비어있습니다.")
