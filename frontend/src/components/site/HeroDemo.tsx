import { useEffect, useState } from "react";
import { Check, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";

const STEPS = [
  "Searching products",
  "Comparing merchants",
  "Checking price against intent",
  "Verifying merchant reputation",
] as const;

export function HeroDemo() {
  const [step, setStep] = useState(0);

  useEffect(() => {
    const id = window.setInterval(() => {
      setStep((s) => (s >= STEPS.length + 2 ? 0 : s + 1));
    }, 1100);
    return () => window.clearInterval(id);
  }, []);

  const evaluating = step >= STEPS.length;
  const approved = step >= STEPS.length + 2;

  return (
    <div className="panel relative overflow-hidden p-5 sm:p-6" aria-live="polite">
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-px overflow-hidden"
        aria-hidden
      >
        <div className="h-px w-1/3 animate-sweep bg-primary/70" />
      </div>

      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">Shopping Agent</span>
        <span className="flex items-center gap-2 rounded-full bg-safe-muted px-2.5 py-1 text-[11px] font-medium tracking-wide text-safe">
          <span className="size-1.5 animate-pulse-dot rounded-full bg-safe" />
          LIVE
        </span>
      </div>

      <div className="mt-6">
        <p className="eyebrow">User intent</p>
        <p className="mt-2 rounded-lg border border-border bg-surface-raised px-3 py-2.5 font-mono text-sm text-foreground">
          “Buy laptop under ₹80,000”
        </p>
      </div>

      <div className="mt-6">
        <p className="eyebrow">Agent activity</p>
        <ul className="mt-3 space-y-2">
          {STEPS.map((label, i) => {
            const done = step > i;
            const active = step === i;
            return (
              <li
                key={label}
                className={cn(
                  "flex items-center gap-2.5 text-sm transition-colors duration-300",
                  done ? "text-foreground" : active ? "text-foreground" : "text-muted-foreground/50",
                )}
              >
                <span
                  className={cn(
                    "flex size-4 shrink-0 items-center justify-center rounded-full border transition-colors",
                    done
                      ? "border-safe bg-safe-muted text-safe"
                      : active
                        ? "border-primary text-primary"
                        : "border-border",
                  )}
                >
                  {done ? (
                    <Check className="size-2.5" />
                  ) : active ? (
                    <span className="size-1.5 animate-pulse-dot rounded-full bg-primary" />
                  ) : null}
                </span>
                {label}
              </li>
            );
          })}
        </ul>
      </div>

      <div className="mt-6 rounded-xl border border-border-strong bg-surface-raised p-4">
        <div className="flex items-center gap-2">
          <ShieldCheck className="size-4 text-primary" aria-hidden />
          <span className="text-xs font-semibold tracking-[0.16em] text-foreground">FINSHIELD</span>
        </div>
        <dl className="mt-4 space-y-3">
          <Metric
            label="Intent alignment"
            value={evaluating ? "97%" : "—"}
            tone="safe"
            fill={evaluating ? 97 : 0}
          />
          <Metric
            label="Transaction risk"
            value={evaluating ? "3%" : "—"}
            tone="info"
            fill={evaluating ? 3 : 0}
          />
          <div className="flex items-center justify-between text-sm">
            <dt className="text-muted-foreground">Policy status</dt>
            <dd
              className={cn(
                "font-mono text-xs font-medium",
                evaluating ? "text-safe" : "text-muted-foreground",
              )}
            >
              {evaluating ? "PASS" : "PENDING"}
            </dd>
          </div>
        </dl>
      </div>

      <div
        className={cn(
          "mt-4 flex items-center justify-center gap-2 rounded-xl border py-3 text-sm font-medium transition-all duration-500",
          approved
            ? "border-safe/40 bg-safe-muted text-safe"
            : "border-border bg-surface text-muted-foreground/60",
        )}
      >
        <Check className={cn("size-4 transition-opacity", approved ? "opacity-100" : "opacity-30")} />
        {approved ? "PAYMENT APPROVED" : "AWAITING DECISION"}
      </div>
    </div>
  );
}

function Metric({
  label,
  value,
  tone,
  fill,
}: {
  label: string;
  value: string;
  tone: "safe" | "info";
  fill: number;
}) {
  return (
    <div>
      <div className="flex items-center justify-between text-sm">
        <dt className="text-muted-foreground">{label}</dt>
        <dd className="font-mono text-xs text-foreground">{value}</dd>
      </div>
      <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-muted">
        <div
          className={cn(
            "h-full rounded-full transition-[width] duration-700 ease-out",
            tone === "safe" ? "bg-safe" : "bg-info",
          )}
          style={{ width: `${fill}%` }}
        />
      </div>
    </div>
  );
}
