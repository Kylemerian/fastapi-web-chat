from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy import func, select, update
from sqlalchemy.sql import and_
from .models import *

async def userAdd(username: str, hashed_password: str, session: AsyncSession):
    user = User(username=username, hashed_password=hashed_password)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user.id


async def userGetAll(session: AsyncSession):
    res = await session.scalars(select(User))
    return res.all()


async def userGetById(id: int, session: AsyncSession):
    res = await session.scalars(select(User).filter_by(User.id == id))
    res = res.scalar_one_or_none()
    return {"username": res.username, "hashed_password": res.hashed_password}

async def userGetByLogin(login: str, session: AsyncSession):
    res = await session.execute(select(User).filter_by(username = login))
    res = res.scalar_one_or_none()
    if res is None:
        return None
    else:
        return {"username": res.username, "hashed_password": res.hashed_password, "id": res.id}

def verifyPassword(passw: str, hashedPass: str):
    return passw == hashedPass


async def addChat(session: AsyncSession, user_id: int, user_id2: int):
    newChat = Chat(chat_name = ".")
    session.add(newChat)
    await session.flush()
    
    chat_members = [ChatMembers(chat_id=newChat.id, user_id=user_id) for user_id in [user_id, user_id2]]
    session.add_all(chat_members)
    await session.commit()
    return newChat.id


async def addMessage(session: AsyncSession, chat_id: int, user_id:int, message: str, time: Time):
    newMessage = Message(chat_id=chat_id, sender_id=user_id, text=message, time=time)
    session.add(newMessage)
    await session.commit()
    await session.refresh(newMessage)
    return newMessage.id


async def getUserChats(session: AsyncSession, user_id: int):
    chat_ids_subquery = (
        select(ChatMembers.chat_id)
        .where(ChatMembers.user_id == user_id)
        .subquery()
    )

    chat_members_subquery = (
        select(ChatMembers.chat_id, ChatMembers.user_id)
        .where(ChatMembers.chat_id.in_(chat_ids_subquery))
        .where(ChatMembers.user_id != user_id)
        .subquery()
    )

    last_message_subquery = (
        select(
            Message.chat_id,
            func.max(Message.time).label('last_message_time')
        )
        .group_by(Message.chat_id)
        .subquery()
    )

    query = (
        select(
            chat_members_subquery.c.chat_id,
            User.avatar_url.label('avatar'),
            User.username.label('participant_name'),
            Message.text.label('last_message_text'),
            last_message_subquery.c.last_message_time
        )
        .select_from(chat_members_subquery)
        .outerjoin(
            last_message_subquery,
            chat_members_subquery.c.chat_id == last_message_subquery.c.chat_id
        )
        .outerjoin(
            Message,
            and_(
                Message.chat_id == chat_members_subquery.c.chat_id,
                Message.time == last_message_subquery.c.last_message_time
            )
        )
        .join(
            User,
            User.id == chat_members_subquery.c.user_id
        )
    )
    
    
    result = await session.execute(query)
    # columns = [column.name for column in query.columns]
    rows = result.fetchall()

    chat_list = [
        {
            'chat_id': row.chat_id,
            'avatar': row.avatar,
            'participant_name': row.participant_name,
            'last_message_text': row.last_message_text,
            'last_message_time': row.last_message_time
        }
        for row in rows
    ]
    # result_dict = [dict(zip(columns, row)) for row in rows]
    # return result_dict 
    return chat_list


async def getMessagesByChatId(session: AsyncSession, chat_id: int):
    
    query = select(Message).where(Message.chat_id == chat_id).order_by(Message.time)
    
    result = await session.execute(query)
    rows = result.fetchall()
    
    message_list = [
        {
            'message_id': row.Message.id,
            'chat_id': row.Message.chat_id,
            'sender_id': row.Message.sender_id,
            'text': row.Message.text,
            'time': row.Message.time.isoformat()
        }
        for row in rows
    ]
    
    return message_list

async def getChatMembersByChatId(session: AsyncSession, chat_id: int):
    query = select(ChatMembers).where(ChatMembers.chat_id == chat_id)
    
    result = await session.execute(query)
    rows = result.fetchall()
    
    user_list = [
        {
            'user_id': row.ChatMembers.user_id
        }
        for row in rows
    ]
    
    return user_list

async def isExistChatByUserIds(session: AsyncSession, user_id:int, user_id2: int):
    member1 = aliased(ChatMembers)
    member2 = aliased(ChatMembers)
    
    # Строим запрос на поиск общего чата
    stmt = (
        select(member1.chat_id)
        .join(member2, member1.chat_id == member2.chat_id)
        .where(member1.user_id == user_id)
        .where(member2.user_id == user_id2)
    )
    
    # Выполняем запрос
    result = await session.execute(stmt)
    chat_id = result.scalar()

    return chat_id is not None


async def userChangeAvatar(path: str, uid: int, session: AsyncSession):
    stmt = (
        update(User)
        .where(User.id == uid)
        .values(avatar_url=path)
        .execution_options(synchronize_session="fetch")
    )
    
    await session.execute(stmt)
    await session.commit()
    
    
async def userGetAvatarById(uid: int, session: AsyncSession):
    stmt = select(User).where(User.id == uid)
    result = await session.execute(stmt)
    
    user = result.scalar_one_or_none()

    if user is None:
        return None

    return user.avatar_url