import uuid
import httpx
import json
from datetime import datetime
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation, ConversationStatus
from app.models.message import Message
from app.config import get_settings

settings = get_settings()

async def get_active_conversation(db: AsyncSession, user_id: uuid.UUID) -> Conversation:
    """Busca la conversación activa del usuario o crea una nueva."""
    # Buscar estado 'Abierto' (o crearlo si no existe para evitar errores)
    q_status = select(ConversationStatus).where(ConversationStatus.slug == "open")
    res_status = await db.execute(q_status)
    status_open = res_status.scalar_one_or_none()
    
    if not status_open:
        status_open = ConversationStatus(name="Abierto", slug="open")
        db.add(status_open)
        await db.commit()
        await db.refresh(status_open)

    # Buscar conversación existente
    query = select(Conversation).where(
        Conversation.user_id == user_id,
        Conversation.status_id == status_open.id,
        Conversation.is_deleted == False
    ).options(selectinload(Conversation.messages)).order_by(Conversation.created_at.desc())
    
    result = await db.execute(query)
    conversation = result.scalars().first()
    
    if not conversation:
        conversation = Conversation(
            user_id=user_id,
            status_id=status_open.id,
            title="Nueva consulta",
            last_activity_at=datetime.utcnow()
        )
        conversation.messages = []
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        
    return conversation


async def get_user_conversations(db: AsyncSession, user_id: uuid.UUID, limit: int = 10, offset: int = 0) -> list[Conversation]:
    """Devuelve las conversaciones de un usuario con los mensajes para la previsualización."""
    query = select(Conversation).where(
        Conversation.user_id == user_id,
        Conversation.is_deleted == False
    ).options(selectinload(Conversation.messages)).order_by(Conversation.updated_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all())

async def search_user_conversations(db: AsyncSession, user_id: uuid.UUID, search_query: str) -> list[Conversation]:
    """Busca conversaciones de un usuario por título o por las que contengan un mensaje con el texto buscado."""
    # Usamos distinct para no traer la conversación múltiples veces si varos mensajes coinciden
    query = (
        select(Conversation)
        .outerjoin(Message, Conversation.id == Message.conversation_id)
        .where(
            Conversation.user_id == user_id,
            Conversation.is_deleted == False
        )
        .where(
            (Conversation.title.ilike(f"%{search_query}%")) |
            (Message.content.ilike(f"%{search_query}%"))
        )
        .options(selectinload(Conversation.messages))
        .order_by(Conversation.updated_at.desc())
        .distinct()
        .limit(20) # Limit search results
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_conversation_by_id(db: AsyncSession, conversation_id: uuid.UUID, user_id: uuid.UUID) -> Conversation | None:
    """Busca una conversación específica de un usuario."""
    query = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.user_id == user_id,
        Conversation.is_deleted == False
    ).options(selectinload(Conversation.messages))
    result = await db.execute(query)
    return result.scalars().first()

async def update_conversation(db: AsyncSession, conversation_id: uuid.UUID, user_id: uuid.UUID, title: str) -> Conversation | None:
    """Actualiza el título de una conversación."""
    conv = await get_conversation_by_id(db, conversation_id, user_id)
    if conv and title:
        conv.title = title
        await db.commit()
        await db.refresh(conv)
    return conv




async def save_message(db: AsyncSession, conversation_id: uuid.UUID, role: str, content: str) -> Message:
    """Guarda un mensaje en la base de datos."""
    from textblob import TextBlob
    
    sentiment_score = None
    sentiment_label = None
    
    # Calculate sentiment only for user messages
    if role == "user":
        try:
            # Simple textblob sentiment analysis
            blob = TextBlob(content)
            # Polarity is between -1.0 (negative) and 1.0 (positive)
            sentiment_score = blob.sentiment.polarity
            
            if sentiment_score > 0.2:
                sentiment_label = "Positivo"
            elif sentiment_score < -0.2:
                sentiment_label = "Negativo"
            else:
                sentiment_label = "Neutral"
        except Exception as e:
            print(f"Error calculating sentiment: {e}")
            pass

    msg = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        sentiment_score=sentiment_score,
        sentiment=sentiment_label
    )
    db.add(msg)
    
    # Update conversation's updated_at timestamp
    query = select(Conversation).where(Conversation.id == conversation_id)
    result = await db.execute(query)
    conv = result.scalar_one_or_none()
    if conv:
        conv.updated_at = datetime.utcnow()
        # Update conversation average sentiment
        if role == "user" and sentiment_score is not None:
            if conv.sentiment_score is None:
                conv.sentiment_score = sentiment_score
            else:
                # Running average of sentiment
                conv.sentiment_score = (conv.sentiment_score + sentiment_score) / 2
                
            if conv.sentiment_score > 0.2:
                conv.sentiment_label = "Positivo"
            elif conv.sentiment_score < -0.2:
                conv.sentiment_label = "Negativo"
            else:
                conv.sentiment_label = "Neutral"
                
    await db.commit()
    await db.refresh(msg)
    return msg

