import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/app-shell";
import { LoginScreen } from "@/components/login-screen";
import { HudBackdrop } from "@/components/hud/backdrop";
import { useAdmin } from "@/lib/admin-store";

export const Route = createFileRoute("/")({ component: Home });

function Home() {
  const authed = useAdmin((s) => s.authed);
  return <HudBackdrop>{authed ? <AppShell /> : <LoginScreen />}</HudBackdrop>;
}
