"use client";

import { Dashboard } from "@/components/Dashboard";
import { Landing } from "@/components/Landing";
import { useServerPath } from "@/lib/useServerPath";

export default function HomePage() {
  const { path, isLoaded, error, isCourseComplete } = useServerPath();

  if (!isLoaded) {
    return null;
  }

  if (error) {
    return <p className="px-4 py-8 text-sm text-red-600">{error}</p>;
  }

  if (!path) {
    return <Landing />;
  }

  return <Dashboard path={path} isCourseComplete={isCourseComplete} />;
}
