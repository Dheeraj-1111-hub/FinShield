import { useState } from "react";
import { X, Key, RotateCcw, Trash2, Shield, Copy, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ApiKey } from "@/data/mock-developers";

interface Props {
  apiKey: ApiKey | null;
  onClose: () => void;
}

export function ApiKeyDrawer({ apiKey, onClose }: Props) {
  const [copied, setCopied] = useState(false);

  if (!apiKey) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(apiKey.maskedKey).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const statusColor = apiKey.status === 'ACTIVE'
    ? 'text-safe bg-safe/10 border-safe/20'
    : apiKey.status === 'EXPIRING'
    ? 'text-warn bg-warn/10 border-warn/20'
    : 'text-danger bg-danger/10 border-danger/20';

  return (
    <div className="fixed inset-0 z-50 flex" onClick={onClose}>
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />
      <div className="ml-auto relative w-full max-w-md h-full bg-surface border-l border-border overflow-y-auto" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="sticky top-0 bg-surface border-b border-border px-6 py-4 flex items-center justify-between z-10">
          <div className="flex items-center gap-3">
            <div className="size-8 rounded-lg bg-primary/15 flex items-center justify-center">
              <Key className="size-4 text-primary" />
            </div>
            <div>
              <h2 className="font-bold text-foreground">{apiKey.name}</h2>
              <div className="text-xs text-muted-foreground">API Key</div>
            </div>
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors">
            <X className="size-5" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Status + Key */}
          <div className="space-y-3">
            <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs font-bold uppercase tracking-wider ${statusColor}`}>
              <span className="size-1.5 rounded-full bg-current" />
              {apiKey.status}
            </span>

            <div className="flex items-center gap-2 bg-background border border-border rounded-xl p-4">
              <code className="flex-1 text-sm font-mono text-primary">{apiKey.maskedKey}</code>
              <button
                onClick={handleCopy}
                className={`shrink-0 size-7 rounded-md flex items-center justify-center transition-colors ${copied ? "bg-safe/15 text-safe" : "bg-muted text-muted-foreground hover:text-foreground"}`}
              >
                {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
              </button>
            </div>
          </div>

          {/* Metadata */}
          <div>
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Details</div>
            <div className="space-y-0 divide-y divide-border border border-border rounded-xl overflow-hidden">
              {[
                { label: "Environment", value: apiKey.environment },
                { label: "Scope",       value: apiKey.scope },
                { label: "Created",     value: apiKey.created },
                { label: "Last used",   value: apiKey.lastUsed },
                { label: "Requests",    value: apiKey.requests.toLocaleString() },
              ].map(row => (
                <div key={row.label} className="flex items-center justify-between px-4 py-3 bg-muted text-sm">
                  <span className="text-muted-foreground">{row.label}</span>
                  <span className="font-medium text-foreground font-mono">{row.value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Permissions */}
          <div>
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Permissions</div>
            <div className="space-y-2">
              {apiKey.permissions.map(p => (
                <div key={p} className="flex items-center gap-2.5 px-3 py-2.5 bg-muted rounded-lg border border-border text-sm">
                  <Check className="size-4 text-safe shrink-0" />
                  <span className="text-foreground font-medium">{p}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Security */}
          <div>
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3 flex items-center gap-2">
              <Shield className="size-3.5" /> Security
            </div>
            <div className="space-y-0 divide-y divide-border border border-border rounded-xl overflow-hidden">
              {[
                { label: "Created by", value: apiKey.createdBy },
                { label: "Last IP",    value: apiKey.lastIp },
                { label: "Expires",    value: apiKey.expires },
              ].map(row => (
                <div key={row.label} className="flex items-center justify-between px-4 py-3 bg-muted text-sm">
                  <span className="text-muted-foreground">{row.label}</span>
                  <span className="font-medium text-foreground font-mono">{row.value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="space-y-2 pt-2">
            <Button variant="outline" className="w-full border-border bg-background gap-2">
              <RotateCcw className="size-4" /> Rotate Key
            </Button>
            <Button variant="outline" className="w-full border-danger/30 bg-danger/5 text-danger hover:bg-danger/10 gap-2">
              <Trash2 className="size-4" /> Revoke Key
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
