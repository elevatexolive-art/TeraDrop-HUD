import { FormEvent, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { useAdmin } from "@/lib/admin-store";

export function UsersView() {
  const users = useAdmin((s) => s.users);
  const applyUserAction = useAdmin((s) => s.applyUserAction);
  const [userId, setUserId] = useState("");
  const [action, setAction] = useState<"premium" | "ban" | "unban">("premium");
  const [plan, setPlan] = useState("r");
  const [q, setQ] = useState("");

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    const id = Number(userId);
    if (!id) return;
    applyUserAction(id, action, plan);
    toast.success(`Applied ${action} to ${id}`);
  }

  const filtered = users.filter((user) => {
    if (!q.trim()) return true;
    return `${user.user_id} ${user.name} ${user.username} ${user.plan}`.toLowerCase().includes(q.toLowerCase());
  });

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <header>
        <p className="text-[11px] uppercase tracking-[0.18em] text-subtle">Users</p>
        <h1 className="mt-1 font-display text-2xl font-semibold tracking-tight">Accounts</h1>
      </header>
      <form onSubmit={onSubmit} className="grid gap-2 rounded-lg border border-border bg-surface p-4 sm:grid-cols-4">
        <Input placeholder="telegram user id" value={userId} onChange={(e) => setUserId(e.target.value)} />
        <select value={action} onChange={(e) => setAction(e.target.value as typeof action)} className="h-11 rounded-md border border-border bg-surface px-3 text-sm">
          <option value="premium">grant premium</option>
          <option value="ban">ban</option>
          <option value="unban">unban</option>
        </select>
        <Input placeholder="plan key" value={plan} onChange={(e) => setPlan(e.target.value)} />
        <Button type="submit">Apply</Button>
      </form>
      <Input placeholder="filter users" value={q} onChange={(e) => setQ(e.target.value)} />
      <ul className="divide-y divide-border rounded-lg border border-border bg-surface">
        {filtered.map((user) => (
          <li key={user.user_id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
            <div>
              <p className="text-sm font-medium">
                {user.name} <span className="font-mono text-xs text-subtle">@{user.username}</span>
              </p>
              <p className="font-mono text-xs text-muted-foreground">
                {user.user_id} · {user.downloads} files · {user.seen}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Badge tone={user.banned ? "danger" : user.plan === "free" ? "neutral" : "ok"}>
                {user.banned ? "banned" : user.plan}
              </Badge>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
