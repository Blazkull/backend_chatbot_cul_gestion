import uuid
from datetime import datetime
from typing import List
from pydantic import BaseModel, ConfigDict

class MessageBase(BaseModel):
    role: str
    content: str

class MessageRead(MessageBase):
    id: uuid.UUID
    conversation_id: uuid.UUID
    created_at: datetime
    # model_config = ConfigDict(from_attributes=True)

class ConversationRead(BaseModel):
    id: uuid.UUID
    title: str | None
    created_at: datetime
    updated_at: datetime
    messages: List[MessageRead] = []
    
    # model_config = ConfigDict(from_attributes=True)

class ConversationUpdate(BaseModel):
    title: str | None = None
