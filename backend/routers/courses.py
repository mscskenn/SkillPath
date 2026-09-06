from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.db import get_connection
from backend.queries import get_course_by_id, list_courses
from backend.schemas import CourseOut, SkillOut

router = APIRouter()


class CourseListItem(CourseOut):
    skills: list[SkillOut]


class CourseListResponse(BaseModel):
    courses: list[CourseListItem]
    total: int


class CourseDetailResponse(CourseOut):
    description: str | None
    source_name: str
    skills: list[SkillOut]


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


@router.get("/courses/{course_id}", response_model=CourseDetailResponse)
def get_course_endpoint(course_id: str) -> CourseDetailResponse:
    conn = get_connection()
    try:
        course = get_course_by_id(conn, course_id)
        if course is None:
            raise HTTPException(status_code=404, detail="course not found")
        return CourseDetailResponse(**course)
    finally:
        conn.close()
