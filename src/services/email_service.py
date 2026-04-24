import asyncio
import smtplib
import ssl
from email.message import EmailMessage

from src.core.config import settings
from src.core.exceptions import BaseAppException
from src.utils.logger import logger


class EmailService:
    def _ensure_configured(self) -> None:
        if not settings.EMAIL_ENABLED:
            raise BaseAppException(
                status_code=503,
                message="Отправка писем отключена",
            )

        required_values = {
            "EMAIL_FROM": settings.EMAIL_FROM,
            "SMTP_HOST": settings.SMTP_HOST,
            "SMTP_PORT": settings.SMTP_PORT,
            "SMTP_USERNAME": settings.SMTP_USERNAME,
            "SMTP_PASSWORD": settings.SMTP_PASSWORD,
        }

        missing = [key for key, value in required_values.items() if not value]
        if missing:
            raise BaseAppException(
                status_code=500,
                message=f"Не настроена отправка email. Отсутствуют параметры: {', '.join(missing)}",
            )

    def _build_message(
        self,
        to_email: str,
        subject: str,
        text_body: str,
        html_body: str | None = None,
    ) -> EmailMessage:
        message = EmailMessage()
        from_name = settings.EMAIL_FROM_NAME.strip() if settings.EMAIL_FROM_NAME else "JobFinder"
        message["From"] = f"{from_name} <{settings.EMAIL_FROM}>"
        message["To"] = to_email
        message["Subject"] = subject

        message.set_content(text_body)

        if html_body:
            message.add_alternative(html_body, subtype="html")

        return message

    def _send_sync(
        self,
        to_email: str,
        subject: str,
        text_body: str,
        html_body: str | None = None,
    ) -> None:
        self._ensure_configured()

        message = self._build_message(
            to_email=to_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )

        context = ssl.create_default_context()

        try:
            if settings.SMTP_USE_SSL:
                with smtplib.SMTP_SSL(
                    host=settings.SMTP_HOST,
                    port=settings.SMTP_PORT,
                    timeout=settings.SMTP_TIMEOUT_SECONDS,
                    context=context,
                ) as server:
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                    server.send_message(message)
            else:
                with smtplib.SMTP(
                    host=settings.SMTP_HOST,
                    port=settings.SMTP_PORT,
                    timeout=settings.SMTP_TIMEOUT_SECONDS,
                ) as server:
                    server.ehlo()

                    if settings.SMTP_USE_TLS:
                        server.starttls(context=context)
                        server.ehlo()

                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                    server.send_message(message)

            logger.info(f"Email sent successfully to {to_email}, subject={subject}")

        except smtplib.SMTPAuthenticationError as e:
            logger.error(
                f"SMTP auth failed for {to_email}: {e}",
                exc_info=True,
            )
            raise BaseAppException(
                status_code=503,
                message="Не удалось авторизоваться на SMTP-сервере",
            )

        except smtplib.SMTPException as e:
            logger.error(
                f"SMTP error while sending email to {to_email}: {e}",
                exc_info=True,
            )
            raise BaseAppException(
                status_code=503,
                message="Не удалось отправить письмо. Попробуйте позже",
            )

        except Exception as e:
            logger.error(
                f"Unexpected email send error for {to_email}: {e}",
                exc_info=True,
            )
            raise BaseAppException(
                status_code=503,
                message="Сервис отправки писем временно недоступен",
            )

    async def send_email(
        self,
        to_email: str,
        subject: str,
        text_body: str,
        html_body: str | None = None,
    ) -> None:
        await asyncio.to_thread(
            self._send_sync,
            to_email,
            subject,
            text_body,
            html_body,
        )

    async def send_signup_code(self, email: str, code: str) -> None:
        subject = "Код подтверждения регистрации JobFinder"

        text_body = (
            f"Ваш код подтверждения: {code}\n\n"
            "Код действует 10 минут.\n"
            "Если вы не запрашивали регистрацию, просто проигнорируйте это письмо."
        )

        html_body = f"""
        <html>
          <body style="margin:0;padding:0;background:#f8fafc;font-family:Arial,sans-serif;color:#0f172a;">
            <div style="max-width:560px;margin:40px auto;padding:32px;background:#ffffff;border-radius:20px;border:1px solid #e2e8f0;">
              <h1 style="margin:0 0 16px;font-size:24px;color:#0a2647;">JobFinder</h1>
              <p style="margin:0 0 16px;font-size:16px;line-height:1.6;">
                Подтвердите регистрацию с помощью кода:
              </p>
              <div style="margin:24px 0;padding:18px 20px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:16px;font-size:32px;font-weight:700;letter-spacing:6px;text-align:center;color:#0a2647;">
                {code}
              </div>
              <p style="margin:0 0 12px;font-size:14px;line-height:1.6;color:#475569;">
                Код действует 10 минут.
              </p>
              <p style="margin:0;font-size:14px;line-height:1.6;color:#64748b;">
                Если вы не запрашивали регистрацию, просто проигнорируйте это письмо.
              </p>
            </div>
          </body>
        </html>
        """

        await self.send_email(
            to_email=email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )

    async def send_password_reset_code(self, email: str, code: str) -> None:
        subject = "Код восстановления пароля JobFinder"

        text_body = (
            f"Ваш код восстановления пароля: {code}\n\n"
            "Код действует 10 минут.\n"
            "Если вы не запрашивали восстановление пароля, просто проигнорируйте это письмо."
        )

        html_body = f"""
        <html>
          <body style="margin:0;padding:0;background:#f8fafc;font-family:Arial,sans-serif;color:#0f172a;">
            <div style="max-width:560px;margin:40px auto;padding:32px;background:#ffffff;border-radius:20px;border:1px solid #e2e8f0;">
              <h1 style="margin:0 0 16px;font-size:24px;color:#0a2647;">JobFinder</h1>
              <p style="margin:0 0 16px;font-size:16px;line-height:1.6;">
                Используйте этот код для восстановления пароля:
              </p>
              <div style="margin:24px 0;padding:18px 20px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:16px;font-size:32px;font-weight:700;letter-spacing:6px;text-align:center;color:#0a2647;">
                {code}
              </div>
              <p style="margin:0 0 12px;font-size:14px;line-height:1.6;color:#475569;">
                Код действует 10 минут.
              </p>
              <p style="margin:0;font-size:14px;line-height:1.6;color:#64748b;">
                Если вы не запрашивали восстановление пароля, просто проигнорируйте это письмо.
              </p>
            </div>
          </body>
        </html>
        """

        await self.send_email(
            to_email=email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )


email_service = EmailService()