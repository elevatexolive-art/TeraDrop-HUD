import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { HudPanel } from "@/components/hud/panel";
import { useAdmin } from "@/lib/admin-store";

export function LoginScreen() {
  const login = useAdmin((s) => s.login);
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!login(password)) {
      setError("Access denied · credential mismatch");
      return;
    }
    setError("");
  }

  return (
    <main className="relative min-h-dvh px-5 py-10 sm:px-8">
      <div className="pointer-events-none absolute inset-x-4 top-4 h-px bg-primary/40 sm:inset-x-8" />
      <div className="pointer-events-none absolute inset-x-4 bottom-4 h-px bg-primary/25 sm:inset-x-8" />
      <div className="mx-auto flex min-h-[calc(100dvh-5rem)] w-full max-w-6xl flex-col justify-between gap-12 lg:flex-row lg:items-center">
        <section className="max-w-lg hud-enter">
          <p className="hud-kicker text-primary">TeraDrop · orbital ops</p>
          <h1 className="mt-5 font-display text-4xl font-semibold leading-[1.05] text-foreground sm:text-5xl">
            Live HUD for isolated concurrent transfers.
          </h1>
          <p className="mt-5 max-w-md text-lg leading-relaxed text-muted-foreground">
            Particles float free in the field. Each operator lane stays private. Environment —
            including the bot token — is editable from this console.
          </p>
          <dl className="mt-10 grid max-w-md grid-cols-2 gap-6">
            <div className="hud-enter hud-enter-d2">
              <dt className="hud-kicker">Lane</dt>
              <dd className="mt-1 font-display text-sm tracking-widest text-primary">{"u<id>/job"}</dd>
            </div>
            <div className="hud-enter hud-enter-d3">
              <dt className="hud-kicker">Apply</dt>
              <dd className="mt-1 font-display text-sm tracking-widest text-primary">live · restart</dd>
            </div>
          </dl>
        </section>

        <HudPanel sweep className="w-full max-w-md hud-enter hud-enter-d2">
          <form onSubmit={onSubmit}>
            <p className="hud-kicker text-primary">Gate</p>
            <h2 className="mt-2 font-display text-xl font-semibold">Authenticate</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Admin password from environment. Preview default is{" "}
              <code className="font-display tracking-widest text-primary">teradrop</code>.
            </p>
            <label className="mt-6 mb-2 block hud-kicker">Passphrase</label>
            <Input
              type="password"
              autoComplete="current-password"
              placeholder="enter passphrase"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            {error ? <p className="mt-3 text-sm text-danger">{error}</p> : null}
            <Button type="submit" className="mt-5 w-full">
              Engage console
            </Button>
          </form>
        </HudPanel>
      </div>
    </main>
  );
}
