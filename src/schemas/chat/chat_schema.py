from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ChatAttachmentResponse(BaseModel):
    id: int
    file_url: str
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatMessageSenderResponse(BaseModel):
    id: int
    email: str
    is_online: bool
    last_seen_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChatMessageCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)


class ChatMessageResponse(BaseModel):
    id: int
    chat_id: int
    sender_id: int
    text: Optional[str] = None
    created_at: datetime
    sender: Optional[ChatMessageSenderResponse] = None
    attachments: list[ChatAttachmentResponse] = []

    class Config:
        from_attributes = True


class ChatApplicationInfo(BaseModel):
    id: int
    vacancy_id: int
    resume_id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatListItemResponse(BaseModel):
    id: int
    application_id: int
    created_at: datetime

    application: Optional[ChatApplicationInfo] = None
    last_message: Optional[ChatMessageResponse] = None
    unread_count: int = 0

    class Config:
        from_attributes = True


class ChatDetailResponse(BaseModel):
    id: int
    application_id: int
    created_at: datetime

    application: Optional[ChatApplicationInfo] = None
    messages: list[ChatMessageResponse] = []

    class Config:
        from_attributes = True
        
class ChatReadResponse(BaseModel):
    chat_id: int
    read_messages_count: int
    read_at: datetime