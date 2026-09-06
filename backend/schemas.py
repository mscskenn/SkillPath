from pydantic import BaseModel


class SkillOut(BaseModel):
    name: str
    slug: str


class GoalOut(BaseModel):
    name: str
    slug: str


class CourseOut(BaseModel):
    id: str
    title: str
    url: str
    difficulty: str | None
    duration_minutes: int | None


class PathStep(BaseModel):
    skill: SkillOut
    courses: list[CourseOut]
