from fastapi import FastAPI, Request, Form, Depends, HTTPException, status, WebSocket
from fastapi.websockets import WebSocketDisconnect
# from typing_extensions import Annotated
# from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse

from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pydantic import BaseModel

from database.models import *

from sqlalchemy.ext.asyncio import AsyncSession
from database.db import get_async_session

from database import *

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
import datetime


class User(BaseModel):
    login: str
    password: str

def login_form(
    login: str = Form(...),
    password: str = Form(...)
) -> User:
    return User(login=login, password=password)

app = FastAPI()


app.mount("/resources/templates", StaticFiles(directory="resources/templates", html=True), name='templates')
app.mount("/resources/images", StaticFiles(directory="resources/images", html=True), name='images')

templates = Jinja2Templates(directory="resources/templates")



oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.post("/login")
async def login(user: User = Depends(login_form), session: AsyncSession=Depends(get_async_session)):
    usr = await userGetByLogin(user.login, session)
    if not usr or not verifyPassword(user.password, usr['hashed_password']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # remove secret
    token = jwt.encode({"sub": user.login, "exp": datetime.datetime.now() + datetime.timedelta(minutes=5)}, "secret", algorithm="HS256")

    response = RedirectResponse(url="/chat", status_code=302)
    response.set_cookie(
        key="access_token", 
        value=token, 
        httponly=True,
        max_age=30 * 60,
        expires=30 * 60, 
        # secure=True,
        samesite="lax"
    )
    return response


@app.post("/register")
async def register(user: User = Depends(login_form), session: AsyncSession=Depends(get_async_session)):
    print(user)
    res = await userAdd(user.login, user.password, session)
    return res


@app.get("/chat")
async def chat(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No access token found",
        )

    try:
        # remove secret
        payload = jwt.decode(token, "secret", algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
        data = {
            "username": username
        }
        return templates.TemplateResponse("chat.html", {"request": request, **data})
    
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

@app.websocket("/ws")
async def websocket(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_text()
            print(f"get mess: {data}")

            await websocket.send_text(f"to send: {data}")
    except WebSocketDisconnect:
        print("Disconnected")


@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

