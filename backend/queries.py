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
