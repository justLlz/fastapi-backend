from fastapi import FastAPI, BackgroundTasks, UploadFile, File, Form
from starlette.responses import JSONResponse
from starlette.requests import Request
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import BaseModel, EmailStr
from typing import List


"""
https://sabuhish.github.io/fastapi-mail/getting-started/
"""
conf = ConnectionConfig(
    MAIL_USERNAME="YourUsername",
    MAIL_PASSWORD="strong_password",
    MAIL_FROM="your@email.com",
    MAIL_PORT=587,
    MAIL_SERVER="your mail server",
    MAIL_TLS=True,
    MAIL_SSL=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

message = MessageSchema()

fm = FastMail(conf)

fm.send_message(message)
