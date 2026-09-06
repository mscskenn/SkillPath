"use client";

import { useCallback, useEffect, useState } from "react";
import type { GoalOut, PathResponse, PathStep } from "@/lib/api";

const STORAGE_KEY = "skillpath.currentPath";

export type StoredPath = {
  goal: GoalOut;
  steps: PathStep[];
  completedCourseIds: string[];
};

function readStoredPath(): StoredPath | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as StoredPath;
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

  useEffect(() => {
    setPath(readStoredPath());
  }, []);

  const savePath = useCallback((newPath: PathResponse) => {
    const stored: StoredPath = { ...newPath, completedCourseIds: [] };
    writeStoredPath(stored);
    setPath(stored);
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

  return { path, savePath, toggleCourseComplete, isCourseComplete, clearPath };
}
