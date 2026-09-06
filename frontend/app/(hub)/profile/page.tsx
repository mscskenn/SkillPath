"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useServerPath } from "@/lib/useServerPath";
import { supabase } from "@/lib/supabaseClient";

export default function ProfilePage() {
  const router = useRouter();
  const { path, isLoaded, isCourseComplete, clearPath } = useServerPath();

  const allCourses = path?.steps.flatMap((step) => step.courses) ?? [];
  const completedCount = allCourses.filter((c) => isCourseComplete(c.id)).length;
  const totalMinutes = allCourses
    .filter((c) => isCourseComplete(c.id))
    .reduce((sum, c) => sum + (c.duration_minutes ?? 0), 0);
  const hoursLearned = Math.round(totalMinutes / 60);

  async function handleChangeGoal() {
    await clearPath();
    router.push("/onboarding");
  }

  async function handleSignOut() {
    await supabase.auth.signOut();
    router.push("/login");
  }

  if (!isLoaded) {
    return null;
  }

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-8">
      <h1 className="text-xl font-bold">Your progress</h1>

      <div className="flex gap-4 text-sm">
        <span className="rounded-full bg-gray-100 px-3 py-1">
          {completedCount} courses done
        </span>
        <span className="rounded-full bg-gray-100 px-3 py-1">
          {hoursLearned} hours learned
        </span>
      </div>

      <div>
        <h2 className="mb-2 font-medium">Your paths</h2>
        {!path && (
          <p className="text-sm text-muted">
            No path started yet.{" "}
            <Link href="/onboarding" className="underline">
              Set a goal
            </Link>
            .
          </p>
        )}
        {path && (
          <>
            <Link
              href="/"
              className="flex items-center justify-between border-y border-gray-200 py-3"
            >
              <span>{path.goal.name}</span>
              <span className="text-sm text-muted">
                {completedCount}/{allCourses.length} complete
              </span>
            </Link>
            <button
              onClick={handleChangeGoal}
              className="mt-3 text-sm underline text-muted"
            >
              Change goal
            </button>
          </>
        )}
      </div>

      <button
        onClick={handleSignOut}
        className="text-sm underline text-muted"
      >
        Log out
      </button>
    </div>
  );
}
