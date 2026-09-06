from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.auth import get_current_user_id
from backend.db import get_connection
from backend.queries import (
    get_courses_for_skill,
    get_goal,
    get_goal_skills,
    upsert_user_goal,
)
from backend.schemas import CourseOut, GoalOut, PathStep, SkillOut

router = APIRouter()


class PathRequest(BaseModel):
    goal_slug: str


class PathResponse(BaseModel):
    goal: GoalOut
    steps: list[PathStep]


@router.post("/paths", response_model=PathResponse)
def create_path(
    request: PathRequest, user_id: str = Depends(get_current_user_id)
) -> PathResponse:
    conn = get_connection()
    try:
        goal = get_goal(conn, request.goal_slug)
        if goal is None:
            raise HTTPException(status_code=404, detail="goal not found")

        upsert_user_goal(conn, user_id, goal["id"])

        skills = get_goal_skills(conn, goal["id"])
        steps = [
            PathStep(
                skill=SkillOut(name=skill["name"], slug=skill["slug"]),
                courses=[
                    CourseOut(**course)
                    for course in get_courses_for_skill(conn, skill["id"])
                ],
            )
            for skill in skills
        ]
        return PathResponse(
            goal=GoalOut(name=goal["name"], slug=goal["slug"]),
            steps=steps,
        )
    finally:
        conn.close()
