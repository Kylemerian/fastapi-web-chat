from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse

from api import auth, ws


app = FastAPI()
app.mount("/resources/templates", StaticFiles(directory="resources/templates", html=True), name='templates')
app.mount("/resources/images", StaticFiles(directory="resources/images", html=True), name='images')
app.mount("/resources/avatars", StaticFiles(directory="resources/avatars", html=True), name='avatars')
app.include_router(auth.router)
app.include_router(ws.router)

templates = Jinja2Templates(directory="resources/templates")

@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return templates.TemplateResponse(request=request, name="error.html")