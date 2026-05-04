import urllib.request
import json
import os, sys
import time
from datetime import datetime, timedelta, date
from difflib import SequenceMatcher
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

#from dotenv import load_dotenv
#load_dotenv()

import holidays
kr_holidays = holidays.KR()

# 공휴일여부, 최근영업일 파악
##################################################################
def get_last_working_day(holiday_dict, base_date):
    today = base_date
    
    # 1. 오늘 상태 확인 로직
    today_holiday_name = holiday_dict.get(today)
    is_weekend = today.weekday() >= 5  # 5: 토, 6: 일
    
    # 휴일 사유 결정
    if today_holiday_name and is_weekend:
        today_reason = f"{'토요일' if today.weekday()==5 else '일요일'}({today_holiday_name})"
    elif today_holiday_name:
        today_reason = today_holiday_name
    elif is_weekend:
        today_reason = "토요일" if today.weekday() == 5 else "일요일"
    else:
        today_reason = "정상 영업일"
    
    is_today_holiday = is_weekend or (today_holiday_name is not None)

    # 2. 가장 최근 영업일 역추적 (오늘 제외 어제부터 탐색)
    search_date = today - timedelta(days=1)
    days_ago = 1
    
    while True:
        # 주말도 아니고 공휴일 딕셔너리에도 없는 날 찾기
        if search_date.weekday() < 5 and search_date not in holiday_dict:
            last_working_day = search_date
            break
        search_date -= timedelta(days=1)
        days_ago += 1
        
    return {
        "holiday_yn":is_today_holiday,
        "days_ago": days_ago,
        "today": today,
        "reason": today_reason
    }


# 1. 네이버 API 인증 정보 (본인의 정보를 입력하세요)
##################################################################
CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

##################################################################
def is_similar(a, b, threshold=0.5):
    """두 문자열(제목)의 유사도를 계산"""
    return SequenceMatcher(None, a, b).ratio() > threshold

def get_kb_news_automated():
    # 검색 키워드 확장 리스트
    ##################################################################
    keywords = [ 
        "AI 신용평가",
        "금융A I",
        "AI 리스크관리",
        "AI 사기탐지",
        "AI 금융규제",
        "AI 공시",
        "AI 회계감사",
        "AI 내부감사",
        "디지털감사",
        "스마트감사",
        "AI 감사도구",
        "AI 이상탐지",
        "AI 감사기준",
        "감사자동화",
        "금감원 AI",
        "감사원 AI",
        "AI 감사위험",
        "AI 재무감사",
        "금융 AI 규제"
    ]
    ##################################################################
    exclude_words = []
    
    all_news = {}
    now = datetime.now()
    last_working_day = now - timedelta(days=day_check_result["days_ago"]) 

    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] 뉴스 수집 시작...")

    # --- 1단계: 키워드별 뉴스 수집 및 중복 제거 ---
    for kw in keywords:
        time.sleep(0.1)

        encText = urllib.parse.quote(kw)
        url = f"https://openapi.naver.com/v1/search/news.json?query={encText}&display=10&sort=sim"

        request = urllib.request.Request(url)
        request.add_header("X-Naver-Client-Id", CLIENT_ID)
        request.add_header("X-Naver-Client-Secret", CLIENT_SECRET)

        try:
            response = urllib.request.urlopen(request)
            items = json.loads(response.read())['items']

            for item in items:
                link = item['link']
                if link in all_news: continue 

                # 날짜 파싱 및 24시간 필터링
                pub_date = datetime.strptime(item['pubDate'], "%a, %d %b %Y %H:%M:%S %z").replace(tzinfo=None)
                
                if pub_date > last_working_day:
                    title = item['title'].replace('<b>', '').replace('</b>', '').replace('&quot;', '"')
                    desc = item['description'].replace('<b>', '').replace('</b>', '').replace('&quot;', '"')

                    # [추가] 제외 단어가 하나라도 포함되어 있으면 스킵
                    if any(word in title for word in exclude_words):
                        continue  # 다음 뉴스로 넘어감
                        
                    all_news[link] = {
                        'date': pub_date.strftime("%Y-%m-%d %H:%M"),
                        'title': title,
                        'desc': desc,
                        'link': link,
                        'raw_date': pub_date,
                        'keyword': kw
                    }
                else:
                    break 
        except Exception as e:
            print(f"검색 오류 ({kw}): {e}")

    # 리스트로 변환 및 기본 정렬 (점수 높은 순 -> 최신순)
    initial_list = sorted(all_news.values(), key=lambda x: (x['raw_date']), reverse=True)

    # --- 2단계: 유사 기사 필터링 (더 좋은 기사 남기기) ---
    final_unique_news = []
    for new_item in initial_list:
        is_duplicate = False
        for i, existing in enumerate(final_unique_news):
            if is_similar(new_item['title'], existing['title'], threshold=0.6):
                is_duplicate = True
                # 점수가 더 높거나, 점수가 같은데 제목이 더 길면(정보량이 많으면) 교체
                if (len(new_item['title']) > len(existing['title'])):
                    final_unique_news[i] = new_item
                break
        
        if not is_duplicate:
            final_unique_news.append(new_item)
            
    return final_unique_news


