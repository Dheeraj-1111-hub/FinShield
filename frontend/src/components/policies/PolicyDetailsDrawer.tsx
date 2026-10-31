import { X, ArrowRight, Activity, Terminal, Edit, Search } from "lucide-react";
import { Link } from "@tanstack/react-router";
import { Policy, policiesApi } from "@/api/policies";
import { Button } from "@/components/ui/button";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth-context";

interface PolicyDetailsDrawerProps {
  policy: Policy;
  onClose: () => void;
}

export function PolicyDetailsDrawer({ policy, onClose }: PolicyDetailsDrawerProps) {
  const queryClient = useQueryClient();
  const { workspace } = useAuth();
  
  const handleDelete = async () => {
    if (confirm("Are you sure you want to delete this policy?")) {
      await policiesApi.delete(policy.id);
      queryClient.invalidateQueries({ queryKey: ['policies', workspace?.id] });
      onClose();
    }
  };
  return (
    <div className="absolute inset-y-0 right-0 w-[550px] bg-background border-l border-border shadow-2xl flex flex-col z-50 animate-in slide-in-from-right duration-300">
      
      {/* Header */}
      <div className="h-14 border-b border-border flex items-center justify-between px-5 bg-surface shrink-0">
        <div className="flex items-center gap-3">
          <div className="text-sm font-semibold text-muted-foreground flex items-center gap-2">
            <Button variant="ghost" size="icon" onClick={onClose} className="size-6 -ml-2 rounded-full">
              <ArrowRight className="size-3.5 rotate-180" />
            </Button>
            Policy
          </div>
          <span className="text-muted-foreground">/</span>
          <div className="font-mono text-sm font-bold">{policy.id}</div>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} className="size-8 rounded-full">
          <X className="size-4" />
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-8 custom-scrollbar">
        
        {/* Hero Section */}
        <div>
          <div className="flex items-center gap-2 mb-4">
            <div className={`size-2.5 rounded-full shadow-[0_0_8px_rgba(16,185,129,0.5)] ${policy.status === 'ACTIVE' ? 'bg-safe' : 'bg-muted-foreground'}`} />
            <span className="text-[10px] font-bold tracking-wider border border-border px-2 py-0.5 rounded uppercase bg-surface-raised">
              {policy.status}
            </span>
            <span className="text-xs font-mono text-muted-foreground ml-2">v{policy.version || 1}</span>
          </div>
          
          <h2 className="text-2xl font-bold tracking-tight mb-2">{policy.name}</h2>
          <p className="text-sm text-muted-foreground">{policy.description}</p>
        </div>

        {/* Scope & Type */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-surface p-4 rounded-xl border border-border shadow-sm">
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Scope</div>
            <div className="font-medium text-sm">Workspace</div>
          </div>
          <div className="bg-surface p-4 rounded-xl border border-border shadow-sm">
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Type</div>
            <div className="font-medium text-sm">{policy.policy_type}</div>
          </div>
        </div>

        {/* Rules */}
        <div>
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4 flex items-center justify-between">
            <span>Rules</span>
            <Button variant="link" className="text-primary text-xs h-auto p-0">Edit Rules</Button>
          </div>
          <div className="space-y-3">
            {Object.entries(policy.conditions || {}).map(([key, val], idx) => (
              <div key={idx} className="bg-surface border border-border rounded-xl p-4 shadow-sm">
                <div className="flex items-center gap-3">
                  <div className="text-xs font-mono text-muted-foreground">IF</div>
                  <div className="font-medium text-sm flex-1">{key} {val.operator} {val.value}</div>
                </div>
                <div className="flex items-center gap-3 mt-3 pt-3 border-t border-border/50">
                  <div className="text-xs font-mono text-muted-foreground">THEN</div>
                  <div className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase border ${
                    policy.actions.decision === 'BLOCK' ? 'bg-danger/10 text-danger border-danger/20' :
                    policy.actions.decision === 'REVIEW' ? 'bg-warn/10 text-warn border-warn/20' :
                    'bg-safe/10 text-safe border-safe/20'
                  }`}>
                    {policy.actions.decision || 'ALLOW'}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Enforcement Stats */}
        <div>
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4">Enforcement</div>
          <div className="bg-background border border-border p-5 rounded-xl shadow-sm opacity-50">
            <div className="text-3xl font-bold font-mono mb-4">0 <span className="text-sm font-medium text-muted-foreground">evaluations</span></div>
            <div className="space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2"><div className="size-2 rounded-full bg-safe/60" /> Allowed</span>
                <span className="font-mono font-medium">0</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2"><div className="size-2 rounded-full bg-warn/80" /> Review required</span>
                <span className="font-mono font-medium">0</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2"><div className="size-2 rounded-full bg-danger/80" /> Blocked</span>
                <span className="font-mono font-medium">0</span>
              </div>
            </div>
          </div>  
            <Button variant="outline" className="w-full mt-6 bg-surface-raised border-border">
              <Search className="size-4 mr-2" />
              View Enforcements in Risk Center
            </Button>
          </div>

        <div className="pt-4 border-t border-border mt-8 flex justify-between">
          <Button variant="outline" className="text-danger border-danger/30 hover:bg-danger/10 hover:text-danger" onClick={handleDelete}>
            Delete Policy
          </Button>
        </div>
        
      </div>
    </div>
  );
}
