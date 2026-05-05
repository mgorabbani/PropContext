import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  FileWarning,
  GitBranch,
  Sparkles,
  Wand2,
} from "lucide-react";
import {
  fetchHermesDashboard,
  fetchProperties,
  type HermesDashboard,
} from "../api";
import { cn } from "../lib/cn";

export function HermesPage() {
  const params = useParams();
  const lie = params.lie ?? "";
  const [data, setData] = useState<HermesDashboard | null>(null);
  const [properties, setProperties] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProperties()
      .then(setProperties)
      .catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    if (!lie) return;
    setLoading(true);
    setError(null);
    fetchHermesDashboard(lie)
      .then(setData)
      .catch((e) => {
        setError(String(e));
        setData(null);
      })
      .finally(() => setLoading(false));
  }, [lie]);

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-[var(--color-bg)]">
      <header className="glass sticky top-0 z-40 flex h-12 items-center justify-between gap-4 border-b border-[var(--color-border)] px-4">
        <div className="flex items-center gap-3">
          <Link
            to={lie ? `/p/${lie}` : "/"}
            aria-label="Back to wiki"
            className="grid h-7 w-7 place-items-center rounded-md border border-[var(--color-border-2)] bg-[var(--color-surface)] text-[var(--color-fg-muted)] transition-colors hover:border-[var(--color-accent-dim)] hover:text-[var(--color-fg)]"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
          </Link>
          <div className="flex items-center gap-2">
            <div className="grid h-6 w-6 place-items-center rounded-md bg-[var(--color-accent)] text-[#0b0b0a]">
              <Activity className="h-3.5 w-3.5" strokeWidth={2.5} />
            </div>
            <span className="font-display text-[15px] font-medium tracking-tight text-[var(--color-ink-50)]">
              Hermes
            </span>
            <span className="font-mono text-[10.5px] uppercase tracking-[0.2em] text-[var(--color-fg-dim)]">
              self-improvement loop
            </span>
          </div>
        </div>

        <div className="relative">
          <select
            value={lie}
            onChange={(e) => {
              window.location.href = `/p/${e.target.value}/hermes`;
            }}
            disabled={properties.length === 0}
            className="h-7 cursor-pointer appearance-none rounded-md border border-[var(--color-border-2)] bg-[var(--color-surface)] px-2.5 pr-7 font-mono text-[12px] font-medium text-[var(--color-fg)] outline-none transition-colors hover:border-[var(--color-accent-dim)] focus:border-[var(--color-accent)]"
          >
            {properties.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
          <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-[var(--color-fg-muted)]">
            <svg width="8" height="6" viewBox="0 0 8 6" fill="none">
              <path
                d="M1 1.5L4 4.5L7 1.5"
                stroke="currentColor"
                strokeWidth="1.4"
                strokeLinecap="round"
              />
            </svg>
          </span>
        </div>
      </header>

      <main className="min-h-0 flex-1 overflow-auto px-6 py-6">
        <div className="mx-auto flex max-w-5xl flex-col gap-6">
          {error && (
            <div className="rounded-md border border-[var(--color-danger,#dc2626)] bg-[color-mix(in_oklab,var(--color-danger,#dc2626)_8%,transparent)] px-3 py-2 font-mono text-[12px] text-[var(--color-danger,#dc2626)]">
              {error}
            </div>
          )}

          {loading && !data && <BlockSkeleton />}

          {data && (
            <>
              <SubstrateBlock data={data} />
              <SkillsBlockView data={data} />
              <ProposalsBlockView data={data} />
              <ArtifactsBlock data={data} />
            </>
          )}
        </div>
      </main>
    </div>
  );
}

function SectionHeader({
  icon,
  title,
  hint,
}: {
  icon: React.ReactNode;
  title: string;
  hint?: string;
}) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <span className="text-[var(--color-accent)]">{icon}</span>
        <h2 className="font-display text-[14px] font-medium tracking-tight text-[var(--color-ink-50)]">
          {title}
        </h2>
      </div>
      {hint && (
        <span className="font-mono text-[10.5px] uppercase tracking-[0.2em] text-[var(--color-fg-dim)]">
          {hint}
        </span>
      )}
    </div>
  );
}