async def get_conversation_messages(db: AsyncSession, conversation_id: uuid.UUID) -> list[Message]:
    """Recupera los mensajes de una conversación de forma explícita para evitar Deadlocks de SQLAlchemy."""
    query = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.asc())
    result = await db.execute(query)
    messages = result.scalars().all()
    return list(messages)

async def close_active_conversation(db: AsyncSession, user_id: uuid.UUID) -> bool:
    """Cierra la conversación activa del usuario cambiándole el estado a 'cerrado'."""
    # Buscar estado 'Cerrado'
    q_status_closed = select(ConversationStatus).where(ConversationStatus.slug == "closed")
    res_status = await db.execute(q_status_closed)
    status_closed = res_status.scalar_one_or_none()
    
    if not status_closed:
        status_closed = ConversationStatus(name="Cerrado", slug="closed")
        db.add(status_closed)
        await db.commit()
        await db.refresh(status_closed)

    # Buscar estado 'Abierto'
    q_status_open = select(ConversationStatus).where(ConversationStatus.slug == "open")
    res_open = await db.execute(q_status_open)
    status_open = res_open.scalar_one_or_none()

    if status_open:
        # Actualizar todas las conversaciones abiertas del usuario a cerradas
        query = select(Conversation).where(
            Conversation.user_id == user_id,
            Conversation.status_id == status_open.id,
            Conversation.is_deleted == False
        )
        result = await db.execute(query)
        conversations = result.scalars().all()
        
        for conv in conversations:
            conv.status_id = status_closed.id
            conv.updated_at = datetime.utcnow()
            
        if conversations:
            await db.commit()
            return True
            
    return False


async def stream_hf_response(user_input: str) -> AsyncGenerator[str, None]:
    """Llama a la API de Hugging Face en modo stream y obliga el idioma español."""
    
    SYS_TAG = "<|system|>"
    USR_TAG = "<|user|>"
    AST_TAG = "<|assistant|>"
    EOS_TAG = "</s>"

    SYSTEM_PROMPT = (
        "Eres el Asistente Virtual de Gestión Académica de la Corporación Universitaria "
        "Latinoamericana (CUL), ubicada en Barranquilla, Colombia. Tu misión es guiar a "
        "los estudiantes en procesos académicos de forma concisa y directa.\n\n"
        "REGLAS ESTRÍCTAS E INQUEBRANTABLES:\n"
        "1. RESPONDE SIEMPRE EN UN SOLO PÁRRAFO.\n"
        "2. NO uses viñetas, listas, negritas, ni formato markdown de ningún tipo.\n"
        "3. NO uses caracteres especiales extraños ni repitas símbolos.\n"
        "4. Responde ÚNICA Y EXCLUSIVAMENTE en idioma ESPAÑOL.\n"
        "5. Ve directo al grano, sin saludos excesivos ni formalidades innecesarias."
    )

    formatted_prompt = (
        f"{SYS_TAG}\n{SYSTEM_PROMPT}{EOS_TAG}\n"
        f"{USR_TAG}\n{user_input}{EOS_TAG}\n"
        f"{AST_TAG}\n"
    )
    
    payload = {
        "inputs": formatted_prompt,
        "max_new_tokens": 200,
        "temperature": 0.6,
        "top_p": 0.9,
        "do_sample": True
    }
    
    headers = {"Content-Type": "application/json"}
    
    async with httpx.AsyncClient() as client:
        try:
            async with client.stream("POST", settings.HF_SPACE_API_URL, json=payload, headers=headers, timeout=300.0) as response:
                response.raise_for_status()
                async for chunk in response.aiter_text():
                    if chunk:
                        yield chunk
        except Exception as e:
            yield f"\n[Error de conexión con IA: {str(e)}]"
async def delete_conversation(db: AsyncSession, conversation_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    """Realiza un soft-delete de una conversación."""
    conv = await get_conversation_by_id(db, conversation_id, user_id)
    if conv:
        conv.is_deleted = True
        conv.deleted_at = datetime.utcnow()
        await db.commit()
        return True
    return False
