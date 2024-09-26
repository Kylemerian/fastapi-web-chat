
from fastapi import APIRouter, Depends, HTTPException
from fastapi import WebSocket, Request
from fastapi.websockets import WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from database.service import *
from sqlalchemy.ext.asyncio import AsyncSession
from database.db import get_async_session
from .connectionManager import manager
import httpx
from database.config import SECRET_HASH, API_BASE_URL
from api.auth import getUserInfoFromJWT
from pydantic import BaseModel


from datetime import datetime
import jwt



router = APIRouter()
templates = Jinja2Templates(directory="resources/templates")


@router.post("/addChat")
async def addChat(
    userName: str,
    user: dict = Depends(getUserInfoFromJWT),
    session: AsyncSession=Depends(get_async_session)
):
    uid = user['uid']
    opp = await usrService.userGetByLogin(userName, session)
    isExistChat = await chatService.isExistChatByUserIds(session, uid, opp['id'])
    if not isExistChat:
        return await chatService.addChat(session, uid, opp['id'])


@router.get("/checkChatMembership")
async def check_chat_membership(chat_id: int, user_id: int, session: AsyncSession = Depends(get_async_session)):
    members = await chatMmbrService.getChatMembersByChatId(session, chat_id)
    if user_id not in [member['user_id'] for member in members]:
        raise HTTPException(status_code=403, detail="Access to chat is denied")
    return {"status": "ok"}


class MessageRequest(BaseModel):
    chat_id: int
    message: str


@router.post("/addMess")
async def addMess(
    request: MessageRequest,
    user: dict = Depends(getUserInfoFromJWT),
    session: AsyncSession = Depends(get_async_session)
):
    user_id = user["uid"]

    members = await chatMmbrService.getChatMembersByChatId(session, request.chat_id)
    if user_id not in [member['user_id'] for member in members]:
        raise HTTPException(status_code=403, detail="You are not a member of this chat")

    time = func.now()
    return await msgService.addMessage(request.chat_id, user_id, request.message, time, session)



@router.get("/getMessages")
async def getMessages(
    chat_id: int,
    user: dict = Depends(getUserInfoFromJWT),
    session: AsyncSession = Depends(get_async_session)
):
    uid = user["uid"]
    members = await chatMmbrService.getChatMembersByChatId(session, chat_id)
    if uid not in [member['user_id'] for member in members]:
        raise HTTPException(status_code=403, detail="Access to chat is denied")
    history = await msgService.getMessagesByChatId(session, chat_id)

    if not isinstance(history, list):
        history = []

    oppuid = (members[0] if members[1] == uid else members[1])['user_id']
    
    return {"history": history, "oppuid": oppuid}



async def verify_jwt(token: str):
    try:
        payload = jwt.decode(token, SECRET_HASH, algorithms=["HS256"])
        return payload.get("userId")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="JWT Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid JWT Token")
    
    

#TODO rewrite httpx to rabbitmq
@router.websocket("/ws")
async def websocket(websocket: WebSocket, session: AsyncSession = Depends(get_async_session)):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            
            if data['type'] == 'auth':
                print(data)
                token = data['cookies']['access_token']
                payload = jwt.decode(token, SECRET_HASH, algorithms=["HS256"])
                uid = payload.get("userId")
                if not uid:
                    await websocket.send_json({"error": "Invalid token"})
                    break
                manager.set_active(websocket, uid)
                await manager.send_uid(uid)
                await websocket.send_json({"message": "Authenticated", "userId": uid})
            
            elif data['type'] == 'message':
                print(f"message in socket {data}")
                token = data.get('cookies', {}).get('access_token')
                payload = jwt.decode(token, SECRET_HASH, algorithms=["HS256"])
                uid = payload.get("userId")
                if not token:
                    await websocket.send_json({"error": "Access token is missing."})
                    return

                chat_id = int(data['chat_id'])
                message = data['text']
                print(f"chat_id = {chat_id, type(chat_id)}, message = {message, type(message)}")

                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            "http://localhost:8000/addMess",
                            json={"chat_id": int(chat_id), "message": message},
                            headers={"Authorization": f"Bearer {token}"},
                            cookies={"access_token": token}
                        )

                    if response.status_code == 200:
                        await manager.send_push(session, {**data, "sender_id": uid})
                    else:
                        await websocket.send_json({
                            "error": "Failed to add message",
                            "details": response.json()
                        })

                except httpx.RequestError as exc:
                    await websocket.send_json({"error": "Request error occurred", "details": str(exc)})

            elif data['type'] == 'addChat':
                token = data['cookies']['access_token']
                user_name = data['nick']
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "http://localhost:8000/addChat",
                        json={"userName": user_name},
                        headers={"Authorization": f"Bearer {token}"},
                        cookies={"access_token": token}
                    )

                if response.status_code == 200:
                    await websocket.send_json({"message": "Chat added successfully"})
                else:
                    await websocket.send_json({
                        "error": "Failed to add chat",
                        "details": response.json()
                    })

            elif data['type'] == 'requestMessages':
                token = data['cookies']['access_token']
                chat_id = data['chat_id']
                

                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"http://localhost:8000/getMessages?chat_id={chat_id}",
                        headers={"Authorization": f"Bearer {token}"},
                        cookies={"access_token": token}
                    )
                
                if response.status_code == 200:
                    messages = response.json()
                    await websocket.send_json({**messages, "type": "requestMessages"})
                else:
                    await websocket.send_json({
                        "error": "Failed to get messages",
                        "details": response.json()
                    })

    except WebSocketDisconnect:
        await manager.disconnect(websocket)