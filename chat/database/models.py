from sqlalchemy import select, Column, String, Integer, DateTime, ForeignKey
from .db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    avatar_url = Column(String, nullable=True)

class Chat(Base):
    __tablename__ = "chats"
    id = Column(Integer, primary_key=True, index=True)
    chat_name = Column(String)
    host_id = Column(Integer)
    
    
class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey('chats.id'))
    sender_id = Column(Integer, ForeignKey('users.id'))
    text = Column(String)
    time = Column(DateTime)
    
class ChatMembers(Base):
    __tablename__ = "chatmembers"
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey('chats.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
