import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from textblob import TextBlob
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.message import Message
from app.schemas.common import APIResponse

router = APIRouter(prefix="/nlp", tags=["NLP Microservices"])

class TextRequest(BaseModel):
    text: str

class ConversationRequest(BaseModel):
    conversation_id: uuid.UUID

@router.post("/sentiment", response_model=APIResponse[dict])
async def analyze_sentiment(data: TextRequest):
    """Analiza la polaridad de un texto dado (Positivo, Negativo o Neutral)."""
    blob = TextBlob(data.text)
    
    # TextBlob works best in English. Since our inputs are mostly Spanish, we can translate it first
    # Or just use the rudimentary approach. For MVP we translate to EN to get better sentiment.
    try:
        if len(data.text) > 3:
            blob = TextBlob(data.text).translate(from_lang="es", to="en")
    except Exception:
        # If translation fails, proceed with the original text
        pass

    score = blob.sentiment.polarity
    
    if score > 0.2:
        label = "positive"
    elif score < -0.2:
        label = "negative"
    else:
        label = "neutral"
        
    return APIResponse(
        success=True,
        data={
            "label": label,
            "score": round(score, 2),
            "confidence": round(abs(score) if score != 0 else 0.5, 2)
        },
        message="Análisis de sentimiento exitoso"
    )

@router.post("/summary", response_model=APIResponse[dict])
async def extract_summary(data: ConversationRequest, db: AsyncSession = Depends(get_db)):
    """(Admin) Genera un resumen y palabras clave a partir del historial de la conversación."""
    result = await db.execute(select(Message).where(Message.conversation_id == data.conversation_id).order_by(Message.created_at.asc()))
    messages = result.scalars().all()
    
    if not messages:
        raise HTTPException(status_code=404, detail="Conversación sin mensajes o no encontrada.")
        
    full_text = " ".join([m.content for m in messages if m.role == "user"])
    
    # Placeholder for more complex NLP extraction. MVP:
    # We will simulate a local extraction for MVP (since huggingface summary model may be heavy)
    blob = TextBlob(full_text)
    
    # Extracts noun phrases as keywords
    try:
        keywords = blob.noun_phrases[:5]
    except Exception:
        keywords = []
        
    return APIResponse(
        success=True,
        data={
            "summary": f"El estudiante interactuó sobre procesos académicos. Longitud: {len(full_text)} caracteres.",
            "keywords": list(set(keywords)) if keywords else ["solicitud", "estudiante"]
        },
        message="Resumen generado"
    )
