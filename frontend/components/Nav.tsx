import Link from "next/link";

export function Nav() {
  return (
    <nav className="flex items-center justify-around border-t border-gray-200 bg-white px-4 py-3 md:justify-start md:gap-8 md:border-b md:border-t-0">
      <Link href="/" className="text-sm font-medium text-gray-900">
        Dashboard
      </Link>
      <Link href="/browse" className="text-sm font-medium text-gray-900">
        Browse
      </Link>
      <Link href="/profile" className="text-sm font-medium text-gray-900">
        Profile
      </Link>
    </nav>
  );
}
