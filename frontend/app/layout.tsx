import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "@/components/Nav";

export const metadata: Metadata = {
  title: "SkillPath",
  description: "Free, step-by-step learning paths toward any skill.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-white text-gray-900">
        <div className="flex min-h-screen flex-col pb-16 md:pb-0">
          <Nav />
          <main className="flex-1">{children}</main>
        </div>
      </body>
    </html>
  );
}
