import { useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { authoritiesApi } from "@/api/authorities";
import { agentsApi } from "@/api/agents";
import { 
  ShieldCheck, ArrowLeft, Play, Ban, Activity,
  Clock, AlertTriangle, History, Target, Zap, Edit, Check, Loader2
} from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { Checkbox } from "@/components/ui/checkbox";
import { ALL_CAPABILITIES } from "../new";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";

export const Route = createFileRoute("/app/authorities/$authorityId/")({
  component: AuthorityDetailRoute,
});

function getStatusDisplay(status: string) {
  switch (status) {
    case "ACTIVE": return { icon: Play, color: "text-safe", bg: "bg-safe/20", text: "ACTIVE" };
    case "DRAFT": return { icon: ShieldCheck, color: "text-muted-foreground", bg: "bg-muted/50", text: "DRAFT" };
    case "REVOKED": return { icon: Ban, color: "text-danger", bg: "bg-danger/20", text: "REVOKED" };
    case "EXPIRED": return { icon: Clock, color: "text-warn", bg: "bg-warn/20", text: "EXPIRED" };
    case "ARCHIVED": return { icon: AlertTriangle, color: "text-muted-foreground", bg: "bg-muted/50", text: "ARCHIVED" };
    default: return { icon: ShieldCheck, color: "text-muted-foreground", bg: "bg-muted/50", text: status };
  }
}

function AuthorityDetailRoute() {
  const { authorityId } = Route.useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [simCapability, setSimCapability] = useState("EXECUTE_PAYMENT");
  const [simAmount, setSimAmount] = useState("");
  const [simCurrency, setSimCurrency] = useState("INR");
  const [simResult, setSimResult] = useState<any>(null);

  const { data: auth, isLoading, error: authError } = useQuery({
    queryKey: ["authorities", authorityId],
    queryFn: () => authoritiesApi.get(authorityId)
  });

  const { data: versions = [], isLoading: versionsLoading } = useQuery({
    queryKey: ["authorities", authorityId, "versions"],
    queryFn: () => authoritiesApi.getVersions(authorityId)
  });

  const { data: agents = [] } = useQuery({
    queryKey: ["agents"],
    queryFn: agentsApi.list
  });

  const activateMutation = useMutation({
    mutationFn: () => authoritiesApi.activate(authorityId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["authorities", authorityId] });
      toast.success("Authority activated");
    }
  });

  const revokeMutation = useMutation({
    mutationFn: () => authoritiesApi.revoke(authorityId, "Manually revoked by user"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["authorities", authorityId] });
      toast.success("Authority revoked");
    }
  });

  const simulateMutation = useMutation({
    mutationFn: (payload: any) => authoritiesApi.simulate(authorityId, payload),
    onSuccess: (data) => {
      setSimResult(data);
    },
    onError: (err: any) => {
      const errorMsg = err?.response?.data?.error?.message || err?.response?.data?.detail || "Simulation failed";
      toast.error(errorMsg);
    }
  });

  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editCapabilities, setEditCapabilities] = useState<string[]>([]);

  const updateMutation = useMutation({
    mutationFn: (data: any) => authoritiesApi.update(authorityId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["authorities", authorityId] });
      queryClient.invalidateQueries({ queryKey: ["authorities", authorityId, "versions"] });
      setIsEditModalOpen(false);
      toast.success("Authority capabilities updated successfully");
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.error?.message || err?.response?.data?.detail || "Failed to update authority";
      toast.error(msg);
    }
  });

  const handleOpenEdit = () => {
    setEditCapabilities([...(auth?.allowed_capabilities || [])]);
    setIsEditModalOpen(true);
  };

  const handleToggleCapability = (cap: string) => {
    setEditCapabilities(prev =>
      prev.includes(cap) ? prev.filter(c => c !== cap) : [...prev, cap]
    );
  };

  const handleSaveCapabilities = () => {
    if (editCapabilities.length === 0) {
      toast.error("At least one capability must be selected");
      return;
    }
    updateMutation.mutate({
      allowed_capabilities: editCapabilities,
      change_reason: "Updated delegated capabilities"
    });
  };

  if (isLoading) {
    return (
      <div className="w-full max-w-5xl mx-auto space-y-6">
        <Skeleton className="h-12 w-1/3" />
        <Skeleton className="h-[400px] w-full" />
      </div>
    );
  }

  if (authError || !auth) {
    return (
      <div className="w-full max-w-5xl mx-auto space-y-6">
        <div className="flex items-center gap-4 mb-2">
          <Button variant="ghost" size="icon" onClick={() => window.history.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-danger flex items-center gap-2">
              <AlertTriangle className="h-6 w-6" /> Authority Not Found
            </h1>
            <p className="text-muted-foreground mt-1">
              Could not load authority record for <code className="font-mono">{authorityId}</code>.
            </p>
          </div>
        </div>
        <Card className="p-6">
          <p className="text-sm text-muted-foreground mb-4">
            The requested authority does not exist or you do not have permission to access it.
          </p>
          <Button onClick={() => navigate({ to: "/app/authorities" })}>
            Return to Authorities
          </Button>
        </Card>
      </div>
    );
  }

  const status = getStatusDisplay(auth.status);
  const StatusIcon = status.icon;
  const agent = agents.find(a => a.id === auth.agent_id);

  const handleSimulate = () => {
    simulateMutation.mutate({
      action: simCapability,
      amount: simAmount ? parseFloat(simAmount) : undefined,
      currency: simCurrency
    });
  };

  return (
    <div className="w-full max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-4 mb-2">
            <Button variant="ghost" size="icon" onClick={() => window.history.back()}>
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <span className={`inline-flex items-center gap-1.5 text-sm font-medium px-2.5 py-1 rounded-full ${status.bg} ${status.color}`}>
              <StatusIcon className="h-4 w-4" />
              {status.text}
            </span>
            <span className="text-sm font-medium text-muted-foreground border px-2.5 py-1 rounded-full">
              v{auth.version}
            </span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight">
            Authority for {agent ? agent.name : auth.agent_id}
          </h1>
          <p className="text-muted-foreground mt-1 font-mono text-sm">ID: {auth.id}</p>
        </div>
        
        <div className="flex items-center gap-2">
          {auth.status === "DRAFT" && (
            <Button onClick={() => activateMutation.mutate()} disabled={activateMutation.isPending}>
              <Play className="h-4 w-4 mr-2" /> Activate Authority
            </Button>
          )}
          {["DRAFT", "ACTIVE"].includes(auth.status) && (
            <Button variant="destructive" onClick={() => revokeMutation.mutate()} disabled={revokeMutation.isPending}>
              <Ban className="h-4 w-4 mr-2" /> Revoke
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Configuration Details</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-y-4 text-sm">
                <div>
                  <span className="font-semibold block text-muted-foreground mb-1">Agent</span>
                  <div className="font-medium">{agent ? agent.name : auth.agent_id}</div>
                </div>
                <div>
                  <span className="font-semibold block text-muted-foreground mb-1">Linked Intent</span>
                  {auth.intent_id ? (
                    <div className="flex items-center gap-1 text-primary">
                      <Target className="h-4 w-4" />
                      <span className="font-mono text-xs">{auth.intent_id}</span>
                    </div>
                  ) : (
                    <span className="text-muted-foreground">None</span>
                  )}
                </div>
                <div>
                  <span className="font-semibold block text-muted-foreground mb-1">Monetary Limit</span>
                  <div className="font-medium">
                    {auth.monetary_limit !== null 
                      ? new Intl.NumberFormat('en-IN', { style: 'currency', currency: auth.currency }).format(auth.monetary_limit)
                      : "Unlimited"
                    }
                  </div>
                </div>
                <div>
                  <span className="font-semibold block text-muted-foreground mb-1">Created At</span>
                  <div>{new Date(auth.created_at).toLocaleString()}</div>
                </div>
              </div>
              
              <div className="mt-6 pt-4 border-t">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold block text-muted-foreground">Allowed Capabilities</span>
                  {["DRAFT", "ACTIVE"].includes(auth.status) && (
                    <Button variant="outline" size="sm" onClick={handleOpenEdit}>
                      <Edit className="h-3.5 w-3.5 mr-1" />
                      Edit Capabilities
                    </Button>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  {auth.allowed_capabilities.map(cap => (
                    <span key={cap} className="px-2 py-1 bg-secondary text-secondary-foreground text-xs rounded-md font-medium">
                      {cap}
                    </span>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* SIMULATOR */}
          <Card className="border-primary/20 bg-primary/5">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5 text-primary" />
                Authority Simulator
              </CardTitle>
              <CardDescription>
                Test what happens if the agent attempts an action under this authority.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label>Capability</Label>
                  <select 
                    className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring"
                    value={simCapability}
                    onChange={(e) => setSimCapability(e.target.value)}
                  >
                    {ALL_CAPABILITIES.map(cap => (
                      <option key={cap} value={cap}>{cap}</option>
                    ))}
                  </select>
                </div>
                <div className="space-y-2">
                  <Label>Amount (optional)</Label>
                  <Input 
                    type="number" 
                    placeholder="e.g. 1000"
                    value={simAmount}
                    onChange={(e) => setSimAmount(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Currency</Label>
                  <select 
                    className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring"
                    value={simCurrency}
                    onChange={(e) => setSimCurrency(e.target.value)}
                  >
                    <option value="INR">INR</option>
                    <option value="USD">USD</option>
                  </select>
                </div>
              </div>
              
              <Button onClick={handleSimulate} disabled={simulateMutation.isPending}>
                <Zap className="h-4 w-4 mr-2" />
                Run Simulation
              </Button>

              {simResult && (
                <div className={`mt-4 p-4 rounded-lg border ${
                  !simResult.authorized 
                    ? 'bg-danger/10 border-danger/30' 
                    : simResult.requires_approval 
                      ? 'bg-warn/10 border-warn/30' 
                      : 'bg-safe/10 border-safe/30'
                }`}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className={`font-bold ${
                        !simResult.authorized 
                          ? 'text-danger' 
                          : simResult.requires_approval 
                            ? 'text-warn' 
                            : 'text-safe'
                      }`}>
                        {!simResult.authorized ? 'DENIED' : 'AUTHORIZED'}
                      </span>
                      {simResult.authorized && (
                        <span className={`text-xs px-2 py-0.5 rounded font-medium border ${
                          simResult.requires_approval 
                            ? 'bg-warn/20 border-warn/40 text-warn-foreground' 
                            : 'bg-safe/20 border-safe/40 text-safe-foreground'
                        }`}>
                          Action Gate: {simResult.requires_approval ? 'REVIEW (Approval Required)' : 'ALLOW'}
                        </span>
                      )}
                    </div>
                  </div>
                  {simResult.requires_approval && (
                    <p className="text-xs text-amber-500 font-medium mb-2">
                      ⚠️ This amount exceeds the configured approval threshold. Action Gate will require human approval before execution.
                    </p>
                  )}
                  <ul className="text-sm list-disc pl-5 space-y-1 text-muted-foreground">
                    {simResult.reasons.map((r: string, i: number) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                  
                  {auth.intent_id && (
                    <div className="mt-4 pt-3 border-t border-border/50 flex items-center justify-between text-sm">
                      <span className="font-medium text-muted-foreground">Intent Alignment:</span>
                      <span className={`font-bold ${
                        simResult.alignment_result === 'ALIGNED' ? 'text-safe' : 
                        simResult.alignment_result === 'MISALIGNED' ? 'text-danger' : 
                        'text-warn'
                      }`}>
                        {simResult.alignment_result}
                      </span>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Version History */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <History className="h-5 w-5" />
                Version History
              </CardTitle>
              <CardDescription>Immutable record of changes.</CardDescription>
            </CardHeader>
            <CardContent>
              {versionsLoading ? (
                <Skeleton className="h-32 w-full" />
              ) : versions.length === 0 ? (
                <p className="text-xs text-muted-foreground">No previous versions recorded.</p>
              ) : (
                <div className="relative border-l border-muted ml-3 space-y-6">
                  {[...versions]
                    .sort((a, b) => ((b.version_number ?? b.version ?? 0) - (a.version_number ?? a.version ?? 0)))
                    .map((v) => {
                      const vNum = v.version_number ?? v.version ?? 1;
                      const limit = v.monetary_limit ?? v.snapshot?.monetary_limit;
                      const curr = v.currency ?? v.snapshot?.currency ?? auth.currency;
                      return (
                        <div key={v.id} className="relative pl-6">
                          <div className={`absolute -left-[5px] top-1.5 h-2 w-2 rounded-full ${vNum === auth.version ? 'bg-primary ring-4 ring-primary/20' : 'bg-muted-foreground'}`} />
                          <div className="flex items-center justify-between">
                            <h4 className="text-sm font-semibold">Version {vNum}</h4>
                            <span className="text-xs text-muted-foreground">
                              {new Date(v.created_at).toLocaleDateString()}
                            </span>
                          </div>
                          <p className="text-xs text-muted-foreground mt-1">
                            {v.change_reason || (vNum === 1 ? "Initial delegation" : "Capabilities updated")}
                          </p>
                          {vNum !== auth.version && limit !== undefined && limit !== null && (
                            <div className="mt-2 text-xs text-muted-foreground">
                              Limit: {new Intl.NumberFormat('en-IN', { style: 'currency', currency: curr }).format(limit)}
                            </div>
                          )}
                        </div>
                      );
                    })}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Edit Capabilities Dialog */}
      <Dialog open={isEditModalOpen} onOpenChange={setIsEditModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Edit Allowed Capabilities</DialogTitle>
            <DialogDescription>
              Modify the canonical capabilities delegated to this agent. This will create a new immutable version of this authority.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="grid grid-cols-1 gap-2.5 max-h-[340px] overflow-y-auto p-1 border rounded-md bg-muted/20">
              {ALL_CAPABILITIES.map(cap => (
                <div key={cap} className="flex items-center space-x-2 p-1.5 hover:bg-muted/50 rounded">
                  <Checkbox 
                    id={`edit-cap-${cap}`}
                    checked={editCapabilities.includes(cap)}
                    onCheckedChange={() => handleToggleCapability(cap)}
                  />
                  <Label htmlFor={`edit-cap-${cap}`} className="text-sm font-medium cursor-pointer">
                    {cap}
                  </Label>
                </div>
              ))}
            </div>
            <p className="text-xs text-muted-foreground">
              Selected capabilities: {editCapabilities.length}
            </p>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSaveCapabilities} disabled={updateMutation.isPending || editCapabilities.length === 0}>
              {updateMutation.isPending ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Check className="h-4 w-4 mr-2" />
              )}
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
