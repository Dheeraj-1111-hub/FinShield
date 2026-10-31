import { useState } from "react";
import { ArrowRight, ChevronDown, Check } from "lucide-react";
import { Card } from "@/components/ui/card";
import { useNavigate } from "@tanstack/react-router";

function Toggle({ checked, onChange }: { checked: boolean; onChange: () => void }) {
  return (
    <button onClick={onChange}
      className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ${checked ? "bg-primary" : "bg-muted-foreground/30"}`}>
      <span className={`pointer-events-none inline-block size-4 rounded-full bg-white shadow transition-transform duration-200 ${checked ? "translate-x-4" : "translate-x-0"}`} />
    </button>
  );
}

const EXPIRY_OPTIONS = ["30 days", "60 days", "90 days", "180 days", "1 year"];
const MAX_EXPIRY_OPTIONS = ["90 days", "180 days", "1 year", "2 years"];

function SelectInline({ options, value, onChange }: { options: string[]; value: string; onChange: (v: string) => void }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative">
      <button onClick={() => setOpen(o => !o)}
        className="flex items-center gap-2 bg-background border border-border rounded-lg px-3 py-1.5 text-sm text-foreground hover:border-border-strong transition-colors">
        {value} <ChevronDown className="size-3.5 text-muted-foreground" />
      </button>
      {open && (
        <div className="absolute z-10 right-0 top-full mt-1 w-36 bg-popover border border-border rounded-lg shadow-xl overflow-hidden">
          {options.map(o => (
            <button key={o} onClick={() => { onChange(o); setOpen(false); }}
              className={`w-full text-left px-3 py-2 text-sm hover:bg-muted flex items-center justify-between ${o === value ? "text-primary font-medium" : "text-foreground"}`}>
              {o} {o === value && <Check className="size-3" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function ToggleRow({ label, desc, checked, onChange }: { label: string; desc?: string; checked: boolean; onChange: () => void }) {
  return (
    <div className="flex items-center justify-between py-4 border-b border-border last:border-0 gap-4">
      <div>
        <div className="text-sm font-medium text-foreground">{label}</div>
        {desc && <div className="text-xs text-muted-foreground mt-0.5">{desc}</div>}
      </div>
      <Toggle checked={checked} onChange={onChange} />
    </div>
  );
}

function InlineRow({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div className="flex items-center justify-between py-4 border-b border-border last:border-0 gap-4">
      <span className="text-sm text-muted-foreground">{label}</span>
      <SelectInline options={EXPIRY_OPTIONS} value={value} onChange={onChange} />
    </div>
  );
}

export function ApiAccessPanel() {
  const navigate = useNavigate();
  const [signedWebhooks, setSignedWebhooks]   = useState(true);
  const [keyRotation, setKeyRotation]         = useState(true);
  const [preventNoExpiry, setPreventNoExpiry] = useState(true);
  const [defaultExpiry, setDefaultExpiry]     = useState("90 days");
  const [maxExpiry, setMaxExpiry]             = useState("1 year");
  const [blockUnknownAgents, setBlockUnknown] = useState(true);
  const [blockUnknownWebhooks, setBlockUW]    = useState(true);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-foreground mb-0.5">API & Access</h2>
        <p className="text-sm text-muted-foreground">Workspace authentication and access defaults.</p>
      </div>

      {/* API Security */}
      <Card className="border-border bg-surface p-6">
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">API Security</div>
        <ToggleRow label="Require signed webhook requests" desc="Reject webhook deliveries without valid HMAC-SHA256 signatures." checked={signedWebhooks} onChange={() => setSignedWebhooks(v => !v)} />
        <ToggleRow label="Require API key rotation"        desc="Enforce periodic key rotation for all workspace API keys."         checked={keyRotation}   onChange={() => setKeyRotation(v => !v)} />
        <ToggleRow label="Prevent keys without expiration" desc="Block creation of API keys that never expire."                     checked={preventNoExpiry} onChange={() => setPreventNoExpiry(v => !v)} />

        <div className="pt-4 space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Default key expiration</span>
            <SelectInline options={EXPIRY_OPTIONS} value={defaultExpiry} onChange={setDefaultExpiry} />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Maximum key lifetime</span>
            <SelectInline options={MAX_EXPIRY_OPTIONS} value={maxExpiry} onChange={setMaxExpiry} />
          </div>
        </div>
      </Card>

      {/* Access Control */}
      <Card className="border-border bg-surface p-6">
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">Access Control</div>
        <ToggleRow
          label="API requests from unknown agents"
          desc="Require agent registration before accepting API requests."
          checked={blockUnknownAgents} onChange={() => setBlockUnknown(v => !v)}
        />
        <ToggleRow
          label="Unknown webhook destinations"
          desc="Block event delivery to unregistered webhook endpoints."
          checked={blockUnknownWebhooks} onChange={() => setBlockUW(v => !v)}
        />
      </Card>

      {/* Link to Developer Portal */}
      <button
        onClick={() => navigate({ to: "/app/developers" })}
        className="flex items-center gap-2 text-sm text-primary hover:underline font-medium w-full text-left"
      >
        Manage API keys in Developer Portal <ArrowRight className="size-4" />
      </button>
    </div>
  );
}