function Card({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)]/40 p-4",
        className,
      )}
    >
      {children}
    </div>
  );
}

function Stat({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: string | number;
  tone?: "default" | "warn" | "danger" | "good";
}) {
  const toneCls = {
    default: "text-[var(--color-fg)]",
    good: "text-[var(--color-accent)]",
    warn: "text-amber-500 dark:text-amber-400",
    danger: "text-rose-500 dark:text-rose-400",
  }[tone];
  return (
    <div className="flex flex-col gap-1 rounded-md border border-[var(--color-border)] bg-[var(--color-bg)]/40 px-3 py-2.5">
      <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-[var(--color-fg-dim)]">
        {label}
      </span>
      <span
        className={cn(
          "font-display text-[20px] font-medium tabular-nums",
          toneCls,
        )}
      >
        {value}
      </span>
    </div>
  );
}

function SubstrateBlock({ data }: { data: HermesDashboard }) {
  const s = data.substrate;
  return (
    <section className="flex flex-col gap-3">
      <SectionHeader
        icon={<Activity className="h-3.5 w-3.5" />}
        title="Substrate"
        hint="_hermes_feedback.jsonl"
      />
      <Card>
        {!s.exists ? (
          <p className="font-mono text-[12px] text-[var(--color-fg-muted)]">
            No substrate yet. Run an ingest to seed feedback.
          </p>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
              <Stat label="total events" value={s.total_events} />
              <Stat label="applied" value={s.applied_events} tone="good" />
              <Stat
                label="misses"
                value={s.miss_events}
                tone={s.miss_events > 0 ? "warn" : "default"}
              />
              <Stat
                label="conflicts"
                value={s.conflict_events}
                tone={s.conflict_events > 0 ? "danger" : "default"}
              />
              <Stat
                label="upstream errors"
                value={s.error_events}
                tone={s.error_events > 0 ? "danger" : "default"}
              />
            </div>
            {(s.last_event_id || s.last_ts) && (
              <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-[var(--color-border)] pt-3 font-mono text-[11px] text-[var(--color-fg-muted)]">
                {s.last_event_id && (
                  <span>
                    last event: <span className="text-[var(--color-fg)]">{s.last_event_id}</span>
                  </span>
                )}
                {s.last_ts && (
                  <span>
                    at <span className="text-[var(--color-fg)]">{s.last_ts}</span>
                  </span>
                )}
              </div>
            )}
          </>
        )}
      </Card>
    </section>
  );
}

