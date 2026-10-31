import { useState } from "react";
import { Download, Check, ChevronDown } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

function Toggle({ checked, onChange }: { checked: boolean; onChange: () => void }) {
  return (
    <button onClick={onChange}
      className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ${checked ? "bg-primary" : "bg-muted-foreground/30"}`}>
      <span className={`pointer-events-none inline-block size-4 rounded-full bg-white shadow transition-transform duration-200 ${checked ? "translate-x-4" : "translate-x-0"}`} />
    </button>
  );
}

const RETENTION_OPTIONS = ["7 days", "30 days", "60 days", "90 days", "180 days", "1 year"];

function RetentionSelect({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="flex items-center justify-between py-3 border-b border-border last:border-0 gap-4">
      <span className="text-sm text-muted-foreground">{label}</span>
      <div className="relative">
        <button onClick={() => setOpen(o => !o)}
          className="flex items-center gap-2 bg-background border border-border rounded-lg px-3 py-1.5 text-sm text-foreground hover:border-border-strong transition-colors">
          {value} <ChevronDown className="size-3.5 text-muted-foreground" />
        </button>
        {open && (
          <div className="absolute z-10 right-0 top-full mt-1 w-32 bg-popover border border-border rounded-lg shadow-xl overflow-hidden">
            {RETENTION_OPTIONS.map(o => (
              <button key={o} onClick={() => { onChange(o); setOpen(false); }}
                className={`w-full text-left px-3 py-2 text-sm hover:bg-muted flex items-center justify-between ${o === value ? "text-primary font-medium" : "text-foreground"}`}>
                {o} {o === value && <Check className="size-3" />}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

const EXPORT_ITEMS = [
  { id: "audit",        label: "Audit events",       defaultChecked: true },
  { id: "investigations", label: "Investigations",    defaultChecked: true },
  { id: "agent",        label: "Agent activity",      defaultChecked: true },
  { id: "policy",       label: "Policy decisions",    defaultChecked: true },
  { id: "credentials",  label: "API credentials",     defaultChecked: false, disabled: true },
];

export function DataPrivacyPanel() {
  const [auditRet, setAuditRet]     = useState("90 days");
  const [invRet, setInvRet]         = useState("90 days");
  const [apiRet, setApiRet]         = useState("30 days");
  const [telemetry, setTelemetry]   = useState(true);
  const [aiAnalysis, setAiAnalysis] = useState(true);
  const [exports, setExports]       = useState<Record<string, boolean>>(
    Object.fromEntries(EXPORT_ITEMS.map(i => [i.id, i.defaultChecked]))
  );
  const [exported, setExported]     = useState(false);

  const handleExport = () => {
    setExported(true);
    setTimeout(() => setExported(false), 3000);
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-foreground mb-0.5">Data & Privacy</h2>
        <p className="text-sm text-muted-foreground">Control how FINSHIELD stores and processes workspace data.</p>
      </div>

      {/* Retention */}
      <Card className="border-border bg-surface p-6">
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Audit Retention</div>
        <RetentionSelect label="Audit events"      value={auditRet} onChange={setAuditRet} />
        <RetentionSelect label="Investigations"    value={invRet}   onChange={setInvRet} />
        <RetentionSelect label="API requests"      value={apiRet}   onChange={setApiRet} />
      </Card>

      {/* Processing */}
      <Card className="border-border bg-surface p-6 space-y-0 divide-y divide-border">
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider pb-3">Data Processing</div>
        <div className="flex items-center justify-between py-4 gap-4">
          <div>
            <div className="text-sm font-medium text-foreground">Agent telemetry</div>
            <div className="text-xs text-muted-foreground mt-0.5">Collect performance and behavior metrics from connected agents.</div>
          </div>
          <Toggle checked={telemetry} onChange={() => setTelemetry(v => !v)} />
        </div>
        <div className="flex items-center justify-between py-4 gap-4">
          <div>
            <div className="text-sm font-medium text-foreground">AI-assisted analysis</div>
            <div className="text-xs text-muted-foreground mt-0.5">Use AI models to analyze events, investigations, and agent behavior.</div>
          </div>
          <Toggle checked={aiAnalysis} onChange={() => setAiAnalysis(v => !v)} />
        </div>
      </Card>

      {/* Export */}
      <Card className="border-border bg-surface p-6 space-y-5">
        <div>
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-0.5">Data Export</div>
          <p className="text-xs text-muted-foreground">Export workspace data. API credentials are never included.</p>
        </div>
        <div className="space-y-2">
          {EXPORT_ITEMS.map(item => (
            <label key={item.id} className={`flex items-center gap-3 p-3 rounded-lg border border-border bg-muted ${item.disabled ? "opacity-50" : "cursor-pointer hover:border-border-strong"} transition-colors`}>
              <div className={`size-4 rounded border-2 flex items-center justify-center shrink-0 ${exports[item.id] && !item.disabled ? "bg-primary border-primary" : "border-muted-foreground/30"}`}>
                {exports[item.id] && !item.disabled && <Check className="size-3 text-primary-foreground" strokeWidth={3} />}
              </div>
              <input type="checkbox" className="sr-only" checked={!!exports[item.id]} disabled={item.disabled}
                onChange={() => !item.disabled && setExports(e => ({ ...e, [item.id]: !e[item.id] }))} />
              <span className="text-sm text-foreground">{item.label}</span>
              {item.disabled && <span className="ml-auto text-xs text-muted-foreground">Never exported</span>}
            </label>
          ))}
        </div>
        <Button
          className={`gap-2 ${exported ? "bg-safe/15 text-safe border-safe/20" : "bg-primary hover:bg-primary/90 text-primary-foreground"}`}
          variant={exported ? "outline" : "default"}
          onClick={handleExport}
        >
          {exported ? <><Check className="size-4" /> Export queued</> : <><Download className="size-4" /> Export data</>}
        </Button>
      </Card>
    </div>
  );
}
