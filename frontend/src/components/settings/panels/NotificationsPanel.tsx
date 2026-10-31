import { useState } from "react";
import { Card } from "@/components/ui/card";
import { DEFAULT_NOTIFICATIONS } from "@/data/mock-settings";

function Toggle({ checked, onChange, disabled }: { checked: boolean; onChange: () => void; disabled?: boolean }) {
  return (
    <button
      onClick={onChange}
      disabled={disabled}
      className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 disabled:opacity-50 ${checked ? "bg-primary" : "bg-muted-foreground/30"}`}
    >
      <span className={`pointer-events-none inline-block size-4 rounded-full bg-white shadow transition-transform duration-200 ${checked ? "translate-x-4" : "translate-x-0"}`} />
    </button>
  );
}

function ToggleRow({ label, desc, checked, onChange }: { label: string; desc?: string; checked: boolean; onChange: () => void }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-border last:border-0 gap-4">
      <div>
        <div className="text-sm font-medium text-foreground">{label}</div>
        {desc && <div className="text-xs text-muted-foreground mt-0.5">{desc}</div>}
      </div>
      <Toggle checked={checked} onChange={onChange} />
    </div>
  );
}

const ESCALATION_ROWS = [
  { label: "Critical alerts",       timing: "Immediately" },
  { label: "High-risk alerts",      timing: "Within 5 minutes" },
  { label: "Informational events",  timing: "Daily digest" },
];

export function NotificationsPanel({ data, onChange }: { data?: any, onChange?: (domain: string, field: string, value: any) => void }) {
  // Merge defaults with backend prefs
  const backendPrefs = data?.prefs?.notification_preferences || {};
  const notifs = {
    ...DEFAULT_NOTIFICATIONS,
    ...backendPrefs,
    security: { ...DEFAULT_NOTIFICATIONS.security, ...(backendPrefs.security || {}) },
    risk: { ...DEFAULT_NOTIFICATIONS.risk, ...(backendPrefs.risk || {}) },
    platform: { ...DEFAULT_NOTIFICATIONS.platform, ...(backendPrefs.platform || {}) },
    delivery: { ...DEFAULT_NOTIFICATIONS.delivery, ...(backendPrefs.delivery || {}) }
  };
  const toggleKey = (group: keyof typeof notifs, key: string) => {
    const g = notifs[group];
    if (typeof g === "object" && typeof (g as Record<string, boolean>)[key] === "boolean") {
      const newNotifs = { ...notifs, [group]: { ...(notifs[group] as Record<string, boolean>), [key]: !(notifs[group] as Record<string, boolean>)[key] } };
      onChange?.("prefs", "notification_preferences", newNotifs);
    }
  };

  const updateNumber = (key: string, value: string) => {
    const num = Number(value);
    if (!isNaN(num)) {
      onChange?.("prefs", "notification_preferences", { ...notifs, [key]: num });
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-foreground mb-0.5">Notifications</h2>
        <p className="text-sm text-muted-foreground">Choose which events FINSHIELD should surface.</p>
      </div>

      {/* Security */}
      <Card className="border-border bg-surface p-6">
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Security</div>
        <ToggleRow label="Critical security events"    checked={notifs.security.critical_security} onChange={() => toggleKey("security", "critical_security")} />
        <ToggleRow label="Suspicious agent behavior"  checked={notifs.security.suspicious_agent}   onChange={() => toggleKey("security", "suspicious_agent")} />
        <ToggleRow label="Failed authentication"      checked={notifs.security.failed_auth}        onChange={() => toggleKey("security", "failed_auth")} />
        <ToggleRow label="API key changes"            checked={notifs.security.api_key_changes}    onChange={() => toggleKey("security", "api_key_changes")} />
      </Card>

      {/* Risk & Financial */}
      <Card className="border-border bg-surface p-6">
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Risk & Financial</div>
        <ToggleRow label="High-risk transaction"   checked={notifs.risk.high_risk_tx}         onChange={() => toggleKey("risk", "high_risk_tx")} />
        <ToggleRow label="Payment blocked"         checked={notifs.risk.payment_blocked}       onChange={() => toggleKey("risk", "payment_blocked")} />
        <ToggleRow label="Policy review required"  checked={notifs.risk.policy_review}         onChange={() => toggleKey("risk", "policy_review")} />
        <ToggleRow label="Investigation opened"    checked={notifs.risk.investigation_opened}  onChange={() => toggleKey("risk", "investigation_opened")} />
      </Card>

      {/* Platform */}
      <Card className="border-border bg-surface p-6">
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Platform</div>
        <ToggleRow label="System incidents"       checked={notifs.platform.system_incidents} onChange={() => toggleKey("platform", "system_incidents")} />
        <ToggleRow label="API degradation"        checked={notifs.platform.api_degradation}  onChange={() => toggleKey("platform", "api_degradation")} />
        <ToggleRow label="Scheduled maintenance"  checked={notifs.platform.maintenance}      onChange={() => toggleKey("platform", "maintenance")} />
        <ToggleRow label="Product updates"        checked={notifs.platform.product_updates}  onChange={() => toggleKey("platform", "product_updates")} />
      </Card>

      {/* Delivery */}
      <Card className="border-border bg-surface p-6">
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Delivery</div>
        <ToggleRow label="Email"    desc="user@finshield.dev"                     checked={notifs.delivery.email}   onChange={() => toggleKey("delivery", "email")} />
        <ToggleRow label="In-app"   desc="FINSHIELD notifications"                checked={notifs.delivery.in_app}  onChange={() => toggleKey("delivery", "in_app")} />
        <ToggleRow label="Webhook"  desc="Use workspace webhook configuration"    checked={notifs.delivery.webhook} onChange={() => toggleKey("delivery", "webhook")} />
      </Card>

      {/* Risk Alert Thresholds */}
      <Card className="border-border bg-surface p-6 space-y-5">
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Risk Alert Thresholds</div>

        <div>
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium text-foreground">Risk score exceeds</span>
            <span className="text-sm font-bold font-mono text-primary">{notifs.riskThreshold}</span>
          </div>
          <input
            type="range" min={0} max={100} value={notifs.riskThreshold}
            onChange={e => updateNumber("riskThreshold", e.target.value)}
            className="w-full h-1.5 bg-muted rounded-full appearance-none cursor-pointer accent-primary"
          />
          <div className="flex justify-between text-xs text-muted-foreground mt-1">
            <span>0</span><span>50</span><span>100</span>
          </div>
        </div>

        <div>
          <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-2">Transaction exceeds (₹)</label>
          <input type="number" value={notifs.txThreshold} onChange={e => updateNumber("txThreshold", e.target.value)}
            className="w-full max-w-xs bg-background border border-border rounded-lg px-3 py-2.5 text-sm text-foreground font-mono focus:outline-none focus:ring-2 focus:ring-primary/40" />
        </div>

        <div>
          <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-2">Daily agent exposure exceeds (₹)</label>
          <input type="number" value={notifs.dailyThreshold} onChange={e => updateNumber("dailyThreshold", e.target.value)}
            className="w-full max-w-xs bg-background border border-border rounded-lg px-3 py-2.5 text-sm text-foreground font-mono focus:outline-none focus:ring-2 focus:ring-primary/40" />
        </div>
      </Card>

      {/* Escalation */}
      <Card className="border-border bg-surface overflow-hidden">
        <div className="px-6 py-4 border-b border-border text-xs font-semibold text-muted-foreground uppercase tracking-wider">Escalation</div>
        <div className="divide-y divide-border">
          {ESCALATION_ROWS.map(row => (
            <div key={row.label} className="px-6 py-4 flex items-center justify-between text-sm">
              <span className="text-muted-foreground">{row.label}</span>
              <span className="font-medium text-foreground">{row.timing}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