def send_news_gmail(news_list):
    # 1. 메일 설정
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = os.getenv("GMAIL_USER")
    app_password = os.getenv("GMAIL_APP_PASSWORD")
    receiver_email = "gomsei@gmail.com" #jungsun8610@gmail.com

    # 2. 메일 본문(HTML) 디자인
    html_content = f"""
    <html>
    <head>
        <style>
            .container {{ font-family: 'Malgun Gothic', sans-serif; padding: 20px; }}
            .header {{ background-color: #ffcc00; padding: 10px; text-align: center; border-radius: 5px; }}
            .news-item {{ border-bottom: 1px solid #ddd; padding: 15px 0; }}
            .title {{ font-size: 16px; font-weight: bold; color: #333; text-decoration: none; }}
            .desc {{ font-size: 12px; color: #666666; text-decoration: none; }}
            .meta {{ color: #888; font-size: 12px; margin-top: 5px; }}
            .tag {{ background: #eee; padding: 2px 5px; border-radius: 3px; font-size: 11px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>📅 AI/금융/감사 뉴스 리포트 ({datetime.now().strftime('%m/%d')})</h2>
            </div>
    """

    for news in news_list:
        html_content += f"""
            <div class="news-item">
                <a href="{news['link']}" class="title">{news['title']}</a><br/>
                <div class="desc">{news['desc']}</div>
                <div class="meta">
                    <span>{news['date']}</span> | 
                    <span class="tag">#{news['keyword']}</span>
                </div>
            </div>
        """

    html_content += """
        </div>
    </body>
    </html>
    """

    # 3. 메일 객체 생성
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = f"[{datetime.now().strftime('%m/%d')}] AI/금융/감사 관련 주요 뉴스 브리핑"
    msg.attach(MIMEText(html_content, 'html'))

    # 4. 메일 전송
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls() # 보안 연결
        server.login(sender_email, app_password)
        server.sendmail(sender_email, receiver_email.split(','), msg.as_string())
        server.quit()
        print("✅ 이메일 발송 성공!")
    except Exception as e:
        print(f"❌ 이메일 발송 실패: {e}")


        
# --- 3단계: 결과 실행 및 출력 ---
if __name__ == "__main__":
    day_check_result = get_last_working_day(kr_holidays, datetime.now(ZoneInfo("Asia/Seoul")).date()) #테스트:date(2026,5,5)
    if day_check_result["holiday_yn"]:
        print(day_check_result["reason"])
        sys.exit(0)
    else:
        print(day_check_result["today"], day_check_result["days_ago"])
    
    results = get_kb_news_automated()
    send_news_gmail(results[:10])
