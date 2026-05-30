from enum import Enum


class RoleName(str, Enum):
    APPLICANT = "applicant"
    COMPANY = "company"
    ADMIN = "admin"


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


class ApplicationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class StorageFolder(str, Enum):
    CHATS = "chats"
    COMPANIES = "companies"
    APPLICANTS = "applicants"


class UploadPurpose(str, Enum):
    CHAT_FILE = "chat_file"
    COMPANY_LOGO = "company_logo"
    APPLICANT_PHOTO = "applicant_photo"


class ContentType:
    JPEG = "image/jpeg"
    PNG = "image/png"
    WEBP = "image/webp"
    GIF = "image/gif"

    PDF = "application/pdf"
    TXT = "text/plain"

    DOC = "application/msword"
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    XLS = "application/vnd.ms-excel"
    XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    ZIP = "application/zip"
    ZIP_COMPRESSED = "application/x-zip-compressed"


CHAT_ALLOWED_CONTENT_TYPES: set[str] = {
    ContentType.JPEG,
    ContentType.PNG,
    ContentType.WEBP,
    ContentType.GIF,
    ContentType.PDF,
    ContentType.TXT,
    ContentType.DOC,
    ContentType.DOCX,
    ContentType.XLS,
    ContentType.XLSX,
    ContentType.ZIP,
    ContentType.ZIP_COMPRESSED,
}

PROFILE_IMAGE_ALLOWED_CONTENT_TYPES: set[str] = {
    ContentType.JPEG,
    ContentType.PNG,
    ContentType.WEBP,
}


class FileErrorMessage:
    EMPTY_FILE = "Файл пустой"
    INVALID_FOLDER = "Некорректная папка для файла"
    STORAGE_SAVE_FAILED = "Не удалось сохранить файл в S3"
    INVALID_FILE_TYPE = "Недопустимый тип файла"