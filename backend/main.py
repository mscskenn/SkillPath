from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers.paths import router

app = FastAPI(title="SkillPath API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
