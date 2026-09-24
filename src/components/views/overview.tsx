import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis } from "recharts";
import { Badge } from "@/components/ui/badge";
import { HudKicker, HudPanel } from "@/components/hud/panel";
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

  const cards = [
    { label: "Users", value: stats.users.toLocaleString() },
    { label: "Downloads", value: stats.downloads.toLocaleString() },
    { label: "Premium", value: String(stats.premium) },
    { label: "Workers", value: `${workers} live` },
  ];

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <header>
        <HudKicker>Overview</HudKicker>
        <h1 className="mt-1 font-display text-2xl font-semibold">Operations</h1>
      </header>

      <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {cards.map((card, i) => (
          <HudPanel key={card.label} className={`hud-enter hud-enter-d${i + 1}`}>
            <p className="hud-kicker">{card.label}</p>
            <p className="mt-2 font-display text-2xl font-semibold tabular-nums text-primary">{card.value}</p>
          </HudPanel>
        ))}
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.4fr_0.8fr]">
        <HudPanel sweep>
          <div className="mb-3 flex items-end justify-between">
            <div>
              <h2 className="font-display text-base font-semibold">Throughput</h2>
              <p className="text-sm text-muted-foreground">Completed sends, last 7 days</p>
            </div>
            <span className="font-display text-xs tracking-widest text-subtle">{completed.toLocaleString()} total</span>
          </div>
          <div className="h-44">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={SERIES}>
                <defs>
                  <linearGradient id="fillN" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#6ee7ff" stopOpacity={0.32} />
                    <stop offset="100%" stopColor="#6ee7ff" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="day" tick={{ fill: "#5d7e8f", fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ background: "#07131c", border: "1px solid rgba(110,231,255,0.22)", borderRadius: 4 }}
                  labelStyle={{ color: "#8fb4c6" }}
                />
                <Area type="monotone" dataKey="n" stroke="#6ee7ff" fill="url(#fillN)" strokeWidth={1.6} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </HudPanel>

        <HudPanel>
          <h2 className="font-display text-base font-semibold">Queue</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Fair priority: VIP, Super, Regular, then free. Lanes never share files.
          </p>
          <dl className="mt-5 space-y-3">
            {[
              ["Waiting", queued],
              ["Max concurrent", env.MAX_CONCURRENT],
              ["Queue cap", env.MAX_QUEUE_SIZE],
            ].map(([label, value]) => (
              <div key={String(label)} className="flex justify-between text-sm">
                <dt className="text-muted-foreground">{label}</dt>
                <dd className="font-display tabular-nums tracking-widest text-primary">{value}</dd>
              </div>
            ))}
          </dl>
        </HudPanel>
      </section>

      <HudPanel>
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <h2 className="font-display text-base font-semibold">Isolated lanes</h2>
            <p className="text-sm text-muted-foreground">Each transfer writes only under its own user/job directory.</p>
          </div>
          <Badge tone="live">{jobs.length} in flight</Badge>
        </div>
        <ul className="space-y-3">
          {jobs.map((job) => (
            <li key={job.job_id} className="bg-surface-2/80 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-medium">
                  {job.filename}
                  <span className="ml-2 font-display text-xs tracking-widest text-subtle">u{job.user_id}</span>
                </p>
                <span className="font-display text-xs tracking-widest text-primary">
                  {Math.round(job.progress)}% · {job.speed}
                </span>
              </div>
              <div className="mt-2 h-1 overflow-hidden bg-bg">
                <div
                  className="h-full bg-primary shadow-[0_0_12px_var(--color-primary)] transition-[width] duration-[var(--motion-fast)]"
                  style={{ width: `${Math.min(100, job.progress)}%` }}
                />
              </div>
              <p className="mt-2 truncate font-display text-xs tracking-wider text-subtle">{job.path}</p>
            </li>
          ))}
        </ul>
      </HudPanel>
    </div>
  );
}
