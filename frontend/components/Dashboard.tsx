import Link from "next/link";
import type { StoredPath } from "@/lib/useLocalPath";

export function Dashboard({
  path,
  isCourseComplete,
}: {
  path: StoredPath;
  isCourseComplete: (courseId: string) => boolean;
}) {
  const allCourses = path.steps.flatMap((step) => step.courses);
  const completedCount = allCourses.filter((c) => isCourseComplete(c.id)).length;
  const totalCount = allCourses.length;
  const progressPercent = totalCount === 0 ? 0 : Math.round((completedCount / totalCount) * 100);

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-8">
      <div>
        <h1 className="text-xl font-bold">{path.goal.name}</h1>
        <div className="mt-2 h-2 w-full rounded-full bg-gray-200">
          <div
            className="h-2 rounded-full bg-accent"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      <div className="flex gap-4 text-sm">
        <span className="rounded-full bg-gray-100 px-3 py-1">
          {totalCount - completedCount} steps left
        </span>
        <span className="rounded-full bg-success/10 px-3 py-1 text-success">
          Free
        </span>
      </div>

      <ol className="flex flex-col divide-y divide-gray-200 border-y border-gray-200">
        {path.steps.map((step, index) => {
          const stepComplete =
            step.courses.length > 0 && step.courses.every((c) => isCourseComplete(c.id));
          return (
            <li key={step.skill.slug} className="flex flex-col gap-2 py-4">
              <div className="flex items-center gap-3">
                <span
                  className={
                    stepComplete
                      ? "flex h-6 w-6 items-center justify-center rounded-full bg-success text-white"
                      : "flex h-6 w-6 items-center justify-center rounded-full border border-gray-400 text-gray-600"
                  }
                >
                  {index + 1}
                </span>
                <span className="font-medium">{step.skill.name}</span>
              </div>
              <div className="flex flex-col gap-1 pl-9">
                {step.courses.length === 0 && (
                  <span className="text-sm text-muted">No courses yet for this step</span>
                )}
                {step.courses.map((course) => (
                  <Link
                    key={course.id}
                    href={`/course/${course.id}`}
                    className="text-sm text-gray-900 underline"
                  >
                    {course.title}
                  </Link>
                ))}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
