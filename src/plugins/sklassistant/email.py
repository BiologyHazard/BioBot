import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Sequence

import aioimaplib
import aiosmtplib
from nonebot import logger
from pydantic import NameEmail

from .config import plugin_config

name_email: NameEmail = plugin_config.skl_name_email
email_password: str = plugin_config.skl_email_password


# def decode_email_str(s: str) -> str:
#     if s.startswith('=?') and s.endswith('?='):
#         try:
#             _, charset, encoding, encoded_str, _ = s.split('?')
#             return base64.b64decode(encoded_str).decode(charset)
#         except Exception:
#             return s
#     return s


async def read_emails():
    imap_client = aioimaplib.IMAP4_SSL("imap.qq.com", 993)
    await imap_client.wait_hello_from_server()
    await imap_client.login(name_email.email, email_password)
    await imap_client.select("INBOX")
    criteria = f'(SUBJECT "token") (UNFLAGGED)'
    status, data = await imap_client.search(criteria)
    mail_ids = data[0].decode().split()
    for mail_id in mail_ids:
        status, data = await imap_client.fetch(mail_id, "(RFC822)")
        email_msg = email.message_from_bytes(data[1])
        print(email_msg["Subject"])
        print(email_msg["From"])
        await imap_client.store(mail_id, "+FLAGS", "\\FLAGGED")

    await imap_client.close()
    await imap_client.logout()


async def send_email(
    recipients: str | Sequence[str], subject: str, content: str
) -> None:
    try:
        email_message = MIMEMultipart()
        email_message.attach(MIMEText(content, "plain", "utf-8"))
        email_message["Subject"] = subject
        email_message["From"] = formataddr((name_email.name, name_email.email))
        async with aiosmtplib.SMTP(
            hostname=plugin_config.skl_email_smtp_host,
            port=plugin_config.skl_email_smtp_port,
            use_tls=True,
        ) as smtp_client:
            await smtp_client.login(name_email.email, email_password)
            await smtp_client.sendmail(
                name_email.email, recipients, email_message.as_string()
            )
    except Exception as e:
        logger.exception(f"邮件 {subject} 发送给 {recipients} 发送失败！")
        raise e
    else:
        logger.success(f"邮件 {subject} 发送给 {recipients} 发送成功！")
