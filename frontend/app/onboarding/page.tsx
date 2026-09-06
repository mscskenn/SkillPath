"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApiError, createPath } from "@/lib/api";
import { useRequireAuth } from "@/lib/useRequireAuth";

const POPULAR_GOALS = [{ label: "Data analyst", slug: "data-analyst" }];

export default function OnboardingPage() {
  const router = useRouter();
  const isAuthChecked = useRequireAuth();
  const [goalSlug, setGoalSlug] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function submitGoal(slug: string) {
    setError(null);
    setIsSubmitting(true);
    try {
      await createPath(slug);
      router.push("/");
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setError("We don't have a path for that goal yet.");
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!isAuthChecked) {
    return null;
  }

  return (
    <div className="mx-auto flex max-w-md flex-col gap-6 px-4 py-12">
      <h1 className="text-2xl font-bold">What do you want to learn?</h1>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (goalSlug.trim()) submitGoal(goalSlug.trim());
        }}
        className="flex flex-col gap-3"
      >
        <input
          type="text"
          value={goalSlug}
          onChange={(e) => setGoalSlug(e.target.value)}
          placeholder="e.g. data-analyst"
          className="rounded border border-gray-300 px-4 py-3 text-base"
        />
        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded bg-accent px-4 py-3 font-medium text-white disabled:opacity-50"
        >
          Build my path
        </button>
      </form>

      <div className="flex flex-wrap gap-2">
        {POPULAR_GOALS.map((goal) => (
          <button
            key={goal.slug}
            onClick={() => submitGoal(goal.slug)}
            disabled={isSubmitting}
            className="rounded-full border border-gray-300 px-3 py-1 text-sm disabled:opacity-50"
          >
            {goal.label}
          </button>
        ))}
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <p className="text-sm text-muted">No credit card. No catch. Ever.</p>
    </div>
  );
}
