from fastapi import FastAPI
from fastapi import FastAPI, Request, Form, Depends

from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.encoders import jsonable_encoder

from pydantic import BaseModel

from database.models import *

from sqlalchemy.ext.asyncio import AsyncSession
from database.db import get_async_session

from database import *


class User(BaseModel):
    login: str
    password: str

def login_form(
    login: str = Form(...),
    password: str = Form(...)
) -> User:
    return User(login=login, password=password)

app = FastAPI()

# templates = Jinja2Templates(directory="templates")
app.mount("/resources/templates", StaticFiles(directory="resources/templates", html=True), name='templates')
app.mount("/resources/images", StaticFiles(directory="resources/images", html=True), name='images')

templates = Jinja2Templates(directory="resources/templates")



@app.post("/login")
async def login(user: User = Depends(login_form), session: AsyncSession=Depends(get_async_session)):
    # res = await userGetById(8, session)
    print(user)
    return {user.login: user.password}



@app.post("/register")
async def register(user: User = Depends(login_form), session: AsyncSession=Depends(get_async_session)):
    print(user)
    res = await userAdd(user.login, user.password, session)
    return res



@app.get("/")
async def root(request: Request):
    # print(templates.get_template())
    return templates.TemplateResponse(request=request, name="index.html")

