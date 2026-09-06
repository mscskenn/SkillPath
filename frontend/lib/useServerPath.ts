"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, clearMyPath, getMyPath, toggleProgress, type ServerPath } from "@/lib/api";

export type { ServerPath };

export function useServerPath() {
  const [path, setPath] = useState<ServerPath | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const result = await getMyPath();
      setPath(result);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setPath(null);
      } else {
        throw err;
      }
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetching the current user's path requires an async call, can't run during render
    refresh().finally(() => setIsLoaded(true));
  }, [refresh]);

  const toggleCourseComplete = useCallback(async (courseId: string) => {
    const result = await toggleProgress(courseId);
    setPath((current) => {
      if (!current) return current;
      const completed_course_ids = result.completed
        ? [...current.completed_course_ids, courseId]
        : current.completed_course_ids.filter((id) => id !== courseId);
      return { ...current, completed_course_ids };
    });
  }, []);

  const isCourseComplete = useCallback(
    (courseId: string) => path?.completed_course_ids.includes(courseId) ?? false,
    [path]
  );

  const clearPath = useCallback(async () => {
    await clearMyPath();
    setPath(null);
  }, []);

  return { path, isLoaded, refresh, toggleCourseComplete, isCourseComplete, clearPath };
}
