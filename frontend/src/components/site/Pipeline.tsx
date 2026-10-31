import { useState } from "react";
import { cn } from "@/lib/utils";

const STAGES = [
  {
    key: "intent",
    label: "Intent",
    summary: "Capture what the user actually authorized.",
    detail:
      "The user instruction is parsed into a structured, signed intent: objective, budget ceiling, category, merchant constraints and validity window. Everything downstream is measured against this object, not against free text.",
  },
  {
    key: "agent",
    label: "Agent",
    summary: "Bind the agent to a scoped financial identity.",
    detail:
      "Each agent gets its own credentials, spending envelope and permission set. FINSHIELD models its normal behaviour so deviations — unusual tools, unusual merchants, unusual pacing — become measurable.",
  },
  {
    key: "trajectory",
    label: "Trajectory",
    summary: "Record every action and every external influence.",
    detail:
      "Tool calls, search results, page content and merchant responses form a trajectory graph. Injected instructions from external content are isolated and flagged as untrusted influence nodes.",
  },
  {
    key: "risk",
    label: "Risk",
    summary: "Score the transaction across five dimensions.",
    detail:
      "Transaction risk, agent risk, intent risk, merchant risk and behavioural risk are scored independently, then fused. Graph features surface merchant/account relationships a single-transaction model would miss.",
  },
  {
    key: "policy",
    label: "Policy",
    summary: "Apply deterministic financial constraints.",
    detail:
      "Limits, categories, geographies, merchant allow/block lists and approval thresholds are evaluated deterministically. Policy is never probabilistic — a hard limit is a hard limit.",
  },
  {
    key: "decision",
    label: "Decision",
    summary: "Allow, review or block — with evidence.",
    detail:
      "A single decision is emitted with the evidence chain attached: intent alignment score, contributing risk factors, policy results and the trajectory nodes that mattered. Every decision is replayable in the audit log.",
  },
] as const;

export function Pipeline() {
  const [active, setActive] = useState(0);
  const stage = STAGES[active] ?? STAGES[0];

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_1.1fr]">
      <ol className="space-y-1" role="tablist" aria-label="FINSHIELD pipeline stages">
        {STAGES.map((s, i) => (
          <li key={s.key}>
            <button
              type="button"
              role="tab"
              aria-selected={active === i}
              onMouseEnter={() => setActive(i)}
              onFocus={() => setActive(i)}
              onClick={() => setActive(i)}
              className={cn(
                "group flex w-full items-start gap-4 rounded-lg border px-4 py-3.5 text-left transition-colors",
                active === i
                  ? "border-primary/40 bg-accent"
                  : "border-transparent hover:bg-secondary",
              )}
            >
              <span
                className={cn(
                  "mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-md border font-mono text-[11px]",
                  active === i
                    ? "border-primary/50 bg-primary/15 text-primary"
                    : "border-border text-muted-foreground",
                )}
              >
                {i + 1}
              </span>
              <span>
                <span className="block text-sm font-medium text-foreground">{s.label}</span>
                <span className="mt-0.5 block text-sm text-muted-foreground">{s.summary}</span>
              </span>
            </button>
          </li>
        ))}
      </ol>

      <div className="panel h-fit p-6 lg:sticky lg:top-24">
        <p className="eyebrow">Stage {active + 1} / 6</p>
        <h3 className="mt-3 text-2xl font-semibold tracking-tight">{stage.label}</h3>
        <p className="mt-4 leading-relaxed text-muted-foreground">{stage.detail}</p>
        <div className="mt-6 flex flex-wrap gap-1.5">
          {STAGES.map((s, i) => (
            <span
              key={s.key}
              className={cn(
                "rounded-md px-2 py-1 font-mono text-[11px] transition-colors",
                i === active
                  ? "bg-primary/15 text-primary"
                  : i < active
                    ? "bg-secondary text-muted-foreground"
                    : "bg-secondary/50 text-muted-foreground/60",
              )}
            >
              {s.label.toLowerCase()}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
