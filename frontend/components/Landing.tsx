import Link from "next/link";

export function Landing() {
  return (
    <div className="mx-auto flex max-w-2xl flex-col items-center gap-8 px-4 py-16 text-center">
      <div className="flex flex-col gap-4">
        <h1 className="text-3xl font-bold md:text-4xl">
          You don&apos;t need money to learn something new.
        </h1>
        <p className="text-gray-600">
          SkillPath turns free content from across the web into a clear,
          step-by-step path — so you always know what to do next.
        </p>
      </div>

      <Link
        href="/onboarding"
        className="rounded bg-accent px-6 py-3 font-medium text-white"
      >
        Start for free
      </Link>

      <div className="grid grid-cols-1 gap-6 text-left md:grid-cols-3">
        <div>
          <p className="font-medium">1. Pick a goal</p>
          <p className="text-sm text-gray-600">Tell us what you want to learn.</p>
        </div>
        <div>
          <p className="font-medium">2. Get your path</p>
          <p className="text-sm text-gray-600">
            An ordered sequence of free courses, built for you.
          </p>
        </div>
        <div>
          <p className="font-medium">3. Track progress</p>
          <p className="text-sm text-gray-600">
            Mark courses complete as you go.
          </p>
        </div>
      </div>

      <div className="flex gap-4 text-sm text-success">
        <span>$0 cost</span>
        <span>100% free</span>
        <span>any skill</span>
      </div>
    </div>
  );
}
