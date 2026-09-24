import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAdmin } from "@/lib/admin-store";

export function LoginScreen() {
  const login = useAdmin((s) => s.login);
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!login(password)) {
      setError("That password does not match ADMIN_PANEL_PASSWORD.");
      return;
    }
    setError("");
  }

  return (
    <main className="relative min-h-dvh overflow-hidden px-5 py-10 sm:px-8">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-72 bg-[radial-gradient(ellipse_at_top,rgba(197,204,214,0.08),transparent_60%)]"
      />
      <div className="mx-auto flex min-h-[calc(100dvh-5rem)] w-full max-w-5xl flex-col justify-between gap-12 lg:flex-row lg:items-center">
        <section className="max-w-lg">
          <p className="mb-5 text-[11px] font-medium uppercase tracking-[0.22em] text-muted-foreground">
            TeraDrop · operations
          </p>
          <h1 className="font-display text-4xl font-semibold leading-[1.08] tracking-[-0.03em] text-foreground sm:text-5xl">
            Control center for isolated, concurrent transfers.
          </h1>
          <p className="mt-5 max-w-md text-base leading-relaxed text-muted-foreground">
            Every user gets a private download lane. Environment values — including the bot token —
            can be edited here and applied live when the process allows.
          </p>
          <dl className="mt-10 grid max-w-md grid-cols-2 gap-6">
            <div>
              <dt className="text-[11px] uppercase tracking-[0.16em] text-subtle">Isolation</dt>
              <dd className="mt-1 font-mono text-sm text-foreground">{"/tmp/u<id>/job"}</dd>
            </div>
            <div>
              <dt className="text-[11px] uppercase tracking-[0.16em] text-subtle">Apply</dt>
              <dd className="mt-1 font-mono text-sm text-foreground">live · restart</dd>
            </div>
          </dl>
        </section>

        <form
          onSubmit={onSubmit}
          className="w-full max-w-md rounded-xl border border-border bg-surface p-5 shadow-[0_0_0_1px_rgba(255,255,255,0.04)] sm:p-7"
        >
          <div className="mb-6">
            <h2 className="font-display text-lg font-semibold">Sign in</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Use the admin password from your environment. Preview default is{" "}
              <code className="font-mono text-foreground">teradrop</code>.
            </p>
          </div>
          <label className="mb-2 block text-[11px] uppercase tracking-[0.14em] text-subtle">
            Admin password
          </label>
          <Input
            type="password"
            autoComplete="current-password"
            placeholder="enter password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {error ? <p className="mt-3 text-sm text-danger">{error}</p> : null}
          <Button type="submit" className="mt-5 w-full">
            Open panel
          </Button>
        </form>
      </div>
    </main>
  );
}
