import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers.courses import router as courses_router
from backend.routers.me import router as me_router
from backend.routers.paths import router as paths_router

load_dotenv()

app = FastAPI(title="SkillPath API")

cors_origins = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ORIGINS", "http://localhost:3000,http://localhost:3001"
    ).split(",")
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(paths_router)
app.include_router(courses_router)
app.include_router(me_router)