function SkillsBlockView({ data }: { data: HermesDashboard }) {
  const sk = data.skills;
  return (
    <section className="flex flex-col gap-3">
      <SectionHeader
        icon={<Sparkles className="h-3.5 w-3.5" />}
        title="Inner loop · skills"
        hint={`promoted ${sk.promoted_count} · registry ${sk.registry_event_types.length}`}
      />
      {sk.registry_event_types.length > 0 && (
        <Card>
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle2 className="h-3.5 w-3.5 text-[var(--color-accent)]" />
            <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-[var(--color-fg-dim)]">
              active briefings
            </span>
            <span className="font-mono text-[10.5px] text-[var(--color-fg-dim)]">
              · injected into next extract prompt
            </span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {sk.registry_event_types.map((et) => {
              const n = sk.registry_briefings[et] ?? 0;
              const promoted = n >= sk.promotion_threshold;
              return (
                <span
                  key={et}
                  className="inline-flex items-center gap-1 rounded-full border border-[var(--color-accent-dim)] bg-[color-mix(in_oklab,var(--color-accent)_8%,transparent)] px-2.5 py-0.5 font-mono text-[11px] text-[var(--color-accent)]"
                >
                  {et}
                  <span className="opacity-70">
                    ×{n}
                    {!promoted && ` → ${sk.promotion_threshold}`}
                  </span>
                  {promoted && (
                    <span className="text-emerald-500 dark:text-emerald-400">✓</span>
                  )}
                </span>
              );
            })}
          </div>
        </Card>
      )}

      {sk.candidates.length === 0 && sk.buckets.length > 0 && (
        <Card>
          <div className="flex items-center justify-between gap-2 mb-2">
            <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-[var(--color-fg-dim)]">
              pattern buckets · progress to promotion
            </span>
            <span className="font-mono text-[10.5px] text-[var(--color-fg-dim)]">
              need ≥{sk.promotion_threshold} same-shape
            </span>
          </div>
          <ul className="flex flex-col gap-2">
            {sk.buckets.map((b) => {
              const pct = Math.min(
                100,
                Math.round((b.occurrences / sk.promotion_threshold) * 100),
              );
              return (
                <li key={b.slug} className="flex flex-col gap-1">
                  <div className="flex items-baseline justify-between gap-2 font-mono text-[11px]">
                    <span className="truncate text-[var(--color-fg)]">
                      <span className="text-[var(--color-fg-muted)]">{b.event_type}</span>
                      {" + "}
                      {b.path_templates.length === 0 ? (
                        <span className="italic text-[var(--color-fg-dim)]">no paths</span>
                      ) : (
                        b.path_templates.join(", ")
                      )}
                    </span>
                    <span className="shrink-0 tabular-nums text-[var(--color-fg-muted)]">
                      {b.occurrences}/{sk.promotion_threshold}
                    </span>
                  </div>
                  <div className="h-1 w-full overflow-hidden rounded bg-[var(--color-bg)]/60">
                    <div
                      className="h-full bg-[var(--color-accent)] transition-all"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </li>
              );
            })}
          </ul>
        </Card>
      )}
      {sk.candidates.length === 0 && sk.buckets.length === 0 ? (
        <Card>
          <p className="font-mono text-[12px] text-[var(--color-fg-muted)]">
            No skill candidates yet. Need ≥{sk.promotion_threshold} same-shape
            occurrences (event_type + touched-path-template) for promotion to{" "}
            <code className="rounded bg-[var(--color-bg)]/60 px-1 text-[var(--color-fg)]">
              06_skills.md
            </code>
            . Briefings register at ≥{sk.registry_threshold}.
          </p>
        </Card>
      ) : sk.candidates.length === 0 ? null : (
        <div className="grid gap-2">
          {sk.candidates.map((c) => (
            <Card key={c.slug}>
              <div className="flex items-start justify-between gap-3">
                <div className="flex flex-col gap-0.5">
                  <code className="font-mono text-[12px] font-medium text-[var(--color-fg)]">
                    {c.slug}
                  </code>
                  <span className="font-mono text-[11px] text-[var(--color-fg-muted)]">
                    event_type: {c.event_type} · last: {c.last_event_id}
                  </span>
                </div>
                <span className="rounded-md border border-[var(--color-border-2)] bg-[var(--color-bg)]/40 px-2 py-0.5 font-mono text-[11px] tabular-nums text-[var(--color-fg)]">
                  ×{c.occurrences}
                </span>
              </div>
              {c.path_templates.length > 0 && (
                <div className="mt-2.5">
                  <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-[var(--color-fg-dim)]">
                    paths
                  </span>
                  <ul className="mt-1 flex flex-col gap-0.5">
                    {c.path_templates.map((p) => (
                      <li
                        key={p}
                        className="font-mono text-[11px] text-[var(--color-fg-muted)]"
                      >
                        {p}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {c.sample_summaries.length > 0 && (
                <details className="mt-2.5">
                  <summary className="cursor-pointer font-mono text-[10px] uppercase tracking-[0.18em] text-[var(--color-fg-dim)] hover:text-[var(--color-fg)]">
                    samples ({c.sample_summaries.length})
                  </summary>
                  <ul className="mt-1.5 flex flex-col gap-1 border-l border-[var(--color-border)] pl-2.5">
                    {c.sample_summaries.map((s, i) => (
                      <li
                        key={i}
                        className="text-[12px] leading-relaxed text-[var(--color-fg-muted)]"
                      >
                        {s}
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </Card>
          ))}
        </div>
      )}
    </section>
  );
}

function ProposalsBlockView({ data }: { data: HermesDashboard }) {
  const p = data.proposals;
  return (
    <section className="flex flex-col gap-3">
      <SectionHeader
        icon={<Wand2 className="h-3.5 w-3.5" />}
        title="Outer loop · proposals"
        hint={`${p.total} pending`}
      />
      {Object.keys(p.by_kind).length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {Object.entries(p.by_kind).map(([k, n]) => (
            <span
              key={k}
              className="rounded-full border border-[var(--color-border-2)] bg-[var(--color-surface)] px-2.5 py-0.5 font-mono text-[11px] text-[var(--color-fg-muted)]"
            >
              {k} <span className="text-[var(--color-fg)]">×{n}</span>
            </span>
          ))}
        </div>
      )}
      {p.items.length === 0 ? (
        <Card>
          <p className="font-mono text-[12px] text-[var(--color-fg-muted)]">
            No proposals. Outer loop watches for repeated misses.
          </p>
        </Card>
      ) : (
        <div className="grid gap-2">
          {p.items.map((item, i) => (
            <Card key={`${item.kind}-${item.target}-${i}`}>
              <div className="flex items-start justify-between gap-3">
                <div className="flex flex-col gap-0.5">
                  <div className="flex items-center gap-2">
                    <span className="rounded-md bg-amber-500/10 px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.15em] text-amber-600 dark:text-amber-400">
                      {item.kind}
                    </span>
                    <code className="font-mono text-[12px] font-medium text-[var(--color-fg)]">
                      {item.target}
                    </code>
                  </div>
                  <p className="text-[12px] leading-relaxed text-[var(--color-fg-muted)]">
                    {item.rationale}
                  </p>
                </div>
                <span className="shrink-0 rounded-md border border-[var(--color-border-2)] bg-[var(--color-bg)]/40 px-2 py-0.5 font-mono text-[11px] tabular-nums text-[var(--color-fg)]">
                  ×{item.evidence_count}
                </span>
              </div>
              {item.evidence_event_ids.length > 0 && (
                <details className="mt-2.5">
                  <summary className="cursor-pointer font-mono text-[10px] uppercase tracking-[0.18em] text-[var(--color-fg-dim)] hover:text-[var(--color-fg)]">
                    evidence ({item.evidence_event_ids.length})
                  </summary>
                  <ul className="mt-1.5 flex flex-wrap gap-1">
                    {item.evidence_event_ids.map((e) => (
                      <li
                        key={e}
                        className="rounded border border-[var(--color-border)] bg-[var(--color-bg)]/40 px-1.5 py-0.5 font-mono text-[10.5px] text-[var(--color-fg-muted)]"
                      >
                        {e}
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </Card>
          ))}
        </div>
      )}
    </section>
  );
}

function ArtifactsBlock({ data }: { data: HermesDashboard }) {
  const a = data.artifacts;
  const items: { label: string; path: string | null; icon: React.ReactNode }[] =
    [
      {
        label: "skills.md",
        path: a.skills_md,
        icon: <Sparkles className="h-3 w-3" />,
      },
      {
        label: "proposals.md",
        path: a.proposals_md,
        icon: <FileWarning className="h-3 w-3" />,
      },
      {
        label: "feedback.jsonl",
        path: a.feedback_jsonl,
        icon: <GitBranch className="h-3 w-3" />,
      },
    ];
  return (
    <section className="flex flex-col gap-3">
      <SectionHeader
        icon={<AlertTriangle className="h-3.5 w-3.5" />}
        title="Artifacts"
        hint="on disk"
      />
      <Card>
        <ul className="flex flex-col gap-1.5">
          {items.map((it) => (
            <li
              key={it.label}
              className="flex items-center gap-2 font-mono text-[11.5px]"
            >
              <span className="text-[var(--color-fg-dim)]">{it.icon}</span>
              <span className="w-32 shrink-0 text-[var(--color-fg-muted)]">
                {it.label}
              </span>
              {it.path ? (
                <code className="truncate text-[var(--color-fg)]">{it.path}</code>
              ) : (
                <span className="italic text-[var(--color-fg-dim)]">
                  not generated yet
                </span>
              )}
            </li>
          ))}
        </ul>
      </Card>
    </section>
  );
}

function BlockSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="flex flex-col gap-3">
          <div className="h-3 w-40 animate-pulse rounded bg-[var(--color-surface)]" />
          <div className="h-24 animate-pulse rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)]/40" />
        </div>
      ))}
    </div>
  );
}
