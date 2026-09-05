from fastapi import FastAPI

from backend.routers.paths import router

app = FastAPI(title="SkillPath API")
app.include_router(router)
