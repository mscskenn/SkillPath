"use client";

import { Nav } from "@/components/Nav";
import { useRequireAuth } from "@/lib/useRequireAuth";

export default function HubLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const isAuthChecked = useRequireAuth();

  if (!isAuthChecked) {
    return null;
  }

  return (
    <div className="flex min-h-screen flex-col pb-16 md:pb-0">
      <Nav />
      <main className="flex-1">{children}</main>
    </div>
  );
}
