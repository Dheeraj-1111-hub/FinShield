import { useState } from "react";
import { Key, Copy, Check, Plus, ChevronRight } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { API_KEYS, ApiKey } from "@/data/mock-developers";

interface Props {
  onCreateKey: () => void;
  onSelectKey: (key: ApiKey) => void;
}

export function ApiKeysTable({ onCreateKey, onSelectKey }: Props) {
  const [copied, setCopied] = useState<string | null>(null);

  const handleCopy = (id: string, key: string) => {
    navigator.clipboard.writeText(key).catch(() => {});
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  };

  const statusStyle = (status: ApiKey["status"]) => {
    switch (status) {
      case "ACTIVE":   return "text-safe bg-safe/10 border-safe/20";
      case "EXPIRING": return "text-warn bg-warn/10 border-warn/20";
      case "REVOKED":  return "text-danger bg-danger/10 border-danger/20";
    }
  };

  return (
    <Card className="border-border bg-surface shadow-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-border">
        <div className="flex items-center gap-3">
          <Key className="size-4 text-primary" />
          <div>
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">API Access</div>
            <div className="font-bold text-foreground">API Keys</div>
          </div>
        </div>
        <Button size="sm" className="bg-primary hover:bg-primary/90 text-primary-foreground gap-1.5" onClick={onCreateKey}>
          <Plus className="size-3.5" /> Create Key
        </Button>
      </div>

      <div className="px-6 pb-2 pt-3">
        <p className="text-xs text-muted-foreground">API keys authenticate requests to FINSHIELD. Never expose keys in client-side code.</p>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left px-6 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Name</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Env</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider hidden lg:table-cell">Scope</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider hidden md:table-cell">Last used</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Status</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {API_KEYS.map(key => (
              <tr
                key={key.id}
                className="hover:bg-muted/50 transition-colors cursor-pointer group"
                onClick={() => onSelectKey(key)}
              >
                <td className="px-6 py-4">
                  <div className="font-medium text-foreground">{key.name}</div>
                  <div className="flex items-center gap-1.5 mt-1">
                    <code className="text-xs font-mono text-muted-foreground">{key.maskedKey}</code>
                    <button
                      onClick={e => { e.stopPropagation(); handleCopy(key.id, key.maskedKey); }}
                      className={`size-5 rounded flex items-center justify-center transition-colors ${copied === key.id ? "text-safe" : "text-muted-foreground hover:text-foreground"}`}
                    >
                      {copied === key.id ? <Check className="size-3" /> : <Copy className="size-3" />}
                    </button>
                  </div>
                </td>
                <td className="px-4 py-4">
                  <span className="text-xs font-medium px-2 py-0.5 rounded-md bg-muted border border-border text-muted-foreground">
                    {key.environment}
                  </span>
                </td>
                <td className="px-4 py-4 hidden lg:table-cell text-muted-foreground">{key.scope}</td>
                <td className="px-4 py-4 hidden md:table-cell text-muted-foreground font-mono text-xs">{key.lastUsed}</td>
                <td className="px-4 py-4">
                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md border text-xs font-bold uppercase ${statusStyle(key.status)}`}>
                    <span className="size-1.5 rounded-full bg-current" />{key.status}
                  </span>
                </td>
                <td className="px-4 py-4">
                  <ChevronRight className="size-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
