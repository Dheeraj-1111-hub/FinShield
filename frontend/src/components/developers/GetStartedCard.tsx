import { Key, Bot, Webhook, Zap, ArrowRight } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { API_KEYS } from "@/data/mock-developers";

const STEPS = [
  { icon: Key,     label: "Create credentials",  desc: "Generate a scoped API key" },
  { icon: Bot,     label: "Register agent",       desc: "Define identity, capabilities and authority" },
  { icon: Webhook, label: "Configure webhooks",   desc: "Receive real-time FINSHIELD events" },
  { icon: Zap,     label: "Protect actions",      desc: "Route financial actions through the policy engine" },
];

export function GetStartedCard() {
  // Step 0 complete if there's at least one key
  const keysExist = API_KEYS.length > 0;
  const completedStep = keysExist ? 1 : 0;

  return (
    <Card className="p-6 border-border bg-surface shadow-sm">
      <div className="flex items-start justify-between gap-4 mb-6">
        <div>
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">Get Started</div>
          <h2 className="text-xl font-bold text-foreground">Connect an Agent</h2>
          <p className="text-sm text-muted-foreground mt-1">Bring your autonomous agent under FINSHIELD protection.</p>
        </div>
        <Button className="shrink-0 bg-primary hover:bg-primary/90 text-primary-foreground gap-2">
          Start integration <ArrowRight className="size-4" />
        </Button>
      </div>

      {/* Progress track */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        {STEPS.map((step, i) => {
          const done    = i < completedStep;
          const current = i === completedStep;
          const Icon    = step.icon;
          return (
            <div key={i} className="relative">
              {/* connector */}
              {i < STEPS.length - 1 && (
                <div className={`hidden sm:block absolute top-5 left-[calc(50%+20px)] right-[-50%] h-px ${done ? "bg-primary/40" : "bg-border"} z-0`} />
              )}
              <div className={`relative z-10 flex flex-col items-center text-center p-4 rounded-xl border transition-colors ${
                done    ? "border-primary/30 bg-primary/8"    :
                current ? "border-primary/40 bg-primary/12 ring-1 ring-primary/20" :
                          "border-border bg-muted"
              }`}>
                <div className={`size-10 rounded-full flex items-center justify-center mb-3 ${
                  done    ? "bg-primary/20 text-primary" :
                  current ? "bg-primary/20 text-primary" :
                            "bg-muted-foreground/10 text-muted-foreground"
                }`}>
                  {done ? (
                    <svg className="size-5 text-primary" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}>
                      <path d="M20 6L9 17l-5-5" />
                    </svg>
                  ) : (
                    <Icon className="size-5" />
                  )}
                </div>
                <div className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-1">{String(i + 1).padStart(2, "0")}</div>
                <div className={`text-sm font-semibold mb-1 ${current || done ? "text-foreground" : "text-muted-foreground"}`}>{step.label}</div>
                <div className="text-xs text-muted-foreground">{step.desc}</div>
                {done && <div className="mt-2 text-xs text-safe font-medium">✓ Complete</div>}
                {current && <div className="mt-2 text-xs text-primary font-medium animate-pulse">→ Next step</div>}
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
