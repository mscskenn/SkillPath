"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { type CourseListItem, listCourses } from "@/lib/api";

export default function BrowsePage() {
  const [search, setSearch] = useState("");
  const [courses, setCourses] = useState<CourseListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const timeout = setTimeout(() => {
      setIsLoading(true);
      setError(null);
      listCourses({ search: search || undefined, limit: 20 })
        .then((result) => setCourses(result.courses))
        .catch(() => setError("Couldn't load courses. Please try again."))
        .finally(() => setIsLoading(false));
    }, 300);
    return () => clearTimeout(timeout);
  }, [search]);

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-8">
      <input
        type="text"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="search courses"
        className="rounded border border-gray-300 px-4 py-3 text-base"
      />

      {isLoading && <p className="text-sm text-muted">Loading...</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      <ul className="flex flex-col divide-y divide-gray-200 border-y border-gray-200">
        {courses.map((course) => (
          <li key={course.id} className="py-4">
            <Link href={`/course/${course.id}`} className="flex flex-col gap-1">
              <span className="font-medium">{course.title}</span>
              <div className="flex flex-wrap gap-2 text-xs">
                <span className="rounded-full bg-success/10 px-2 py-1 text-success">
                  Free
                </span>
                {course.difficulty && (
                  <span className="rounded-full bg-gray-100 px-2 py-1 text-gray-700">
                    {course.difficulty}
                  </span>
                )}
                {course.skills.map((skill) => (
                  <span key={skill.slug} className="rounded-full bg-gray-100 px-2 py-1 text-gray-700">
                    {skill.name}
                  </span>
                ))}
              </div>
            </Link>
          </li>
        ))}
      </ul>

      {!isLoading && courses.length === 0 && (
        <p className="text-sm text-muted">No courses found.</p>
      )}
    </div>
  );
}
