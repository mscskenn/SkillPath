"use client";

import { useCallback, useEffect, useState } from "react";
import type { GoalOut, PathResponse, PathStep } from "@/lib/api";

const STORAGE_KEY = "skillpath.currentPath";

export type StoredPath = {
  goal: GoalOut;
  steps: PathStep[];
  completedCourseIds: string[];
};

function isValidStoredPath(value: unknown): value is StoredPath {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  if (typeof v.goal !== "object" || v.goal === null) return false;
  const goal = v.goal as Record<string, unknown>;
  return (
    typeof goal.name === "string" &&
    typeof goal.slug === "string" &&
    Array.isArray(v.steps) &&
    Array.isArray(v.completedCourseIds)
  );
}

function readStoredPath(): StoredPath | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    const parsed: unknown = JSON.parse(raw);
    return isValidStoredPath(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function writeStoredPath(path: StoredPath | null) {
  if (typeof window === "undefined") return;
  if (path === null) {
    window.localStorage.removeItem(STORAGE_KEY);
  } else {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(path));
  }
}

export function useLocalPath() {
  const [path, setPath] = useState<StoredPath | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- SSR-safe hydration: localStorage can't be read during server render, so this effect populates state after mount
    setPath(readStoredPath());
    setIsLoaded(true);
  }, []);

  const savePath = useCallback((newPath: PathResponse) => {
    setPath((current) => {
      const completedCourseIds =
        current?.goal.slug === newPath.goal.slug ? current.completedCourseIds : [];
      const stored: StoredPath = { ...newPath, completedCourseIds };
      writeStoredPath(stored);
      return stored;
    });
  }, []);

  const toggleCourseComplete = useCallback((courseId: string) => {
    setPath((current) => {
      if (!current) return current;
      const isComplete = current.completedCourseIds.includes(courseId);
      const completedCourseIds = isComplete
        ? current.completedCourseIds.filter((id) => id !== courseId)
        : [...current.completedCourseIds, courseId];
      const updated = { ...current, completedCourseIds };
      writeStoredPath(updated);
      return updated;
    });
  }, []);

  const isCourseComplete = useCallback(
    (courseId: string) => path?.completedCourseIds.includes(courseId) ?? false,
    [path]
  );

  const clearPath = useCallback(() => {
    writeStoredPath(null);
    setPath(null);
  }, []);

  return { path, isLoaded, savePath, toggleCourseComplete, isCourseComplete, clearPath };
}
