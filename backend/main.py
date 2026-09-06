from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers.courses import router as courses_router
from backend.routers.paths import router as paths_router

app = FastAPI(title="SkillPath API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(paths_router)
app.include_router(courses_router)
