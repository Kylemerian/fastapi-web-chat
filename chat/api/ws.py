
from fastapi import APIRouter, Depends
from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from database.service import *
from sqlalchemy.ext.asyncio import AsyncSession
from database.db import get_async_session
from .connectionManager import manager
from database.config import SECRET_HASH


from datetime import datetime
import jwt


router = APIRouter()
templates = Jinja2Templates(directory="resources/templates")


@router.websocket("/ws")
async def websocket(websocket: WebSocket, session: AsyncSession=Depends(get_async_session)):
    #
    uid = None
    #
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if data['type'] == 'auth':
                token = data['cookies']['access_token']
                payload = jwt.decode(token, SECRET_HASH, algorithms=["HS256"])
                uid = payload.get("userId")
                manager.set_active(websocket, uid)
                await manager.send_uid(uid)
            
            elif data['type'] == 'message':
                now = datetime.fromisoformat(data['date'].replace('Z', '+00:00')).time()
                # m id need for deleting it
                messageId = await msgService.addMessage(int(data['chat_id']), uid, data['text'], now, session)
                await manager.send_push(session, {**data, 'sender_id': uid})
            
            elif data['type'] == 'requestMessages':
                members = await chatMmbrService.getChatMembersByChatId(session, int(data['chat_id']))
                # broken
                # if uid not in members:
                #     break
                history = await msgService.getMessagesByChatId(session, int(data['chat_id']))
                oppuid = (members[0] if members[1] == uid else members[1])['user_id']
                await manager.send_history(uid, history, oppuid)
                # return messages by chat_id
            elif data['type'] == 'addChat':
                opp = await usrService.userGetByLogin(data['nick'], session)
                isExistChat = await chatService.isExistChatByUserIds(session, uid, opp['id'])
                if not isExistChat:
                    await chatService.addChat(session, uid, opp['id'])
    
    except WebSocketDisconnect:
        # set last time active
        # should sent to every1 usr offline?
        manager.disconnect(uid)

