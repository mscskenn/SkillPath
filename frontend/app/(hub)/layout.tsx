import { Nav } from "@/components/Nav";

export default function HubLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className="flex min-h-screen flex-col pb-16 md:pb-0">
      <Nav />
      <main className="flex-1">{children}</main>
    </div>
  );
}
