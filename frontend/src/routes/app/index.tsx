import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getOverview } from "@/api/overview";
import { approvalsApi } from "@/api/approvals";
import { useAuth } from "@/lib/auth-context";
import { formatCurrency } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { 
  ShieldCheck, 
  AlertTriangle, 
  Shield,
  Plus,
  CheckCircle2,
  XCircle,
  Activity,
  ArrowRight
} from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatRelativeTime } from "@/lib/utils";

export const Route = createFileRoute("/app/")({
  component: CommandCenter,
});

function CommandCenter() {
  const { workspace: currentWorkspace } = useAuth();
  const queryClient = useQueryClient();

  const approveMutation = useMutation({
    mutationFn: (id: string) => approvalsApi.decide(id, "APPROVED", "Approved from Command Center"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["overview", currentWorkspace?.id] });
    }
  });

  const rejectMutation = useMutation({
    mutationFn: (id: string) => approvalsApi.decide(id, "REJECTED", "Rejected from Command Center"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["overview", currentWorkspace?.id] });
    }
  });

  const { data: overview, isLoading, error } = useQuery({
    queryKey: ["overview", currentWorkspace?.id],
    queryFn: () => getOverview(currentWorkspace?.id || ""),
    enabled: !!currentWorkspace,
    refetchInterval: 15000, // Refresh every 15s to feel operational
  });

  if (!currentWorkspace) {
    return <div className="p-8">No workspace selected.</div>;
  }

  if (isLoading) {
    return (
      <div className="space-y-8 p-6 animate-pulse">
        <Skeleton className="h-10 w-[200px]" />
        <Skeleton className="h-24 w-full" />
        <div className="grid gap-4 md:grid-cols-4">
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
        </div>
      </div>
    );
  }

  if (error || !overview) {
    return (
      <div className="p-8 text-danger flex items-center gap-2">
        <AlertTriangle className="size-5" />
        Failed to load overview data.
      </div>
    );
  }

  // Calculate items requiring attention
  const needsAttention = (overview.recent_approvals?.length || 0) + (overview.recent_critical_risks?.length || 0);

  return (
    <div className="space-y-8 animate-rise pb-10">
      
      {/* 1. Greeting & Global Status */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
        <div>
          <h2 className="text-3xl font-semibold tracking-tight text-foreground">Command Center</h2>
          <p className="text-base text-muted-foreground mt-1">
            Good evening. Your autonomous financial workspace is operating normally.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" className="border-border" asChild>
            <Link to="/app/policies">
              <Shield className="mr-2 size-4" />
              Add Policy
            </Link>
          </Button>
          <Button asChild>
            <Link to="/app/agents">
              <Plus className="mr-2 size-4" />
              Create Agent
            </Link>
          </Button>
        </div>
      </div>

      {/* 2. FINSHIELD Protection Bar - Clean & Professional */}
      <div className="rounded-xl border border-safe/20 bg-surface flex flex-col md:flex-row items-start md:items-center justify-between p-5 shadow-sm overflow-hidden relative">
        <div className="absolute top-0 left-0 w-1 h-full bg-safe" />
        
        <div className="flex items-center gap-4">
          <div className="flex size-10 items-center justify-center rounded-lg bg-safe/10 text-safe border border-safe/20">
            <ShieldCheck className="size-5" />
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h3 className="text-sm font-bold tracking-wide text-foreground">FINSHIELD PROTECTION</h3>
              <Badge variant="outline" className="border-safe/30 text-safe bg-safe/5 rounded-full px-2.5 py-0 text-[10px] font-semibold tracking-wider">
                <span className="size-1.5 rounded-full bg-safe mr-1.5 animate-pulse-dot" />
                OPERATIONAL
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground mt-1 font-medium">
              {overview.agents.total} agent{overview.agents.total === 1 ? '' : 's'} protected • {overview.gate.allow + overview.gate.block + overview.gate.review} actions evaluated
            </p>
          </div>
        </div>
        <div className="mt-4 md:mt-0 flex flex-wrap gap-4 md:gap-6 text-sm text-muted-foreground font-medium bg-background/50 py-1.5 px-4 rounded-md border border-border/50">
          <div className="flex items-center gap-2"><CheckCircle2 className="size-4 text-safe" /> Intent monitoring</div>
          <div className="flex items-center gap-2"><CheckCircle2 className="size-4 text-safe" /> Policy enforcement</div>
          <div className="flex items-center gap-2"><CheckCircle2 className="size-4 text-safe" /> Risk engine</div>
        </div>
      </div>

      {/* 3. Key Metrics - Clean Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="bg-surface shadow-sm border-border">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Captured Volume</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono text-foreground">
              {formatCurrency(overview.financial.payment_volume, overview.financial.currency || currentWorkspace?.currency || "INR")}
            </div>
            <p className="text-xs text-muted-foreground mt-1 font-medium">
              {overview.financial.payment_count} payments captured · {overview.financial.orders_count || 0} orders
            </p>
          </CardContent>
        </Card>
        
        <Card className="bg-surface shadow-sm border-border">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Agent activity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono text-foreground">{overview.agents.active}</div>
            <p className="text-xs text-muted-foreground mt-1 font-medium">Active of {overview.agents.total} total</p>
          </CardContent>
        </Card>
        
        <Card className="bg-surface shadow-sm border-border">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Gate Decisions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono text-foreground">{overview.gate.allow_rate.toFixed(2)}%</div>
            <p className="text-xs text-muted-foreground mt-1 font-medium">Approval rate ({overview.time_range})</p>
          </CardContent>
        </Card>
        
        <Card className="bg-surface shadow-sm border-border">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Security posture</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              {overview.security.open_findings > 0 ? (
                <>
                  <span className="size-2.5 rounded-full bg-warn" />
                  <div className="text-2xl font-bold font-mono text-foreground">MEDIUM</div>
                </>
              ) : (
                <>
                  <span className="size-2.5 rounded-full bg-safe" />
                  <div className="text-2xl font-bold font-mono text-foreground">LOW</div>
                </>
              )}
            </div>
            <p className="text-xs text-muted-foreground mt-1 font-medium">
              {overview.security.open_findings} finding{overview.security.open_findings === 1 ? '' : 's'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* 4. Needs Your Attention - Semantic Action Cards */}
      {needsAttention > 0 && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2 text-foreground font-semibold uppercase tracking-wider text-sm">
              <span className="size-2 rounded-full bg-warn" />
              Needs Your Attention
            </div>
            <Badge variant="outline" className="bg-surface text-muted-foreground">{needsAttention} items</Badge>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            
            {/* Approvals */}
            {overview.recent_approvals?.map(approval => (
              <div key={approval.id} className="rounded-xl border border-border bg-surface p-5 shadow-sm relative group overflow-hidden">
                <div className="absolute top-0 left-0 w-1 h-full bg-warn" />
                <div className="flex justify-between items-start mb-4">
                  <div className="flex items-center gap-2 text-warn font-semibold text-sm">
                    <AlertTriangle className="size-4" />
                    ACTION APPROVAL REQUIRED
                  </div>
                  <Badge variant="outline" className="text-warn border-warn/30 bg-warn/10">HIGH</Badge>
                </div>
                <p className="text-base text-foreground font-medium mb-4">
                  {approval.agent_name} wants to perform<br/><span className="text-muted-foreground">{approval.action_type === "Unknown" ? "AN UNKNOWN ACTION" : approval.action_type}</span>
                </p>
                <div className="grid grid-cols-[100px_1fr] gap-y-2 text-sm mb-6 bg-background/50 p-3 rounded-lg border border-border/50">
                  {approval.amount && (
                    <>
                      <span className="text-muted-foreground font-medium">Amount</span>
                      <span className="font-mono text-foreground font-medium">₹{approval.amount.toLocaleString()}</span>
                    </>
                  )}
                  {approval.merchant && (
                    <>
                      <span className="text-muted-foreground font-medium">Merchant</span>
                      <span className="text-foreground">{approval.merchant}</span>
                    </>
                  )}
                  <span className="text-muted-foreground font-medium">Reason</span>
                  <span className="text-foreground">{approval.reason}</span>
                </div>
                <div className="flex gap-3 mt-auto justify-end">
                  <Button 
                    variant="outline" 
                    className="border-border"
                    disabled={rejectMutation.isPending || approveMutation.isPending}
                    onClick={() => rejectMutation.mutate(approval.id)}
                  >
                    Reject
                  </Button>
                  <Button 
                    className="bg-warn text-warn-foreground hover:bg-warn/90"
                    disabled={rejectMutation.isPending || approveMutation.isPending}
                    onClick={() => approveMutation.mutate(approval.id)}
                  >
                    Review & Approve
                  </Button>
                </div>
              </div>
            ))}

            {/* Critical Risks */}
            {overview.recent_critical_risks?.map(risk => (
              <div key={risk.id} className="rounded-xl border border-border bg-surface p-5 shadow-sm relative group overflow-hidden">
                <div className="absolute top-0 left-0 w-1 h-full bg-danger" />
                <div className="flex justify-between items-start mb-4">
                  <div className="flex items-center gap-2 text-danger font-semibold text-sm">
                    <XCircle className="size-4" />
                    {risk.risk_level === "CRITICAL" ? "CRITICAL RISK EVENT" : "HIGH RISK EVENT"}
                  </div>
                  <Badge variant="outline" className="text-danger border-danger/30 bg-danger/10">{risk.risk_level}</Badge>
                </div>
                <p className="text-base text-foreground font-medium mb-4">
                  {risk.agent_name} attempted<br/><span className="text-danger">{risk.action_type}</span>
                </p>
                <div className="grid grid-cols-[120px_1fr] gap-y-2 text-sm mb-6 bg-background/50 p-3 rounded-lg border border-border/50">
                  <span className="text-muted-foreground font-medium">Score</span>
                  <span className="font-mono text-danger font-semibold">{risk.score}/100</span>
                  <span className="text-muted-foreground font-medium">Reason</span>
                  <span className="text-foreground">{risk.reason}</span>
                  <span className="text-muted-foreground font-medium">Decision</span>
                  <span className="text-danger font-bold flex items-center gap-1.5"><Shield className="size-3.5" /> BLOCKED</span>
                </div>
                <div className="flex gap-3 mt-auto justify-end">
                  <Button variant="outline" className="border-border" asChild>
                    <Link to="/app/risk">Dismiss</Link>
                  </Button>
                  <Button variant="destructive" asChild>
                    <Link to="/app/investigations">View Investigation</Link>
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 5. Minimalist Data Tables - Clean & Scannable */}
      <div className="grid gap-6 lg:grid-cols-2">
        
        {/* Recent Audit Log */}
        <div className="border border-border rounded-xl bg-surface shadow-sm overflow-hidden">
          <div className="flex justify-between items-center p-4 border-b border-border/50 bg-background/30">
            <div className="flex items-center gap-2">
              <Activity className="size-4 text-muted-foreground" />
              <h3 className="font-semibold text-sm uppercase tracking-wider text-foreground">Recent Activity Log</h3>
            </div>
            <Button variant="ghost" size="sm" className="h-8 text-xs text-muted-foreground hover:text-foreground" asChild>
              <Link to="/app/audit">
                View All <ArrowRight className="ml-1 size-3" />
              </Link>
            </Button>
          </div>
          <Table>
            <TableHeader className="bg-transparent">
              <TableRow className="border-border/50 hover:bg-transparent">
                <TableHead className="text-xs font-semibold uppercase text-muted-foreground h-10">Event</TableHead>
                <TableHead className="text-xs font-semibold uppercase text-muted-foreground h-10">Target</TableHead>
                <TableHead className="text-xs font-semibold uppercase text-muted-foreground h-10 text-right">Time</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {overview.recent_audit_events?.length > 0 ? overview.recent_audit_events.map((log, i) => (
                <TableRow key={i} className="border-border/50 hover:bg-background/50 transition-colors">
                  <TableCell className="font-medium text-foreground py-3 text-sm">
                    {log.event_type.replace(/_/g, ' ')}
                  </TableCell>
                  <TableCell className="text-muted-foreground py-3 text-sm">
                    {log.target_type ? `${log.target_type} (${log.target_id?.slice(0, 8)})` : '-'}
                  </TableCell>
                  <TableCell className="text-right text-muted-foreground py-3 text-sm">
                    {formatRelativeTime(log.occurred_at)}
                  </TableCell>
                </TableRow>
              )) : (
                <TableRow>
                  <TableCell colSpan={3} className="text-center py-6 text-muted-foreground text-sm">
                    No recent activity.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>

        {/* System Health */}
        <div className="border border-border rounded-xl bg-surface shadow-sm overflow-hidden">
          <div className="flex justify-between items-center p-4 border-b border-border/50 bg-background/30">
            <div className="flex items-center gap-2">
              <Shield className="size-4 text-muted-foreground" />
              <h3 className="font-semibold text-sm uppercase tracking-wider text-foreground">System Health</h3>
            </div>
          </div>
          <Table>
            <TableHeader className="bg-transparent">
              <TableRow className="border-border/50 hover:bg-transparent">
                <TableHead className="text-xs font-semibold uppercase text-muted-foreground h-10">Component</TableHead>
                <TableHead className="text-xs font-semibold uppercase text-muted-foreground h-10 text-right">Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {Object.entries(overview.health).map(([key, value]) => (
                <TableRow key={key} className="border-border/50 hover:bg-background/50 transition-colors">
                  <TableCell className="font-medium text-foreground py-3 text-sm capitalize">
                    {key} Node
                  </TableCell>
                  <TableCell className="text-right py-3 text-sm">
                    {value === "HEALTHY" ? (
                      <Badge variant="outline" className="bg-safe/10 text-safe border-safe/30 text-[10px]">HEALTHY</Badge>
                    ) : (
                      <Badge variant="outline" className="bg-danger/10 text-danger border-danger/30 text-[10px]">{value}</Badge>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

      </div>

    </div>
  );
}
