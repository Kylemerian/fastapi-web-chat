from sqlalchemy import select, Column, String, Integer
from .db import Base
from sqlalchemy.ext.asyncio import AsyncSession


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)


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
    print("LOGIN:", login)
    res = await session.execute(select(User).filter_by(username = login))
    res = res.scalar_one_or_none()
    if res is None:
        return None
    else:
        return {"username": res.username, "hashed_password": res.hashed_password}

def verifyPassword(passw: str, hashedPass: str):
    return passw == hashedPass