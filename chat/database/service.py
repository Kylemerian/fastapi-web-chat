
from database.crud import *
from fastapi import Depends
from database.db import get_async_session
from sqlalchemy.ext.asyncio import AsyncSession


class UserService:
    async def userGetById(self, uid: int, session: AsyncSession):
        return await userGetById(uid, session)
    
    async def userAdd(self, username: str, hashed_password: str, session: AsyncSession):
        if await userGetByLogin(username, session):
            return -1
        return await userAdd(username, hashed_password, session)
    
    async def userGetAll(self, session: AsyncSession):
        return await userGetAll(session)
    
    def verifyPassword(self, pass1, pass2):
        return verifyPassword(pass1, pass2)
    
    async def userGetByLogin(self, login: str, session: AsyncSession):
        return await userGetByLogin(login, session)
    
    async def userChangeAvatar(self, path: str, uid: int, session: AsyncSession):
        return await userChangeAvatar(path, uid, session)

    async def userGetAvatarById(self, uid: int, session: AsyncSession):
        return await userGetAvatarById(uid, session)


class MessageService:
    async def addMessage(self, chat_id: int, user_id: int, message: str, time: Time, session: AsyncSession):
        return await addMessage(session, chat_id, user_id, message, time)
    
    async def getMessagesByChatId(self, session: AsyncSession, chat_id: int):
        return await getMessagesByChatId(session, chat_id)



class ChatMemberService:
    async def getChatMembersByChatId(self, session: AsyncSession, chat_id: int):
        return await getChatMembersByChatId(session, chat_id)



class ChatService:
    async def getUserChats(self, session: AsyncSession, user_id: int):
        return await getUserChats(session, user_id)
    
    async def addChat(self, session: AsyncSession, user_id: int, user_id2: int):
        return await addChat(session, user_id, user_id2)
    
    async def isExistChatByUserIds(self, session: AsyncSession, user_id:int, user_id2: int):
        return await isExistChatByUserIds(session, user_id, user_id2)

    
msgService = MessageService()
chatService = ChatService()
chatMmbrService = ChatMemberService()
usrService = UserService()