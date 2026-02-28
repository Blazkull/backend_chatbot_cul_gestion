import uuid
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from app.db.session import async_session, get_db
from app.config import get_settings
from app.services.auth_service import get_user_by_id
from app.services.chat_service import get_active_conversation, save_message, stream_hf_response, get_conversation_messages, close_active_conversation, update_conversation
from app.schemas.chat import ConversationRead, ConversationUpdate
from app.schemas.common import APIResponse
from app.dependencies.auth import get_current_user
from datetime import datetime

settings = get_settings()
router = APIRouter(prefix="/chat", tags=["Chat & WebSocket"])


async def get_ws_current_user(token: str, db: AsyncSession):
    """Extrae el usuario del token JWT pasado por WebSocket."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            return None
        user = await get_user_by_id(db, uuid.UUID(user_id))
        return user
    except JWTError:
        return None


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    """
    Endpoint WebSocket para el chat en tiempo real.
    El frontend debe enviar el JWT token en la query: ws://.../ws?token=EL_TOKEN
    """
    await websocket.accept()
    
    # Manejar sesión DB para WebSockets manualmente ya que Depends()
    # funciona distinto en el ciclo de vida del socket.
    async with async_session() as db:
        user = await get_ws_current_user(token, db)
        if not user:
            await websocket.send_json({"error": "Authentication failed o token inválido."})
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # Busca su conversación activa
        conversation = await get_active_conversation(db, user.id)
        
        try:
            while True:
                # 1. Recibir mensaje del usuario
                raw_data = await websocket.receive_text()
                try:
                    data_json = json.loads(raw_data)
                    user_message = data_json.get("content", raw_data)
                except json.JSONDecodeError:
                    user_message = raw_data
                
                # Obtener conversation_id si fue proveído, sino usar la actual
                target_conv_id_str = data_json.get("conversation_id") if isinstance(data_json, dict) else None
                if target_conv_id_str:
                    try:
                        target_conv_id = uuid.UUID(target_conv_id_str)
                        if conversation.id != target_conv_id:
                            # User switched active conversation mid-socket
                            from app.services.chat_service import get_conversation_by_id
                            new_conv = await get_conversation_by_id(db, target_conv_id, user.id)
                            if new_conv:
                                conversation = new_conv
                    except ValueError:
                        pass
                
                # 2. Guardar mensaje de usuario en BD
                await save_message(db, conversation.id, "user", user_message)
                
                # 2.5 Actualizar título si es una conversación nueva
                if conversation.title == "Nueva consulta":
                    # Usar hasta las primeras 250 letras del mensaje del usuario como título
                    new_title = user_message[:250] + ("..." if len(user_message) > 250 else "")
                    conversation.title = new_title
                    conversation.updated_at = datetime.utcnow()
                    await db.commit()
                    # Notificar al frontend del cambio de título
                    await websocket.send_json({
                        "type": "title_update",
                        "title": new_title
                    })
                
                # 3. Transmitir respuesta de la IA en streaming
                full_response = ""
                async for chunk in stream_hf_response(user_message):
                    if chunk:
                        full_response += chunk
                        # Mandar chunk como JSON para que el frontend lo procese correctamente como stream
                        await websocket.send_json({
                            "type": "content",
                            "content": chunk
                        })
                
                # 4. Guardar respuesta de la IA en BD
                saved_msg = await save_message(db, conversation.id, "assistant", full_response)
                
                # 5. Enviar la respuesta completa
                await websocket.send_json({
                    "type": "assistant",
                    "conversation_id": str(conversation.id),
                    "content": full_response,
                    "id": str(saved_msg.id),
                    "timestamp": saved_msg.created_at.isoformat()
                })

                # 6. Notificar fin de stream visual
                await websocket.send_json({
                    "type": "done",
                    "conversation_id": str(conversation.id)
                })

        except WebSocketDisconnect:
            print(f"[{user.email}] WebSocket Desconectado.")


@router.get("/history", response_model=APIResponse[list[ConversationRead]])
async def get_chat_history(
    limit: int = Query(10, ge=1, le=100, description="Cantidad de conversaciones a devolver"),
    offset: int = Query(0, ge=0, description="Cantidad de conversaciones a saltar"),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    print(f"[DEBUG_MARKER] Entering get_chat_history for user {current_user.id}")
    """Devuelve el historial de todas las conversaciones del usuario."""
    try:
        from app.services.chat_service import get_user_conversations
        conversations = await get_user_conversations(db, current_user.id, limit=limit, offset=offset)
        
        from app.schemas.chat import MessageRead
        
        result_data = []
        for conv in conversations:
            messages_data = sorted([
                MessageRead(
                    id=m.id,
                    conversation_id=m.conversation_id,
                    role=m.role,
                    content=m.content,
                    created_at=m.created_at
                ) for m in conv.messages
            ], key=lambda x: x.created_at)
            
            result_data.append(ConversationRead(
                id=conv.id,
                title=conv.title,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                messages=messages_data
            ))

        return APIResponse(
            success=True,
            data=result_data,
            message="Historial recuperado exitosamente."
        )
    except Exception as e:
        print(f"[DEBUG_MARKER] Error in get_chat_history: {e}")
        return APIResponse(success=False, message=f"Error al recuperar historial: {str(e)}")

@router.get("/search", response_model=APIResponse[list[ConversationRead]])
async def search_chat_history(
    q: str = Query(..., min_length=1, description="Texto a buscar en titulo o mensajes"),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Busca en el historial de todas las conversaciones del usuario por título o contenido."""
    try:
        from app.services.chat_service import search_user_conversations
        from app.schemas.chat import MessageRead
        
        conversations = await search_user_conversations(db, current_user.id, q)
        
        result_data = []
        for conv in conversations:
            messages_data = sorted([
                MessageRead(
                    id=m.id,
                    conversation_id=m.conversation_id,
                    role=m.role,
                    content=m.content,
                    created_at=m.created_at
                ) for m in conv.messages
            ], key=lambda x: x.created_at)
            
            result_data.append(ConversationRead(
                id=conv.id,
                title=conv.title,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                messages=messages_data
            ))

        return APIResponse(
            success=True,
            data=result_data,
            message="Búsqueda completada."
        )
    except Exception as e:
        print(f"[DEBUG_MARKER] Error in search_chat_history: {e}")
        return APIResponse(success=False, message=f"Error en la búsqueda: {str(e)}")


