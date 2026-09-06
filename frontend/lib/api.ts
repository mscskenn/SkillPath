import { supabase } from "@/lib/supabaseClient";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export type SkillOut = { name: string; slug: string };
export type GoalOut = { name: string; slug: string };
export type CourseOut = {
  id: string;
  title: string;
  url: string;
  difficulty: string | null;
  duration_minutes: number | null;
};
export type PathStep = { skill: SkillOut; courses: CourseOut[] };
export type PathResponse = { goal: GoalOut; steps: PathStep[] };
export type CourseListItem = CourseOut & { skills: SkillOut[] };
export type CourseDetail = CourseOut & {
  description: string | null;
  source_name: string;
  skills: SkillOut[];
};

export type ServerPath = {
  goal: GoalOut;
  steps: PathStep[];
  completed_course_ids: string[];
};

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new ApiError(response.status, body.detail ?? response.statusText);
  }
  return response.json();
}

async function authHeaders(): Promise<Record<string, string>> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function createPath(goalSlug: string): Promise<PathResponse> {
  const response = await fetch(`${API_BASE_URL}/paths`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await authHeaders()) },
    body: JSON.stringify({ goal_slug: goalSlug }),
  });
  return handleResponse<PathResponse>(response);
}

export async function listCourses(params: {
  search?: string;
  skill?: string;
  limit?: number;
  offset?: number;
}): Promise<{ courses: CourseListItem[]; total: number }> {
  const query = new URLSearchParams();
  if (params.search) query.set("search", params.search);
  if (params.skill) query.set("skill", params.skill);
  if (params.limit !== undefined) query.set("limit", String(params.limit));
  if (params.offset !== undefined) query.set("offset", String(params.offset));

  const response = await fetch(`${API_BASE_URL}/courses?${query.toString()}`);
  return handleResponse<{ courses: CourseListItem[]; total: number }>(response);
}

export async function getCourse(id: string): Promise<CourseDetail> {
  const response = await fetch(`${API_BASE_URL}/courses/${id}`);
  return handleResponse<CourseDetail>(response);
}

export async function getMyPath(): Promise<ServerPath> {
  const response = await fetch(`${API_BASE_URL}/me/path`, {
    headers: await authHeaders(),
  });
  return handleResponse<ServerPath>(response);
}

export async function toggleProgress(
  courseId: string
): Promise<{ course_id: string; completed: boolean }> {
  const response = await fetch(`${API_BASE_URL}/me/progress`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await authHeaders()) },
    body: JSON.stringify({ course_id: courseId }),
  });
  return handleResponse<{ course_id: string; completed: boolean }>(response);
}

export async function clearMyPath(): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/me/path`, {
    method: "DELETE",
    headers: await authHeaders(),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new ApiError(response.status, body.detail ?? response.statusText);
  }
}
