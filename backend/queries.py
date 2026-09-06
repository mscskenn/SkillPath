import psycopg


def get_goal(conn: psycopg.Connection, slug: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute("SELECT id, name, slug FROM goals WHERE slug = %s", (slug,))
        row = cur.fetchone()
        if not row:
            return None
        return {"id": str(row[0]), "name": row[1], "slug": row[2]}


def get_goal_skills(conn: psycopg.Connection, goal_id: str) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT sk.id, sk.name, sk.slug
            FROM goal_skills gs
            JOIN skills sk ON sk.id = gs.skill_id
            WHERE gs.goal_id = %s
            ORDER BY gs.step_order
            """,
            (goal_id,),
        )
        return [{"id": str(r[0]), "name": r[1], "slug": r[2]} for r in cur.fetchall()]


def get_courses_for_skill(conn: psycopg.Connection, skill_id: str) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.id, c.title, c.url, c.difficulty, c.duration_minutes
            FROM courses c
            JOIN course_skills cs ON cs.course_id = c.id
            WHERE cs.skill_id = %s
            ORDER BY
              CASE c.difficulty
                WHEN 'beginner' THEN 0
                WHEN 'intermediate' THEN 1
                WHEN 'advanced' THEN 2
                ELSE 3
              END,
              cs.relevance_score DESC,
              c.duration_minutes ASC
            """,
            (skill_id,),
        )
        return [
            {
                "id": str(r[0]),
                "title": r[1],
                "url": r[2],
                "difficulty": r[3],
                "duration_minutes": r[4],
            }
            for r in cur.fetchall()
        ]


def list_courses(
    conn: psycopg.Connection,
    search: str | None,
    skill_slug: str | None,
    limit: int,
    offset: int,
) -> tuple[list[dict], int]:
    where_clauses = []
    params: list = []

    if search:
        where_clauses.append("c.title ILIKE %s")
        params.append(f"%{search}%")

    if skill_slug:
        where_clauses.append(
            "c.id IN (SELECT cs.course_id FROM course_skills cs "
            "JOIN skills sk ON sk.id = cs.skill_id WHERE sk.slug = %s)"
        )
        params.append(skill_slug)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM courses c {where_sql}", params)
        total = cur.fetchone()[0]

        cur.execute(
            f"""
            SELECT c.id, c.title, c.url, c.difficulty, c.duration_minutes
            FROM courses c
            {where_sql}
            ORDER BY c.ingested_at DESC, c.id
            LIMIT %s OFFSET %s
            """,
            [*params, limit, offset],
        )
        courses = [
            {
                "id": str(r[0]),
                "title": r[1],
                "url": r[2],
                "difficulty": r[3],
                "duration_minutes": r[4],
            }
            for r in cur.fetchall()
        ]

        for course in courses:
            cur.execute(
                """
                SELECT sk.name, sk.slug
                FROM course_skills cs
                JOIN skills sk ON sk.id = cs.skill_id
                WHERE cs.course_id = %s
                """,
                (course["id"],),
            )
            course["skills"] = [{"name": r[0], "slug": r[1]} for r in cur.fetchall()]

        return courses, total


def get_course_by_id(conn: psycopg.Connection, course_id: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.id, c.title, c.url, c.description, c.difficulty,
                   c.duration_minutes, s.name
            FROM courses c
            JOIN sources s ON s.id = c.source_id
            WHERE c.id = %s
            """,
            (course_id,),
        )
        row = cur.fetchone()
        if not row:
            return None

        cur.execute(
            """
            SELECT sk.name, sk.slug
            FROM course_skills cs
            JOIN skills sk ON sk.id = cs.skill_id
            WHERE cs.course_id = %s
            """,
            (course_id,),
        )
        skills = [{"name": r[0], "slug": r[1]} for r in cur.fetchall()]

        return {
            "id": str(row[0]),
            "title": row[1],
            "url": row[2],
            "description": row[3],
            "difficulty": row[4],
            "duration_minutes": row[5],
            "source_name": row[6],
            "skills": skills,
        }
