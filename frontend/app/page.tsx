"use client";

import { Dashboard } from "@/components/Dashboard";
import { Landing } from "@/components/Landing";
import { useLocalPath } from "@/lib/useLocalPath";

export default function HomePage() {
  const { path, isCourseComplete } = useLocalPath();

  if (!path) {
    return <Landing />;
  }

  return <Dashboard path={path} isCourseComplete={isCourseComplete} />;
}
