"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { type CourseDetail, getCourse } from "@/lib/api";
import { useLocalPath } from "@/lib/useLocalPath";

export default function CourseDetailPage() {
  const params = useParams<{ id: string }>();
  const { path, toggleCourseComplete, isCourseComplete } = useLocalPath();
  const [course, setCourse] = useState<CourseDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    setCourse(null);
    getCourse(params.id)
      .then(setCourse)
      .catch(() => setError("Course not found."));
  }, [params.id]);

  if (error) {
    return <p className="px-4 py-8 text-sm text-red-600">{error}</p>;
  }

  if (!course) {
    return <p className="px-4 py-8 text-sm text-muted">Loading...</p>;
  }

  const stepIndex = path?.steps.findIndex((step) =>
    step.courses.some((c) => c.id === course.id)
  );
  const step = stepIndex !== undefined && stepIndex >= 0 ? path?.steps[stepIndex] : undefined;
  const nextCourseInStep =
    step && stepIndex !== undefined
      ? step.courses[step.courses.findIndex((c) => c.id === course.id) + 1]
      : undefined;

  const complete = isCourseComplete(course.id);

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-8">
      <div className="aspect-video w-full rounded bg-gray-100" />

      <div>
        <h1 className="text-xl font-bold">{course.title}</h1>
        <p className="text-sm text-gray-600">
          {course.source_name}
          {course.duration_minutes ? ` · ${course.duration_minutes} min` : ""}
          {course.difficulty ? ` · ${course.difficulty}` : ""}
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {course.skills.map((skill) => (
          <span key={skill.slug} className="rounded-full bg-gray-100 px-2 py-1 text-xs text-gray-700">
            {skill.name}
          </span>
        ))}
      </div>

      {course.description && <p className="text-sm text-gray-700">{course.description}</p>}

      {step && stepIndex !== undefined && (
        <p className="rounded border border-accent/30 bg-accent/5 px-4 py-3 text-sm">
          Step {stepIndex + 1} of {path!.steps.length} in your {path!.goal.name} path —
          builds your {step.skill.name} skills.
        </p>
      )}

      <div className="flex flex-col gap-3 md:flex-row">
        <a
          href={course.url}
          target="_blank"
          rel="noreferrer"
          className="rounded bg-accent px-4 py-3 text-center font-medium text-white"
        >
          Start course
        </a>
        <button
          onClick={() => toggleCourseComplete(course.id)}
          className="rounded border border-gray-300 px-4 py-3 font-medium"
        >
          {complete ? "Completed" : "Mark as complete"}
        </button>
      </div>

      {nextCourseInStep && (
        <Link href={`/course/${nextCourseInStep.id}`} className="text-sm underline">
          Up next: {nextCourseInStep.title}
        </Link>
      )}
    </div>
  );
}