@router.post("/new", response_model=APIResponse[ConversationRead])
async def create_new_conversation(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cierra la conversación activa actual y crea una nueva."""
    try:
        # Cerrar la actual
        await close_active_conversation(db, current_user.id)
        
        # Obtener inmediatamente una nueva (get_active_conversation la crea si no hay open)
        conversation = await get_active_conversation(db, current_user.id)
        
        history_data = ConversationRead(
            id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            messages=[]
        )

        return APIResponse(
            success=True,
            data=history_data,
            message="Nueva conversación creada exitosamente."
        )
    except Exception as e:
        import traceback
        print(f"[REALLY_DEBUG] Error en new conversation: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversation/{conversation_id}", response_model=APIResponse[ConversationRead])
async def get_conversation(
    conversation_id: uuid.UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Devuelve el detalle de una conversación específica incluyendo los mensajes."""
    try:
        from app.services.chat_service import get_conversation_by_id
        from app.schemas.chat import MessageRead
        
        # Permitir que el usuario solo vea sus propias conversaciones
        conv = await get_conversation_by_id(db, conversation_id, current_user.id)
        if not conv:
            return APIResponse(success=False, message="Conversación no encontrada.")
            
        messages_data = sorted([
            MessageRead(
                id=m.id,
                conversation_id=m.conversation_id,
                role=m.role,
                content=m.content,
                created_at=m.created_at
            ) for m in conv.messages
        ], key=lambda x: x.created_at)
        
        result_data = ConversationRead(
            id=conv.id,
            title=conv.title,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            messages=messages_data
        )

        return APIResponse(
            success=True,
            data=result_data,
            message="Conversación recuperada exitosamente."
        )
    except Exception as e:
        print(f"Error en get_conversation: {e}")
        return APIResponse(success=False, message=f"Error obteniendo conversación: {str(e)}")

@router.put("/conversation/{conversation_id}", response_model=APIResponse[ConversationRead])
async def update_conversation_title_route(
    conversation_id: uuid.UUID,
    data: ConversationUpdate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Actualiza el título de una conversación."""
    try:
        from app.services.chat_service import update_conversation
        from app.schemas.chat import MessageRead
        
        conv = await update_conversation(db, conversation_id, current_user.id, data.title)
        if not conv:
            return APIResponse(success=False, message="Conversación no encontrada.")
            
        messages_data = sorted([
            MessageRead(
                id=m.id,
                conversation_id=m.conversation_id,
                role=m.role,
                content=m.content,
                created_at=m.created_at
            ) for m in conv.messages
        ], key=lambda x: x.created_at)
        
        result_data = ConversationRead(
            id=conv.id,
            title=conv.title,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            messages=messages_data
        )

        return APIResponse(
            success=True,
            data=result_data,
            message="Conversación actualizada exitosamente."
        )
    except Exception as e:
        print(f"Error en update_conversation_title_route: {e}")
        return APIResponse(success=False, message=f"Error actualizando conversación: {str(e)}")


@router.get("/user/{user_id}/conversations", response_model=APIResponse[list[ConversationRead]])
async def get_user_chat_history_admin(
    user_id: uuid.UUID,
    limit: int = Query(10, ge=1, le=100, description="Cantidad de conversaciones a devolver"),
    offset: int = Query(0, ge=0, description="Cantidad de conversaciones a saltar"),
    db: AsyncSession = Depends(get_db)
    # TODO: Podríamos agregar Dependency para verificar rol Admin si es otro usuario
):
    """Devuelve el historial de todas las conversaciones de un ID de usuario en particular (Ideal para Metrics o Admins)."""
    try:
        from app.services.chat_service import get_user_conversations
        conversations = await get_user_conversations(db, user_id, limit=limit, offset=offset)
        
        from app.schemas.chat import MessageRead
        
        result_data = []
        for conv in conversations:
            messages_data = sorted([
                MessageRead(
                    id=m.id,
                    conversation_id=m.conversation_id,
                    role=m.role,
                    content=m.content,
                    created_at=m.created_at
                ) for m in conv.messages
            ], key=lambda x: x.created_at)
            
            result_data.append(ConversationRead(
                id=conv.id,
                title=conv.title,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                messages=messages_data
            ))

        return APIResponse(
            success=True,
            data=result_data,
            message="Historial recuperado exitosamente."
        )
    except Exception as e:
        return APIResponse(success=False, message=f"Error al recuperar historial: {str(e)}")
@router.delete("/conversation/{conversation_id}", response_model=APIResponse[bool])
async def delete_conversation_route(
    conversation_id: uuid.UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Realiza un soft-delete de una conversación."""
    from app.services.chat_service import delete_conversation
    success = await delete_conversation(db, conversation_id, current_user.id)
    if not success:
        return APIResponse(success=False, message="Conversación no encontrada o ya eliminada.")
    
    return APIResponse(
        success=True,
        data=True,
        message="Conversación eliminada exitosamente."
    )
