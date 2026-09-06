"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { supabase } from "@/lib/supabaseClient";

export default function SignupPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    const { data, error: signUpError } = await supabase.auth.signUp({
      email,
      password,
    });
    setIsSubmitting(false);
    if (signUpError) {
      setError("Something went wrong creating your account. Please try again.");
      return;
    }
    if (!data.session) {
      setError("Check your email to confirm your account, then log in.");
      return;
    }
    router.push("/onboarding");
  }

  return (
    <div className="mx-auto flex max-w-md flex-col gap-6 px-4 py-12">
      <h1 className="text-2xl font-bold">Sign up</h1>

      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="email"
          required
          className="rounded border border-gray-300 px-4 py-3 text-base"
        />
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="password"
          required
          minLength={6}
          className="rounded border border-gray-300 px-4 py-3 text-base"
        />
        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded bg-accent px-4 py-3 font-medium text-white disabled:opacity-50"
        >
          Sign up
        </button>
      </form>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <p className="text-sm text-muted">No credit card. No catch. Ever.</p>

      <div className="border-t border-gray-200 pt-4 text-center text-sm">
        Already have an account?{" "}
        <Link href="/login" className="underline">
          Log in
        </Link>
      </div>
    </div>
  );
}
