-- Sprint 2 schema: goals, goal_skills
-- Seeds one example goal (data-analyst) so POST /paths has real data to
-- return during development and testing. "data-visualization" is seeded
-- with no ingested courses on purpose, to exercise the empty-courses path.

CREATE TABLE IF NOT EXISTS goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS goal_skills (
    goal_id UUID NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    step_order INT NOT NULL,
    PRIMARY KEY (goal_id, skill_id)
);

INSERT INTO skills (name, slug) VALUES
    ('SQL', 'sql'),
    ('Python', 'python'),
    ('Statistics', 'statistics'),
    ('Data Visualization', 'data-visualization')
ON CONFLICT (slug) DO NOTHING;

INSERT INTO goals (name, slug) VALUES
    ('Data Analyst', 'data-analyst')
ON CONFLICT (slug) DO NOTHING;

INSERT INTO goal_skills (goal_id, skill_id, step_order)
SELECT g.id, s.id, v.step_order
FROM (VALUES
    ('data-analyst', 'sql', 1),
    ('data-analyst', 'python', 2),
    ('data-analyst', 'statistics', 3),
    ('data-analyst', 'data-visualization', 4)
) AS v(goal_slug, skill_slug, step_order)
JOIN goals g ON g.slug = v.goal_slug
JOIN skills s ON s.slug = v.skill_slug
ON CONFLICT (goal_id, skill_id) DO NOTHING;
