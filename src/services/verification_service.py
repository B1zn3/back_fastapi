import hashlib
import hmac
import secrets
from datetime import datetime, timezone

from src.core.config import settings
from src.core.exceptions import BaseAppException
from src.redis.verification_store import verification_store


class VerificationService:
    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()

    @staticmethod
    def _generate_code(length: int = 6) -> str:
        return ''.join(str(secrets.randbelow(10)) for _ in range(length))

    @staticmethod
    def _hash_code(code: str) -> str:
        return hashlib.sha256(code.encode('utf-8')).hexdigest()

    @staticmethod
    def _build_code_payload(code: str) -> dict:
        return {
            'code_hash': VerificationService._hash_code(code),
            'attempts_left': settings.OTP_MAX_ATTEMPTS,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }

    async def create_signup_verification(self, email: str, pending_data: dict) -> str:
        normalized_email = self._normalize_email(email)
        code = self._generate_code(settings.OTP_CODE_LENGTH)

        await verification_store.set_signup_pending(
            normalized_email,
            pending_data,
            settings.PENDING_REGISTRATION_TTL_SECONDS,
        )
        await verification_store.set_signup_code(
            normalized_email,
            self._build_code_payload(code),
            settings.OTP_TTL_SECONDS,
        )
        return code

    async def verify_signup_code(self, email: str, code: str) -> dict:
        normalized_email = self._normalize_email(email)
        normalized_code = code.strip()

        pending = await verification_store.get_signup_pending(normalized_email)
        if not pending:
            raise BaseAppException(status_code=404, message='Регистрация не найдена или истекла')

        code_data = await verification_store.get_signup_code(normalized_email)
        if not code_data:
            raise BaseAppException(status_code=400, message='Код подтверждения истёк')

        attempts_left = int(code_data.get('attempts_left', 0))
        stored_hash = str(code_data.get('code_hash', ''))

        if attempts_left <= 0:
            await verification_store.delete_signup_state(normalized_email)
            raise BaseAppException(status_code=400, message='Превышено число попыток. Начните регистрацию заново')

        incoming_hash = self._hash_code(normalized_code)
        if not hmac.compare_digest(incoming_hash, stored_hash):
            attempts_left -= 1

            if attempts_left <= 0:
                await verification_store.delete_signup_state(normalized_email)
                raise BaseAppException(status_code=400, message='Превышено число попыток. Начните регистрацию заново')

            code_data['attempts_left'] = attempts_left
            await verification_store.set_signup_code(
                normalized_email,
                code_data,
                settings.OTP_TTL_SECONDS,
            )
            raise BaseAppException(
                status_code=400,
                message=f'Неверный код. Осталось попыток: {attempts_left}',
            )

        return pending

    async def clear_signup_state(self, email: str) -> None:
        normalized_email = self._normalize_email(email)
        await verification_store.delete_signup_state(normalized_email)

    async def create_password_reset_verification(self, email: str) -> str:
        normalized_email = self._normalize_email(email)
        code = self._generate_code(settings.OTP_CODE_LENGTH)

        await verification_store.set_password_reset_code(
            normalized_email,
            self._build_code_payload(code),
            settings.OTP_TTL_SECONDS,
        )

        return code

    async def verify_password_reset_code(self, email: str, code: str) -> None:
        normalized_email = self._normalize_email(email)
        normalized_code = code.strip()

        code_data = await verification_store.get_password_reset_code(normalized_email)
        if not code_data:
            raise BaseAppException(status_code=400, message='Код подтверждения истёк')

        attempts_left = int(code_data.get('attempts_left', 0))
        stored_hash = str(code_data.get('code_hash', ''))

        if attempts_left <= 0:
            await verification_store.delete_password_reset_state(normalized_email)
            raise BaseAppException(status_code=400, message='Превышено число попыток. Запросите код заново')

        incoming_hash = self._hash_code(normalized_code)

        if not hmac.compare_digest(incoming_hash, stored_hash):
            attempts_left -= 1

            if attempts_left <= 0:
                await verification_store.delete_password_reset_state(normalized_email)
                raise BaseAppException(status_code=400, message='Превышено число попыток. Запросите код заново')

            code_data['attempts_left'] = attempts_left
            await verification_store.set_password_reset_code(
                normalized_email,
                code_data,
                settings.OTP_TTL_SECONDS,
            )

            raise BaseAppException(
                status_code=400,
                message=f'Неверный код. Осталось попыток: {attempts_left}',
            )

    async def clear_password_reset_state(self, email: str) -> None:
        normalized_email = self._normalize_email(email)
        await verification_store.delete_password_reset_state(normalized_email)


verification_service = VerificationService()