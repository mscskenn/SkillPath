from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.db import get_connection
from backend.queries import get_courses_for_skill, get_goal, get_goal_skills

router = APIRouter()


class PathRequest(BaseModel):
    goal_slug: str


class CourseOut(BaseModel):
    id: str
    title: str
    url: str
    difficulty: str | None
    duration_minutes: int | None


class SkillOut(BaseModel):
    name: str
    slug: str


class GoalOut(BaseModel):
    name: str
    slug: str


class PathStep(BaseModel):
    skill: SkillOut
    courses: list[CourseOut]


class PathResponse(BaseModel):
    goal: GoalOut
    steps: list[PathStep]


@router.post("/paths", response_model=PathResponse)
def create_path(request: PathRequest) -> PathResponse:
    conn = get_connection()
    try:
        goal = get_goal(conn, request.goal_slug)
        if goal is None:
            raise HTTPException(status_code=404, detail="goal not found")

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
