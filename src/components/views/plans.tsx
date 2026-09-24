import { FormEvent, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAdmin, type Plan } from "@/lib/admin-store";

const EMPTY: Plan = {
  key: "",
  label: "",
  short_label: "",
  price: 0,
  duration_days: 30,
  batch_limit: 5,
  total_links: 0,
  active: true,
};

export function PlansView() {
  const plans = useAdmin((s) => s.plans);
  const savePlan = useAdmin((s) => s.savePlan);
  const hidePlan = useAdmin((s) => s.hidePlan);
  const [form, setForm] = useState<Plan>(EMPTY);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!form.key || !form.label) return;
    savePlan({ ...form, key: form.key.toLowerCase() });
    setForm(EMPTY);
    toast.success("Plan saved");
  }

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <header>
        <p className="text-[11px] uppercase tracking-[0.18em] text-subtle">Plans</p>
        <h1 className="mt-1 font-display text-2xl font-semibold tracking-tight">Premium catalog</h1>
      </header>
      <ul className="space-y-2">
        {plans.map((plan) => (
          <li key={plan.key} className="flex flex-col gap-3 rounded-lg border border-border bg-surface p-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="font-medium">
                {plan.label}{" "}
                <span className="font-mono text-xs text-subtle">{plan.key}</span>
                {!plan.active ? <span className="ml-2 text-xs text-warn">hidden</span> : null}
              </p>
              <p className="text-sm text-muted-foreground">
                ₹{plan.price} · {plan.duration_days} days · batch {plan.batch_limit} ·{" "}
                {plan.total_links ? `${plan.total_links} links` : "unlimited"}
              </p>
            </div>
            <div className="flex gap-2">
              <Button variant="secondary" size="sm" onClick={() => setForm(plan)}>
                Edit
              </Button>
              <Button variant="danger" size="sm" onClick={() => hidePlan(plan.key)}>
                Hide
              </Button>
            </div>
          </li>
        ))}
      </ul>
      <form onSubmit={onSubmit} className="grid gap-3 rounded-lg border border-border bg-surface p-4 sm:grid-cols-2">
        <h2 className="font-display text-base font-semibold sm:col-span-2">Add or edit</h2>
        <Input placeholder="key" value={form.key} onChange={(e) => setForm({ ...form, key: e.target.value })} />
        <Input placeholder="name" value={form.label} onChange={(e) => setForm({ ...form, label: e.target.value })} />
        <Input placeholder="short name" value={form.short_label} onChange={(e) => setForm({ ...form, short_label: e.target.value })} />
        <Input placeholder="price" type="number" value={form.price} onChange={(e) => setForm({ ...form, price: Number(e.target.value) })} />
        <Input placeholder="days" type="number" value={form.duration_days} onChange={(e) => setForm({ ...form, duration_days: Number(e.target.value) })} />
        <Input placeholder="batch" type="number" value={form.batch_limit} onChange={(e) => setForm({ ...form, batch_limit: Number(e.target.value) })} />
        <Input placeholder="total links, 0 = unlimited" type="number" value={form.total_links} onChange={(e) => setForm({ ...form, total_links: Number(e.target.value) })} />
        <div className="flex items-end sm:col-span-2">
          <Button type="submit">Save plan</Button>
        </div>
      </form>
    </div>
  );
}
