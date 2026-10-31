import { useCallback, useEffect, useRef, useState } from "react";
import { AlertTriangle, Ban, Check, Play, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type Tone = "safe" | "warn" | "danger" | "muted";

type Event = { label: string; detail: string; tone: Tone };

const SAFE_RUN: Event[] = [
  { label: "Intent created", detail: "Buy laptop · ceiling ₹80,000 · category electronics", tone: "safe" },
  { label: "Search initiated", detail: "4 merchants queried", tone: "muted" },
  { label: "37 products found", detail: "8 satisfy budget and category constraints", tone: "muted" },
  { label: "Merchant reputation checked", detail: "Merchant trust score 0.92", tone: "safe" },
  { label: "Product selected", detail: "Dell Inspiron 14 · ₹74,999", tone: "muted" },
  { label: "FINSHIELD evaluation", detail: "Intent alignment 97% · risk 3% · policy PASS", tone: "safe" },
  { label: "Payment approved", detail: "PAY-48291 captured · order created", tone: "safe" },
];

const ATTACK_RUN: Event[] = [
  { label: "Intent created", detail: "Buy laptop · ceiling ₹80,000 · category electronics", tone: "safe" },
  { label: "Search initiated", detail: "4 merchants queried", tone: "muted" },
  {
    label: "External instruction detected",
    detail: "Merchant page contains injected directive targeting the agent",
    tone: "warn",
  },
  { label: "Agent behaviour changed", detail: "Category switched to gift cards · basket ₹1,50,000", tone: "warn" },
  { label: "Intent drift measured", detail: "Intent alignment dropped to 14%", tone: "danger" },
  { label: "Policy violation", detail: "Max transaction ₹80,000 exceeded · category not permitted", tone: "danger" },
  { label: "Payment blocked", detail: "INV-18291 opened · trajectory preserved for review", tone: "danger" },
];

export function AttackDemo() {
  const [mode, setMode] = useState<"safe" | "attack">("safe");
  const [count, setCount] = useState(0);
  const [running, setRunning] = useState(false);
  const timer = useRef<number | null>(null);

  const events = mode === "safe" ? SAFE_RUN : ATTACK_RUN;

  const stop = useCallback(() => {
    if (timer.current) window.clearInterval(timer.current);
    timer.current = null;
  }, []);

  useEffect(() => stop, [stop]);

  const run = (next: "safe" | "attack") => {
    stop();
    setMode(next);
    setCount(0);
    setRunning(true);
    const list = next === "safe" ? SAFE_RUN : ATTACK_RUN;
    timer.current = window.setInterval(() => {
      setCount((c) => {
        if (c >= list.length - 1) {
          stop();
          setRunning(false);
          return list.length;
        }
        return c + 1;
      });
    }, 750);
    setCount(1);
  };

  const reset = () => {
    stop();
    setRunning(false);
    setCount(0);
  };

  const finished = count >= events.length;

  return (
    <div className="grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
      <div className="panel h-fit p-6">
        <p className="eyebrow">Try the workflow</p>
        <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
          Run the same user instruction twice — once in a clean environment, once against a merchant
          page carrying an injected instruction.
        </p>
        <p className="mt-4 rounded-lg border border-border bg-surface-raised px-3 py-2.5 font-mono text-sm">
          “Buy laptop under ₹80,000”
        </p>
        <div className="mt-5 flex flex-col gap-2">
          <Button onClick={() => run("safe")} disabled={running}>
            <Play className="size-4" /> Run legitimate purchase
          </Button>
          <Button onClick={() => run("attack")} disabled={running} variant="destructive">
            <AlertTriangle className="size-4" /> Run under attack
          </Button>
          <Button onClick={reset} variant="ghost" size="sm" disabled={running || count === 0}>
            <RotateCcw className="size-4" /> Reset
          </Button>
        </div>
      </div>

      <div className="panel min-h-[420px] p-6">
        <div className="flex items-center justify-between border-b border-border pb-4">
          <span className="text-sm font-medium">Agent activity timeline</span>
          <span
            className={cn(
              "rounded-full px-2.5 py-1 font-mono text-[11px]",
              running
                ? "bg-info-muted text-info"
                : finished && mode === "attack"
                  ? "bg-danger-muted text-danger"
                  : finished
                    ? "bg-safe-muted text-safe"
                    : "bg-secondary text-muted-foreground",
            )}
          >
            {running ? "RUNNING" : finished ? (mode === "attack" ? "BLOCKED" : "APPROVED") : "IDLE"}
          </span>
        </div>

        {count === 0 ? (
          <p className="py-16 text-center text-sm text-muted-foreground">
            No run yet. Launch a scenario to watch the agent act and FINSHIELD decide.
          </p>
        ) : (
          <ol className="mt-5 space-y-3">
            {events.slice(0, count).map((e, i) => (
              <li key={e.label} className="flex animate-rise gap-3" style={{ animationDelay: `${i * 20}ms` }}>
                <Dot tone={e.tone} />
                <div className="min-w-0">
                  <p className="text-sm font-medium text-foreground">{e.label}</p>
                  <p className="mt-0.5 font-mono text-xs text-muted-foreground">{e.detail}</p>
                </div>
              </li>
            ))}
          </ol>
        )}

        {finished ? (
          <div
            className={cn(
              "mt-6 flex animate-rise items-center gap-3 rounded-xl border p-4",
              mode === "attack"
                ? "border-danger/40 bg-danger-muted text-danger"
                : "border-safe/40 bg-safe-muted text-safe",
            )}
          >
            {mode === "attack" ? <Ban className="size-5" /> : <Check className="size-5" />}
            <div>
              <p className="text-sm font-semibold">
                {mode === "attack" ? "Transaction blocked" : "Payment approved"}
              </p>
              <p className="mt-0.5 text-xs opacity-80">
                {mode === "attack"
                  ? "Intent alignment 14% · budget exceeded · injected instruction identified"
                  : "Intent alignment 97% · risk 3% · every policy satisfied"}
              </p>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function Dot({ tone }: { tone: Tone }) {
  return (
    <span className="relative flex w-4 shrink-0 justify-center">
      <span
        className={cn(
          "mt-1.5 size-2 rounded-full",
          tone === "safe" && "bg-safe",
          tone === "warn" && "bg-warn",
          tone === "danger" && "bg-danger",
          tone === "muted" && "bg-muted-foreground/50",
        )}
      />
    </span>
  );
}
