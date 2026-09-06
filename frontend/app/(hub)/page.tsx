"use client";

import { Dashboard } from "@/components/Dashboard";
import { Landing } from "@/components/Landing";
import { useServerPath } from "@/lib/useServerPath";

export default function HomePage() {
  const { path, isLoaded, isCourseComplete } = useServerPath();

  if (!isLoaded) {
    return null;
  }

  if (!path) {
    return <Landing />;
  }

  return <Dashboard path={path} isCourseComplete={isCourseComplete} />;
}
