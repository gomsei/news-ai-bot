import os
import smtplib
import datetime
import pandas as pd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from concurrent.futures import ThreadPoolExecutor
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

# 환경 변수 설정
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
RECIPIENTS = os.getenv("RECIPIENTS").split(",")
KEYWORDS = ["인공지능", "반도체", "디지털 트랜스포메이션"] # 또는 환경변수 처리

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

def fetch_naver_news(keyword):
    url = f"https://search.naver.com/search.naver?where=news&query={keyword}&sm=tab_opt&sort=1"
    res = requests.get(url)
    soup = BeautifulSoup(res.text, 'html.parser')
    news_list = []
    for item in soup.select(".news_tit")[:5]:
        news_list.append({'title': item.get_text(), 'link': item['href']})
    return news_list

def fetch_google_news(keyword):
    url = f"https://news.google.com/rss/search?q={keyword}&hl=ko&gl=KR&ceid=KR:ko"
    res = requests.get(url)
    soup = BeautifulSoup(res.text, 'xml')
    news_list = []
    for item in soup.select("item")[:5]:
        news_list.append({'title': item.title.text, 'link': item.link.text})
    return news_list

def get_gemini_summary(news_data):
    combined_text = "\n".join([f"제목: {n['title']}" for n in news_data])
    prompt = f"""
    다음 뉴스 리스트 중에서 가장 중요하고 인기가 높을 법한 기사 10개를 선정해줘.
    각 기사에 대해 제목, 링크를 유지하고 내용을 2~3문장으로 핵심 요약해줘.
    결과는 반드시 HTML의 <li> 태그 형식으로 작성해줘.
    ---
    {combined_text}
    """
    response = model.generate_content(prompt)
    return response.text

def send_email(html_content):
    msg = MIMEMultipart()
    msg['Subject'] = f"[일일 업무 브리핑] {datetime.date.today()} 주요 뉴스"
    msg['From'] = GMAIL_USER
    msg['To'] = ", ".join(RECIPIENTS)
    
    msg.attach(MIMEText(html_content, 'html'))
    
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        smtp.send_message(msg)

def main():
    # 1. 병렬 크롤링
    all_news = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for kw in KEYWORDS:
            futures.append(executor.submit(fetch_naver_news, kw))
            futures.append(executor.submit(fetch_google_news, kw))
        
        for f in futures:
            all_news.extend(f.result())

    # 2. 중복 제거 (제목 기준)
    df = pd.DataFrame(all_news).drop_duplicates(subset=['title'])
    
    # 3. Gemini 요약 및 선정
    summary_html = get_gemini_summary(df.to_dict('records'))

    # 4. HTML 메일 구성
    email_body = f"""
    <html>
        <body>
            <h2>오늘의 주요 업무 관련 기사 요약</h2>
            <ul>
                {summary_html}
            </ul>
        </body>
    </html>
    """
    
    # 5. 메일 발송
    send_email(email_body)

if __name__ == "__main__":
    main()
