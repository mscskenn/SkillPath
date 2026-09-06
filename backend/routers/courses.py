from fastapi import APIRouter
from pydantic import BaseModel

from backend.db import get_connection
from backend.queries import list_courses
from backend.schemas import CourseOut, SkillOut

router = APIRouter()


class CourseListItem(CourseOut):
    skills: list[SkillOut]


class CourseListResponse(BaseModel):
    courses: list[CourseListItem]
    total: int


@router.get("/courses", response_model=CourseListResponse)
def list_courses_endpoint(
    search: str | None = None,
    skill: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> CourseListResponse:
    conn = get_connection()
    try:
        courses, total = list_courses(conn, search, skill, limit, offset)
        return CourseListResponse(
            courses=[CourseListItem(**course) for course in courses],
            total=total,
        )
    finally:
        conn.close()
