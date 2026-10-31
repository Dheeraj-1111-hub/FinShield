import { useState } from "react";
import { Key, Copy, Check, X, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Props {
  open: boolean;
  onClose: () => void;
}

const PERMISSIONS = [
  { id: "agent_actions",       label: "Agent actions",        desc: "Evaluate and execute agent actions" },
  { id: "policy_eval",         label: "Policy evaluation",    desc: "Query the policy engine" },
  { id: "policy_admin",        label: "Policy administration",desc: "Create and modify policies" },
  { id: "audit_read",          label: "Audit read",           desc: "Read audit log events" },
  { id: "investigation_read",  label: "Investigation read",   desc: "View investigation reports" },
];

const EXPIRATIONS = ["30 days", "60 days", "90 days", "180 days", "1 year", "Never"];

export function CreateApiKeyModal({ open, onClose }: Props) {
  const [name, setName]           = useState("");
  const [env, setEnv]             = useState<"Sandbox" | "Production">("Sandbox");
  const [perms, setPerms]         = useState<Record<string, boolean>>({ agent_actions: true, policy_eval: true });
  const [expiry, setExpiry]       = useState("90 days");
  const [showExpiry, setShowExpiry] = useState(false);
  const [created, setCreated]     = useState(false);
  const [secret]                  = useState("fs_sbx_a7f3c9d2e1b8044f6a2c890d3e1f4b5c");
  const [copied, setCopied]       = useState(false);

  if (!open) return null;

  const togglePerm = (id: string) =>
    setPerms(p => ({ ...p, [id]: !p[id] }));

  const handleCreate = () => {
    if (!name.trim()) return;
    setCreated(true);
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(secret).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleClose = () => {
    setName(""); setEnv("Sandbox"); setPerms({ agent_actions: true, policy_eval: true });
    setExpiry("90 days"); setCreated(false); setCopied(false);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={handleClose}>
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      <div
        className="relative w-full max-w-lg bg-surface border border-border rounded-2xl shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-6 pb-4 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="size-8 rounded-lg bg-primary/15 flex items-center justify-center">
              <Key className="size-4 text-primary" />
            </div>
            <h2 className="text-lg font-bold text-foreground">
              {created ? "API Key Created" : "Create API Key"}
            </h2>
          </div>
          <button onClick={handleClose} className="text-muted-foreground hover:text-foreground transition-colors">
            <X className="size-5" />
          </button>
        </div>

        {!created ? (
          /* ── CREATE FORM ── */
          <div className="p-6 space-y-5">
            {/* Name */}
            <div>
              <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-2">Name</label>
              <input
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="e.g. Production Finance Agent"
                className="w-full bg-muted border border-border rounded-lg px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
            </div>

            {/* Environment */}
            <div>
              <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-2">Environment</label>
              <div className="flex gap-3">
                {(["Sandbox", "Production"] as const).map(e => (
                  <label key={e} className={`flex items-center gap-2.5 flex-1 px-4 py-3 rounded-lg border cursor-pointer transition-colors ${
                    env === e
                      ? "border-primary/50 bg-primary/10 text-primary"
                      : "border-border bg-muted text-muted-foreground hover:border-border-strong"
                  }`}>
                    <div className={`size-4 rounded-full border-2 flex items-center justify-center shrink-0 ${env === e ? "border-primary" : "border-muted-foreground/40"}`}>
                      {env === e && <div className="size-2 rounded-full bg-primary" />}
                    </div>
                    <input type="radio" className="sr-only" checked={env === e} onChange={() => setEnv(e)} />
                    <span className="text-sm font-medium">{e}</span>
                  </label>
                ))}
              </div>
              {env === "Production" && (
                <p className="text-xs text-warn mt-2">⚠ Production keys authenticate against live data and real financial actions.</p>
              )}
            </div>

            {/* Permissions */}
            <div>
              <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-2">Permissions</label>
              <div className="space-y-2">
                {PERMISSIONS.map(p => (
                  <label key={p.id} className="flex items-start gap-3 p-3 rounded-lg border border-border bg-muted cursor-pointer hover:border-border-strong transition-colors">
                    <div className={`size-4 rounded border-2 flex items-center justify-center shrink-0 mt-0.5 transition-colors ${perms[p.id] ? "bg-primary border-primary" : "border-muted-foreground/40"}`}>
                      {perms[p.id] && <Check className="size-3 text-primary-foreground" strokeWidth={3} />}
                    </div>
                    <input type="checkbox" className="sr-only" checked={!!perms[p.id]} onChange={() => togglePerm(p.id)} />
                    <div>
                      <div className="text-sm font-medium text-foreground">{p.label}</div>
                      <div className="text-xs text-muted-foreground">{p.desc}</div>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {/* Expiration */}
            <div>
              <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-2">Expiration</label>
              <div className="relative">
                <button
                  onClick={() => setShowExpiry(s => !s)}
                  className="w-full flex items-center justify-between bg-muted border border-border rounded-lg px-3 py-2.5 text-sm text-foreground hover:border-border-strong transition-colors"
                >
                  {expiry} <ChevronDown className="size-4 text-muted-foreground" />
                </button>
                {showExpiry && (
                  <div className="absolute z-10 top-full mt-1 w-full bg-popover border border-border rounded-lg shadow-xl overflow-hidden">
                    {EXPIRATIONS.map(e => (
                      <button
                        key={e}
                        onClick={() => { setExpiry(e); setShowExpiry(false); }}
                        className={`w-full text-left px-4 py-2.5 text-sm hover:bg-muted transition-colors ${e === expiry ? "text-primary font-medium" : "text-foreground"}`}
                      >
                        {e}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-3 pt-2">
              <Button variant="outline" className="flex-1 border-border bg-background" onClick={handleClose}>Cancel</Button>
              <Button
                className="flex-1 bg-primary hover:bg-primary/90 text-primary-foreground"
                onClick={handleCreate}
                disabled={!name.trim()}
              >
                Create Key
              </Button>
            </div>
          </div>
        ) : (
          /* ── POST-CREATION ── */
          <div className="p-6 space-y-5">
            <div className="flex items-start gap-3 p-4 bg-safe/10 border border-safe/25 rounded-xl">
              <Check className="size-5 text-safe shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-semibold text-safe">Key generated successfully</p>
                <p className="text-xs text-muted-foreground mt-0.5">Copy this key now. You won't be able to view it again.</p>
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-2">Your API Key</label>
              <div className="flex items-center gap-2 bg-background border border-border rounded-xl p-4">
                <code className="flex-1 text-sm font-mono text-primary break-all">{secret}</code>
                <button
                  onClick={handleCopy}
                  className={`shrink-0 size-8 rounded-lg flex items-center justify-center transition-colors ${copied ? "bg-safe/15 text-safe" : "bg-muted text-muted-foreground hover:text-foreground hover:bg-border"}`}
                >
                  {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
                </button>
              </div>
              {copied && <p className="text-xs text-safe mt-1.5">Copied to clipboard</p>}
            </div>

            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="bg-muted rounded-lg p-3">
                <div className="text-xs text-muted-foreground mb-1">Name</div>
                <div className="font-medium text-foreground">{name}</div>
              </div>
              <div className="bg-muted rounded-lg p-3">
                <div className="text-xs text-muted-foreground mb-1">Environment</div>
                <div className="font-medium text-foreground">{env}</div>
              </div>
              <div className="bg-muted rounded-lg p-3">
                <div className="text-xs text-muted-foreground mb-1">Expiration</div>
                <div className="font-medium text-foreground">{expiry}</div>
              </div>
              <div className="bg-muted rounded-lg p-3">
                <div className="text-xs text-muted-foreground mb-1">Permissions</div>
                <div className="font-medium text-foreground">{Object.values(perms).filter(Boolean).length} scopes</div>
              </div>
            </div>

            <Button className="w-full bg-primary hover:bg-primary/90 text-primary-foreground" onClick={handleClose}>
              Done
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
