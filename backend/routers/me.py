import uuid

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.auth import get_current_user_id
from backend.db import get_connection
from backend.queries import (
    delete_user_goal,
    get_completed_course_ids,
    get_courses_for_skill,
    get_goal_skills,
    get_user_goal,
    toggle_completed_course,
)
from backend.schemas import CourseOut, GoalOut, PathStep, SkillOut

router = APIRouter(prefix="/me")


class MePathResponse(BaseModel):
    goal: GoalOut
    steps: list[PathStep]
    completed_course_ids: list[str]


class ProgressRequest(BaseModel):
    course_id: uuid.UUID


class ProgressResponse(BaseModel):
    course_id: str
    completed: bool


@router.get("/path", response_model=MePathResponse)
def get_my_path(user_id: str = Depends(get_current_user_id)) -> MePathResponse:
    conn = get_connection()
    try:
        goal = get_user_goal(conn, user_id)
        if goal is None:
            raise HTTPException(status_code=404, detail="no goal set")

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
        completed_course_ids = get_completed_course_ids(conn, user_id)
        return MePathResponse(
            goal=GoalOut(name=goal["name"], slug=goal["slug"]),
            steps=steps,
            completed_course_ids=completed_course_ids,
        )
    finally:
        conn.close()


@router.post("/progress", response_model=ProgressResponse)
def toggle_progress(
    request: ProgressRequest, user_id: str = Depends(get_current_user_id)
) -> ProgressResponse:
    conn = get_connection()
    try:
        try:
            completed = toggle_completed_course(conn, user_id, str(request.course_id))
        except psycopg.errors.ForeignKeyViolation:
            conn.rollback()
            raise HTTPException(status_code=404, detail="course not found")
        return ProgressResponse(course_id=str(request.course_id), completed=completed)
    finally:
        conn.close()


@router.delete("/path", status_code=204)
def clear_my_path(user_id: str = Depends(get_current_user_id)) -> None:
    conn = get_connection()
    try:
        delete_user_goal(conn, user_id)
    finally:
        conn.close()
