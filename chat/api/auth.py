from pydantic import BaseModel
from fastapi import Form, Depends, HTTPException, APIRouter, status, Request, UploadFile, File
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi.templating import Jinja2Templates
import shutil
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from database.db import get_async_session

import jwt
import datetime
from database.config import SECRET_HASH

from database.service import *

router = APIRouter()


class User(BaseModel):
    login: str
    password: str

def login_form(
    login: str = Form(...),
    password: str = Form(...)
) -> User:
    return User(login=login, password=password)


templates = Jinja2Templates(directory="resources/templates")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def getUserInfoFromJWT(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No access token found",
        )

    try:
        # remove secret
        payload = jwt.decode(token, SECRET_HASH, algorithms=["HS256"])
        username: str = payload.get("sub")
        uid: int = payload.get("userId")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
        return {'username': username, 'uid': uid}
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


@router.post("/login")
async def login(
    user: User = Depends(login_form),
    session: AsyncSession=Depends(get_async_session)
):
    usr = await usrService.userGetByLogin(user.login, session)
    if not usr or not usrService.verifyPassword(user.password, usr['hashed_password']):
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    token = jwt.encode({"sub": user.login, "userId": usr['id'], "exp": datetime.datetime.now() + datetime.timedelta(minutes=1440)}, SECRET_HASH, algorithm="HS256")
    response = RedirectResponse(url="/chat", status_code=302)
    response.set_cookie(
        key="access_token", 
        value=token, 
        # httponly=True,
        httponly=False,
        max_age=1440 * 60,
        expires=1440 * 60, 
        # secure=True,
        samesite="lax"
    )
    return response


IMAGE_DIR = Path("resources/avatars/")

async def save_file(file: UploadFile, uid: int) -> str:
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    file_extension = file.filename.split(".")[-1]
    file_name = f"{uid}.{file_extension}"
    file_path = IMAGE_DIR / file_name

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return str(file_path)


@router.post("/setAvatar")
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    session: AsyncSession=Depends(get_async_session)
):
    data = getUserInfoFromJWT(request)
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Invalid file format. Only JPEG and PNG are allowed.")
    
    file_path = await save_file(file, data['uid'])
    await usrService.userChangeAvatar(file_path, data['uid'], session)
    return {"filename": file.filename, "filepath": file_path}


@router.post("/register")
async def register(
    user: User = Depends(login_form),
    session: AsyncSession=Depends(get_async_session)
):
    res = await usrService.userAdd(user.login, user.password, session)
    return RedirectResponse(url="/", status_code=302)



@router.get("/chat")
async def chat(
    request: Request,
    session: AsyncSession=Depends(get_async_session)
):
    data = getUserInfoFromJWT(request)
    avatar = await usrService.userGetAvatarById(data['uid'], session)
    chats = await chatService.getUserChats(session, data['uid'])
    messages = []
    return templates.TemplateResponse("chat.html", {"request": request, **data, "chats": chats, "messages": messages, "avatar": avatar})



@router.get("/chat2")
async def chat2(request: Request, session: AsyncSession=Depends(get_async_session)):
    data = getUserInfoFromJWT(request)
    return await getUserChats(session, data['uid'])


# to rework
# @router.post("/addChat")
# async def addChat(user: int, user2: int, session: AsyncSession=Depends(get_async_session)):
#     return await chatService.addChat(session, user, user2)


# @router.post("/addMess")
# async def addMessage(chat_id: int, user_id:int, message: str, session: AsyncSession=Depends(get_async_session)):
#     time = func.now()
#     return await msgService.addMessage(chat_id, user_id, message, time, session)