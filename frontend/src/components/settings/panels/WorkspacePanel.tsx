import { Card } from "@/components/ui/card";
import { Check, Info } from "lucide-react";

function Toggle({ label, description, checked, onChange }: { label: string; description: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <div className="flex items-start justify-between gap-4 p-4 border border-border rounded-lg bg-background">
      <div>
        <div className="text-sm font-semibold text-foreground">{label}</div>
        <div className="text-sm text-muted-foreground mt-1">{description}</div>
      </div>
      <button
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-background ${checked ? 'bg-primary' : 'bg-muted-foreground/30'}`}
      >
        <span className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${checked ? 'translate-x-5' : 'translate-x-0'}`} />
      </button>
    </div>
  );
}

export function WorkspacePanel({ data, onChange }: { data?: any, onChange?: (domain: string, field: string, value: any) => void }) {
  if (!data?.workspace || !data?.settings) return null;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-foreground mb-0.5">Workspace Settings</h2>
        <p className="text-sm text-muted-foreground">Manage your workspace identity and risk configuration.</p>
      </div>

      <Card className="border-border bg-surface p-6 space-y-5">
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Workspace Identity</div>
        <div>
          <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-2">Workspace Name</label>
          <input value={data.workspace.name || ""} onChange={e => onChange?.("workspace", "name", e.target.value)}
            className="w-full bg-background border border-border rounded-lg px-3 py-2.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40" />
        </div>
        <div>
          <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-2">Workspace Slug</label>
          <input value={data.workspace.slug || ""} onChange={e => onChange?.("workspace", "slug", e.target.value)}
            className={`w-full bg-background border rounded-lg px-3 py-2.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 ${
              data.workspace.slug && (!/^[a-z0-9-]+$/.test(data.workspace.slug) || data.workspace.slug.length < 3 || data.workspace.slug.length > 40)
                ? 'border-red-500 focus:ring-red-500/40' : 'border-border'
            }`} />
          {data.workspace.slug && (!/^[a-z0-9-]+$/.test(data.workspace.slug) || data.workspace.slug.length < 3 || data.workspace.slug.length > 40) && (
            <p className="text-xs text-red-500 mt-1">Slug must be 3-40 characters (lowercase letters, numbers, hyphens only).</p>
          )}
        </div>
        <div>
          <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-2">Environment</label>
          <input value={data.workspace.environment || ""} disabled
            className="w-full bg-muted border border-border rounded-lg px-3 py-2.5 text-sm text-muted-foreground focus:outline-none cursor-not-allowed" />
        </div>
      </Card>

      <Card className="border-border bg-surface p-6 space-y-5">
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Risk Engine Configuration</div>
        
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-2">Review Threshold (0-100)</label>
            <input type="number" value={data.settings.review_threshold || 0} onChange={e => onChange?.("settings", "review_threshold", parseInt(e.target.value) || 0)}
              className="w-full bg-background border border-border rounded-lg px-3 py-2.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40" />
          </div>
          <div>
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-2">Block Threshold (0-100)</label>
            <input type="number" value={data.settings.risk_threshold || 0} onChange={e => onChange?.("settings", "risk_threshold", parseInt(e.target.value) || 0)}
              className="w-full bg-background border border-border rounded-lg px-3 py-2.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40" />
          </div>
        </div>

        <Toggle 
          label="Human Review for Critical Actions" 
          description="Require manual approval for actions exceeding the block threshold."
          checked={data.settings.human_review_for_critical_actions || false}
          onChange={v => onChange?.("settings", "human_review_for_critical_actions", v)}
        />
      </Card>
    </div>
  );
}
