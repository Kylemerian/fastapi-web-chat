from fastapi import WebSocket
import redis
from sqlalchemy.ext.asyncio import AsyncSession
from database.service import *

# for local test
# redis_client = redis.StrictRedis(host='localhost', port=6380, db=0, decode_responses=True)
redis_client = redis.StrictRedis(host='redis', port=6379, db=0, decode_responses=True)

class ConnectionManager:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()

    async def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        # print("to redis remove user = ", user_id)
        redis_client.srem("active_users", user_id)

    async def send_history(self, uid, history, oppuid):
        websocket = self.active_connections.get(uid)
        if websocket:
            await websocket.send_json({'type': 'requestMessages', 'history': history, 'online': oppuid in self.active_connections.keys()})
    
    async def send_uid(self, uid):
        websocket = self.active_connections.get(uid)
        if websocket:
            await websocket.send_json({'type': 'uidInfo', 'uid': uid})
    
    async def send_push(self, session: AsyncSession, data):
        receivers = await chatMmbrService.getChatMembersByChatId(session, int(data['chat_id']))
        for receiver in receivers:
            receiver_id = receiver['user_id']
            print("receiver:", receiver_id, " message:", data)
            if receiver_id in self.active_connections:
                sock = self.active_connections[receiver_id]
                await sock.send_json(data)
    
    def set_active(self, websocket: WebSocket, user_id: int):
        self.active_connections[user_id] = websocket
        redis_client.sadd("active_users", user_id)
        # print("to redis add user = ", user_id)


manager = ConnectionManager()