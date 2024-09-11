
from fastapi import APIRouter, Depends, Cookie
from fastapi import WebSocket, Request, Query
from fastapi.websockets import WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from database.crud import *
from sqlalchemy.ext.asyncio import AsyncSession
from database.db import get_async_session
from sqlalchemy import func
import redis
from api.auth import getUserInfoFromJWT
from datetime import datetime
import jwt
# from api.auth import getUserInfoFromJWT

router = APIRouter()
templates = Jinja2Templates(directory="resources/templates")
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)

class ConnectionManager:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        print("to redis remove user = ", user_id)
        redis_client.srem("active_users", user_id)

    async def send_message(self, message: str, user_id: str):
        websocket = self.active_connections.get(user_id)
        if websocket:
            await websocket.send_text(message)
    
    async def send_push(self, session: AsyncSession, data):
        # TODO get receiver_id by chat_id
        receiver_id = 4
        receivers = await getChatMembersByChatId(session, int(data['chat_id']))
        for receiver in receivers:
            receiver_id = receiver['user_id']
            if receiver_id in self.active_connections:
                sock = self.active_connections[receiver_id]
                await sock.send_json(data)
    def set_active(self, websocket: WebSocket, user_id: int):
        self.active_connections[user_id] = websocket
        redis_client.sadd("active_users", user_id)
        print("to redis add user = ", user_id)



manager = ConnectionManager()





@router.websocket("/ws")
async def websocket(websocket: WebSocket, session: AsyncSession=Depends(get_async_session)):
    #
    uid = None
    #     
    print("SOCKET OPENED")

    await manager.connect(websocket)
    print("CONNECTED")
    try:
        while True:
            data = await websocket.receive_json()
            print("data: ", data)
            if data['type'] == 'auth':
                # print(f"get mess: {data}")
                token = data['cookies']['access_token']
                payload = jwt.decode(token, "secret", algorithms=["HS256"])
                username = payload.get("sub")
                uid = payload.get("userId")
                print(token, username, uid)
                manager.set_active(websocket, uid)   
            else:
                now = datetime.fromisoformat(data['date'].replace('Z', '+00:00')).time()
                print(data['chat_id'], uid, data['text'], now)
                messageId = await addMessage(session, int(data['chat_id']), uid, data['text'], now)
                # save mess to DB
                # send mess to receiver if active
                await manager.send_push(session, data)
                # await websocket.send_json(data)
    except WebSocketDisconnect:
        # set last time active
        manager.disconnect(uid)
        print("Disconnected")

