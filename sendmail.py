import smtplib
from email.mime.text import MIMEText

sender_email = "gomsei@gmail.com"
sender_password = "hyuq azpv tdce tpmu"
receiver_email = "gomsei@yonsei.ac.kr"

msg = MIMEText("SSL 방식으로 보내는 메일입니다.", "plain", "utf-8")
msg['Subject'] = "SSL 테스트"
msg['From'] = sender_email
msg['To'] = receiver_email

# SMTP_SSL을 사용하여 직접 SSL 연결 (포트 465)
try:
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.login(sender_email, sender_password)
    server.sendmail(sender_email, receiver_email, msg.as_string())
    print("✅ SSL 방식 발송 성공!")
except Exception as e:
    print(f"❌ 오류: {e}")
finally:
    server.quit()
