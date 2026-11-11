# app/services/notification_service.py

import smtplib
from email.mime.text import MIMEText
from email.header import Header
from typing import Optional
import ssl

from ..core.config import settings

class NotificationService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NotificationService, cls).__new__(cls)
            cls._instance.smtp_host = settings.SMTP_HOST
            cls._instance.smtp_port = settings.SMTP_PORT
            cls._instance.smtp_username = settings.SMTP_USERNAME
            cls._instance.smtp_password = settings.SMTP_PASSWORD
            cls._instance.sender_email = settings.SMTP_SENDER_EMAIL
            # print(f"[NotificationService] Initialized with SMTP Host: {cls._instance.smtp_host}, Port: {cls._instance.smtp_port}") # 移除调试
            # if not cls._instance.smtp_username or not cls._instance.smtp_password:
            #     print("[NotificationService] WARNING: SMTP username or password not configured. Email sending will be skipped.") # 移除调试
        return cls._instance

    def send_email(self, recipient_email: str, subject: str, body: str) -> bool:
        """
        发送邮件。
        Args:
            recipient_email: 收件人邮箱地址。
            subject: 邮件主题。
            body: 邮件正文。
        Returns:
            发送成功返回 True，否则返回 False。
        """
        # print(f"[NotificationService] Attempting to send email to: {recipient_email}") # 移除调试
        # print(f"[NotificationService] Subject: {subject}") # 移除调试

        if not self.smtp_username or not self.smtp_password:
            # print("[NotificationService] SMTP username or password not configured. Skipping email sending.") # 移除调试
            return False

        if not recipient_email:
            # print("[NotificationService] Recipient email is empty. Skipping email sending.") # 移除调试
            return False

        try:
            msg = MIMEText(body, 'plain', 'utf-8')
            msg['From'] = self.sender_email
            msg['To'] = recipient_email
            msg['Subject'] = Header(subject, 'utf-8')

            context = ssl.create_default_context()

            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context) as server:
                # server.set_debuglevel(1) # 移除调试
                server.login(self.smtp_username, self.smtp_password)
                server.sendmail(self.sender_email, recipient_email, msg.as_string())
            # print(f"[NotificationService] Email sent successfully to {recipient_email} for subject: '{subject}'") # 移除调试
            return True
        except smtplib.SMTPAuthenticationError as e:
            print(f"SMTP Authentication Error: Check username and password. Error: {e}") # 保留关键错误日志
            return False
        except smtplib.SMTPException as e:
            print(f"SMTP Error: Failed to send email to {recipient_email}. Error: {e}") # 保留关键错误日志
            return False
        except Exception as e:
            print(f"An unexpected error occurred while sending email to {recipient_email}. Error: {e}") # 保留关键错误日志
            return False

# 创建单例服务实例
notification_service = NotificationService()