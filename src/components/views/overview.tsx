import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis } from "recharts";
import { Badge } from "@/components/ui/badge";
import { useAdmin } from "@/lib/admin-store";

const SERIES = [
  { day: "Wed", n: 820 },
  { day: "Thu", n: 940 },
  { day: "Fri", n: 1012 },
  { day: "Sat", n: 1288 },
  { day: "Sun", n: 1440 },
  { day: "Mon", n: 1195 },
  { day: "Tue", n: 1362 },
];

export function OverviewView() {
  const stats = useAdmin((s) => s.stats);
  const jobs = useAdmin((s) => s.jobs);
  const workers = useAdmin((s) => s.workers);
  const queued = useAdmin((s) => s.queued);
  const completed = useAdmin((s) => s.completed);
  const env = useAdmin((s) => s.env);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header>
        <p className="text-[11px] uppercase tracking-[0.18em] text-subtle">Overview</p>
        <h1 className="mt-1 font-display text-2xl font-semibold tracking-tight">Operations</h1>
      </header>

      <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[
          { label: "Users", value: stats.users.toLocaleString() },
          { label: "Downloads", value: stats.downloads.toLocaleString() },
          { label: "Premium", value: String(stats.premium) },
          { label: "Workers", value: `${workers} live` },
        ].map((card) => (
          <div key={card.label} className="rounded-lg border border-border bg-surface p-4">
            <p className="text-[11px] uppercase tracking-[0.14em] text-subtle">{card.label}</p>
            <p className="mt-2 font-display text-2xl font-semibold tabular-nums">{card.value}</p>
          </div>
        ))}
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.4fr_0.8fr]">
        <div className="rounded-lg border border-border bg-surface p-4 sm:p-5">
          <div className="mb-3 flex items-end justify-between">
            <div>
              <h2 className="font-display text-base font-semibold">Throughput</h2>
              <p className="text-sm text-muted-foreground">Completed sends, last 7 days</p>
            </div>
            <span className="font-mono text-xs text-subtle">{completed.toLocaleString()} total</span>
          </div>
          <div className="h-44">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={SERIES}>
                <defs>
                  <linearGradient id="fillN" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#c5ccd6" stopOpacity={0.28} />
                    <stop offset="100%" stopColor="#c5ccd6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="day" tick={{ fill: "#6d7380", fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ background: "#111318", border: "1px solid rgba(243,244,246,0.12)", borderRadius: 8 }}
                  labelStyle={{ color: "#9aa0ab" }}
                />
                <Area type="monotone" dataKey="n" stroke="#d7dde6" fill="url(#fillN)" strokeWidth={1.6} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-lg border border-border bg-surface p-4 sm:p-5">
          <h2 className="font-display text-base font-semibold">Queue</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Fair priority: VIP, Super, Regular, then free. One user cannot occupy another user's files.
          </p>
          <dl className="mt-5 space-y-3">
            <div className="flex justify-between text-sm">
              <dt className="text-muted-foreground">Waiting</dt>
              <dd className="font-mono tabular-nums">{queued}</dd>
            </div>
            <div className="flex justify-between text-sm">
              <dt className="text-muted-foreground">Max concurrent</dt>
              <dd className="font-mono tabular-nums">{env.MAX_CONCURRENT}</dd>
            </div>
            <div className="flex justify-between text-sm">
              <dt className="text-muted-foreground">Queue cap</dt>
              <dd className="font-mono tabular-nums">{env.MAX_QUEUE_SIZE}</dd>
            </div>
          </dl>
        </div>
      </section>

      <section className="rounded-lg border border-border bg-surface p-4 sm:p-5">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <h2 className="font-display text-base font-semibold">Isolated lanes</h2>
            <p className="text-sm text-muted-foreground">Each transfer writes only under its own user/job directory.</p>
          </div>
          <Badge tone="live">{jobs.length} in flight</Badge>
        </div>
        <ul className="space-y-4">
          {jobs.map((job) => (
            <li key={job.job_id} className="rounded-md bg-surface-2 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-medium">
                  {job.filename}
                  <span className="ml-2 font-mono text-xs text-subtle">u{job.user_id}</span>
                </p>
                <span className="font-mono text-xs text-muted-foreground">
                  {Math.round(job.progress)}% · {job.speed}
                </span>
              </div>
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-bg">
                <div
                  className="h-full rounded-full bg-primary transition-[width] duration-[var(--motion-fast)]"
                  style={{ width: `${Math.min(100, job.progress)}%` }}
                />
              </div>
              <p className="mt-2 truncate font-mono text-[11px] text-subtle">{job.path}</p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
