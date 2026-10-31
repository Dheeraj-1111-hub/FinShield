import { CreditCard, Zap, ArrowUpRight } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { BILLING, INVOICES } from "@/data/mock-settings";

function UsageBar({ label, used, max }: { label: string; used: number; max: number }) {
  const pct = Math.round((used / max) * 100);
  const color = pct > 85 ? "bg-danger" : pct > 65 ? "bg-warn" : "bg-primary";
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="text-foreground font-medium">{label}</span>
        <span className="font-mono text-muted-foreground">
          {used.toLocaleString()} / {max.toLocaleString()}
        </span>
      </div>
      <div className="h-2 bg-muted rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <div className="text-xs text-muted-foreground text-right">{pct}% used</div>
    </div>
  );
}

export function BillingPanel() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-foreground mb-0.5">Billing</h2>
        <p className="text-sm text-muted-foreground">Your FINSHIELD subscription and usage.</p>
      </div>

      {/* Current Plan */}
      <Card className="border-border bg-surface p-6">
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4">Current Plan</div>
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-3">
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-black text-foreground">{BILLING.plan}</span>
              <span className="text-xl font-bold text-muted-foreground">{BILLING.price} / month</span>
            </div>
            <ul className="space-y-1.5">
              {BILLING.features.map(f => (
                <li key={f} className="flex items-center gap-2 text-sm text-muted-foreground">
                  <div className="size-1.5 rounded-full bg-muted-foreground/50" />
                  {f}
                </li>
              ))}
            </ul>
          </div>
          <Button className="bg-primary hover:bg-primary/90 text-primary-foreground shrink-0 gap-2">
            Upgrade plan <ArrowUpRight className="size-4" />
          </Button>
        </div>
      </Card>

      {/* Usage */}
      <Card className="border-border bg-surface p-6 space-y-6">
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Current Usage</div>
        <UsageBar label="Protected actions" used={BILLING.usage.protectedActions.used} max={BILLING.usage.protectedActions.max} />
        <UsageBar label="API requests"      used={BILLING.usage.apiRequests.used}      max={BILLING.usage.apiRequests.max} />
        <UsageBar label="Agents"            used={BILLING.usage.agents.used}           max={BILLING.usage.agents.max} />
      </Card>

      {/* Invoices */}
      <Card className="border-border bg-surface overflow-hidden">
        <div className="px-6 py-4 border-b border-border text-xs font-semibold text-muted-foreground uppercase tracking-wider">
          Invoices
        </div>
        <div className="divide-y divide-border">
          {INVOICES.map((inv, i) => (
            <div key={i} className="px-6 py-4 grid grid-cols-[auto_1fr_auto_auto] gap-4 items-center text-sm">
              <span className="text-muted-foreground font-mono w-16">{inv.date}</span>
              <span className="text-foreground">{inv.description}</span>
              <span className="font-mono font-semibold text-foreground">{inv.amount}</span>
              <span className="text-xs px-2 py-0.5 rounded-md bg-safe/10 border border-safe/20 text-safe font-bold">{inv.status}</span>
            </div>
          ))}
        </div>
      </Card>

      {/* Payment Method */}
      <Card className="border-border bg-surface p-6 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="size-10 rounded-xl bg-muted border border-border flex items-center justify-center">
            <CreditCard className="size-5 text-muted-foreground" />
          </div>
          <div>
            <div className="font-medium text-foreground text-sm">Payment method</div>
            <div className="text-xs text-muted-foreground">No payment method required for Free plan.</div>
          </div>
        </div>
        <Button variant="outline" className="border-border bg-background shrink-0">Add payment method</Button>
      </Card>
    </div>
  );
}
