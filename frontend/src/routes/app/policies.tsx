import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { 
  ShieldCheck, Filter, Plus, ShieldAlert, ArrowUpRight, CheckCircle2, AlertTriangle, MoreHorizontal
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PolicyDetailsDrawer } from "@/components/policies/PolicyDetailsDrawer";
import { policiesApi, Policy } from "@/api/policies";
import { CreatePolicyDrawer } from "@/components/policies/CreatePolicyDrawer";
import { useAuth } from "@/lib/auth-context";
import { POLICIES_METRICS } from "@/data/mock-policies";

export const Route = createFileRoute("/app/policies")({
  component: PoliciesPage,
});

function PoliciesPage() {
  const [selectedPolicy, setSelectedPolicy] = useState<Policy | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const { workspace } = useAuth();

  const { data: policies = [], refetch } = useQuery({
    queryKey: ['policies', workspace?.id],
    queryFn: policiesApi.list,
    enabled: !!workspace,
  });

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-in fade-in duration-500">
      
      {/* 1. Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground mb-2">Policies</h1>
          <p className="text-muted-foreground font-medium">Define and enforce deterministic boundaries for autonomous financial agents.</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" className="border-border bg-background">
            <Filter className="size-4 mr-2" />
            Filter
          </Button>
          <Button onClick={() => setIsCreateOpen(true)}>
            <Plus className="size-4 mr-2" />
            Create Policy
          </Button>
        </div>
      </div>

      {/* 2. KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-5 border-border bg-surface shadow-sm">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Active Policies</div>
          <div className="text-3xl font-bold font-mono text-foreground mb-1">{policies.filter(p => p.status === 'ACTIVE').length}</div>
          <div className="text-sm text-muted-foreground font-medium flex items-center gap-1">
            {policies.length} total defined
          </div>
        </Card>

        <Card className="p-5 border-border bg-surface shadow-sm">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Policy Enforcements</div>
          <div className="text-3xl font-bold font-mono text-foreground mb-1">{policies.reduce((acc, p) => acc + (p.priority || 0), 0) > 0 ? policies.length : 0}</div>
          <div className="text-sm text-muted-foreground font-medium">
            Live workspace enforcements
          </div>
        </Card>

        <Card className="p-5 border-border bg-surface shadow-sm">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Blocked by Policy</div>
          <div className="text-3xl font-bold font-mono text-foreground mb-1">0</div>
          <div className="text-sm text-muted-foreground font-medium">
            ₹0 prevented in workspace
          </div>
        </Card>

        <Card className="p-5 border-border bg-surface shadow-sm">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Agent Coverage</div>
          <div className="text-3xl font-bold font-mono text-foreground mb-1">
            {policies.length > 0 ? "100%" : "0%"}
          </div>
          <div className="text-sm text-muted-foreground font-medium">
            {policies.length > 0 ? "Policies active" : "No policies configured"}
          </div>
        </Card>
      </div>

      {/* 3. Enforcement & Health */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        <Card className="col-span-1 lg:col-span-2 p-6 border-border bg-surface shadow-sm flex flex-col">
          <div className="flex items-center justify-between mb-6">
            <div className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Policy Enforcement</div>
            <div className="flex bg-background border border-border rounded-md text-xs font-medium">
              <button className="px-3 py-1 bg-surface-raised text-foreground rounded-l-md">24h</button>
              <button className="px-3 py-1 text-muted-foreground hover:text-foreground">7d</button>
              <button className="px-3 py-1 text-muted-foreground hover:text-foreground rounded-r-md">30d</button>
            </div>
          </div>
          
          <div className="flex-1 flex flex-col justify-end relative h-40">
            {/* CSS Pseudo-Chart for Enforcements */}
            <div className="absolute inset-0 flex items-end justify-between px-2">
              <div className="flex flex-col-reverse items-center justify-start h-[40%] w-2"><div className="h-full w-full bg-safe/60 rounded-t"></div></div>
              <div className="flex flex-col-reverse items-center justify-start h-[30%] w-2"><div className="h-full w-full bg-safe/60 rounded-t"></div></div>
              <div className="flex flex-col-reverse items-center justify-start h-[60%] w-2"><div className="h-full w-full bg-safe/60 rounded-t"></div></div>
              <div className="flex flex-col-reverse items-center justify-start h-[45%] w-2"><div className="h-[90%] w-full bg-safe/60"></div><div className="h-[10%] w-full bg-danger/80 rounded-t"></div></div>
              <div className="flex flex-col-reverse items-center justify-start h-[80%] w-2"><div className="h-[90%] w-full bg-safe/60"></div><div className="h-[10%] w-full bg-warn/80 rounded-t"></div></div>
              <div className="flex flex-col-reverse items-center justify-start h-[50%] w-2"><div className="h-full w-full bg-safe/60 rounded-t"></div></div>
              <div className="flex flex-col-reverse items-center justify-start h-[90%] w-2"><div className="h-[80%] w-full bg-safe/60"></div><div className="h-[5%] w-full bg-warn/80"></div><div className="h-[15%] w-full bg-danger/80 rounded-t"></div></div>
            </div>
            {/* Grid lines */}
            <div className="absolute inset-0 flex flex-col justify-between pointer-events-none">
              <div className="w-full border-t border-border/50 border-dashed" />
              <div className="w-full border-t border-border/50 border-dashed" />
              <div className="w-full border-t border-border/50 border-dashed" />
              <div className="w-full border-t border-border/50 border-dashed" />
            </div>
          </div>
          <div className="h-8 mt-6 w-full flex items-end justify-between px-2 text-[10px] font-mono text-muted-foreground/50 border-b border-border/50 pb-1">
            <span>Mon</span>
            <span>Tue</span>
            <span>Wed</span>
            <span>Thu</span>
            <span>Fri</span>
            <span>Sat</span>
            <span>Sun</span>
          </div>
          <div className="flex gap-6 mt-4 pt-4 border-t border-border">
            <div className="flex items-center gap-2 text-sm font-medium"><div className="size-2 rounded-full bg-safe/60" /> Allow: 0</div>
            <div className="flex items-center gap-2 text-sm font-medium"><div className="size-2 rounded-full bg-warn/80" /> Review: 0</div>
            <div className="flex items-center gap-2 text-sm font-medium"><div className="size-2 rounded-full bg-danger/80" /> Block: 0</div>
          </div>
        </Card>

        <Card className="p-6 border-border bg-surface shadow-sm">
          <div className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-6">Policy Health</div>
          <div className="space-y-4 text-sm font-medium">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="size-5 text-safe" />
              <span>{policies.filter(p => p.status === 'ACTIVE').length} healthy policies</span>
            </div>
            <div className="flex items-center gap-3">
              <CheckCircle2 className="size-5 text-safe" />
              <span>0 policy conflict detected</span>
            </div>
            <div className="flex items-center gap-3">
              <CheckCircle2 className="size-5 text-safe" />
              <span>{policies.filter(p => p.status === 'DRAFT').length} unused policy</span>
            </div>
            <div className="flex items-center gap-3">
              <CheckCircle2 className="size-5 text-safe" />
              <span>0 agents covered</span>
            </div>
            <div className="flex items-center gap-3">
              <CheckCircle2 className="size-5 text-safe" />
              <span>No enforcement failures</span>
            </div>
          </div>
        </Card>
      </div>

      {/* 4. Policy List */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-4">
            <h2 className="text-lg font-bold tracking-tight">Policies</h2>
            <div className="flex bg-surface border border-border rounded-md text-sm font-medium p-0.5">
              <button className="px-3 py-1 bg-background text-foreground rounded shadow-sm">All {policies.length}</button>
              <button className="px-3 py-1 text-muted-foreground hover:text-foreground">Active {policies.filter(p => p.status === 'ACTIVE').length}</button>
              <button className="px-3 py-1 text-muted-foreground hover:text-foreground">Draft {policies.filter(p => p.status === 'DRAFT').length}</button>
            </div>
          </div>
          <div className="relative">
            <input 
              type="text" 
              placeholder="Search policies..." 
              className="w-64 bg-surface border border-border rounded-md pl-3 pr-3 py-1.5 text-sm focus:outline-none focus:border-primary transition-colors"
            />
          </div>
        </div>

        <Card className="bg-surface border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-surface-raised border-b border-border">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground w-12">Status</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Policy</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Scope</th>
                <th className="px-4 py-3 text-right font-medium text-muted-foreground">Rules</th>
                <th className="px-4 py-3 text-right font-medium text-muted-foreground">Enforcements</th>
                <th className="px-4 py-3 text-right font-medium text-muted-foreground">Last Triggered</th>
                <th className="px-4 py-3 text-right font-medium text-muted-foreground w-12"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {policies.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-muted-foreground">
                    No activity yet.
                  </td>
                </tr>
              ) : policies.map((policy) => (
                <tr key={policy.id} className="hover:bg-surface-raised transition-colors cursor-pointer group" onClick={() => setSelectedPolicy(policy)}>
                  <td className="px-4 py-3 text-center">
                    <div className={`size-2.5 rounded-full ${policy.status === 'ACTIVE' ? 'bg-safe shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-muted-foreground'} mx-auto`} />
                  </td>
                  <td className="px-4 py-3">
                    <div className="font-semibold text-foreground group-hover:text-primary transition-colors">
                      {policy.name}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase bg-surface-raised border border-border">
                      {policy.policy_type.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-muted-foreground">{Object.keys(policy.conditions || {}).length}</td>
                  <td className="px-4 py-3 text-right font-mono text-muted-foreground">0</td>
                  <td className="px-4 py-3 text-right text-xs text-muted-foreground whitespace-nowrap">
                    Never
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Button variant="ghost" size="icon" className="size-6 text-muted-foreground" onClick={(e) => { e.stopPropagation(); }}>
                      <MoreHorizontal className="size-4" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>

      {/* 5. Recent Policy Decisions */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold tracking-tight">Recent Policy Decisions</h2>
          <Button variant="link" className="text-primary text-sm h-auto p-0">View all →</Button>
        </div>
        <Card className="bg-surface border-border overflow-hidden p-0">
          <div className="divide-y divide-border">
            {([] as any[]).map((event, idx) => (
              <div key={idx} className="flex items-center justify-between p-4 hover:bg-surface-raised transition-colors cursor-pointer">
                <div className="flex items-center gap-6">
                  <div className="font-mono text-muted-foreground text-sm">{event.time}</div>
                  <div className="font-medium">{event.type}</div>
                  <div className="text-muted-foreground text-sm">{event.agent}</div>
                </div>
                <div className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase border ${event.color}`}>
                  {event.decision}
                </div>
              </div>
            ))}
            <div className="p-4 text-center text-muted-foreground text-sm">
              No recent decisions.
            </div>
          </div>
        </Card>
      </div>

      {/* Drawers */}
      {selectedPolicy && (
        <PolicyDetailsDrawer 
          policy={selectedPolicy} 
          onClose={() => setSelectedPolicy(null)} 
        />
      )}
      
      {isCreateOpen && (
        <CreatePolicyDrawer 
          onClose={() => setIsCreateOpen(false)} 
          onSuccess={() => {
            setIsCreateOpen(false);
            refetch();
          }}
        />
      )}
    </div>
  );
}
