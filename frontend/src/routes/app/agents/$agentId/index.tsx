import { useState, useEffect } from "react";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { agentsApi, AgentUpdate, AgentCapability } from "@/api/agents";
import { useAuth } from "@/lib/auth-context";
import { 
  ArrowLeft, Terminal, Pause, Edit, 
  Play, ShoppingBag, Plane, LineChart, Bot, AlertTriangle, Loader2, CheckCircle2, Save,
  Key, Copy, Plus, Trash2, Clock
} from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/app/agents/$agentId/")({
  component: AgentDetailsRoute,
});

function getAgentIcon(type: string) {
  switch (type) {
    case "SHOPPING": return ShoppingBag;
    case "PAYMENT": return LineChart;
    case "FINANCE": return LineChart;
    case "OPERATIONS": return Bot;
    default: return Bot;
  }
}

const SHOPPING_CAPABILITIES: { value: AgentCapability, label: string }[] = [
  { value: "SEARCH_PRODUCTS", label: "Search products" },
  { value: "COMPARE_PRODUCTS", label: "Compare products" },
  { value: "CREATE_CART", label: "Create cart" },
  { value: "MANAGE_CART", label: "Manage cart" },
  { value: "ADD_CART_ITEM", label: "Add cart item" },
  { value: "UPDATE_CART", label: "Update cart" },
  { value: "CREATE_ORDER", label: "Create order" },
  { value: "CANCEL_ORDER", label: "Cancel order" },
  { value: "PAY_ORDER", label: "Pay order" },
];

const FINANCIAL_CAPABILITIES: { value: AgentCapability, label: string }[] = [
  { value: "REQUEST_PAYMENT", label: "Request payment" },
  { value: "EXECUTE_PAYMENT", label: "Execute payment" },
  { value: "REQUEST_REFUND", label: "Request refund" },
];

function AgentDetailsRoute() {
  const { agentId } = Route.useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");

  const { data: agent, isLoading, isError } = useQuery({
    queryKey: ["agents", agentId],
    queryFn: () => agentsApi.get(agentId),
  });

  // Local state for capabilities form
  const [selectedCapabilities, setSelectedCapabilities] = useState<AgentCapability[]>([]);
  // Local state for financial form
  const [maxTxn, setMaxTxn] = useState<string>("");
  const [monthlyLimit, setMonthlyLimit] = useState<string>("");
  const [dailyLimit, setDailyLimit] = useState<string>("");
  const [approvalThreshold, setApprovalThreshold] = useState<string>("");
  const [currency, setCurrency] = useState<string>("INR");

  // Credentials
  const [isCreateCredModalOpen, setIsCreateCredModalOpen] = useState(false);
  const [newCredName, setNewCredName] = useState("");
  const [isSubmittingCred, setIsSubmittingCred] = useState(false);
  const [generatedSecret, setGeneratedSecret] = useState<{ clientId: string, secret: string } | null>(null);

  const { data: credentials = [], isLoading: credsLoading } = useQuery({
    queryKey: ["agents", agentId, "credentials"],
    queryFn: () => agentsApi.listCredentials(agentId),
    enabled: !!agent
  });

  const { data: activities = [], isLoading: activitiesLoading } = useQuery({
    queryKey: ["agents", agentId, "activity"],
    queryFn: () => agentsApi.listActivity(agentId),
    enabled: !!agent
  });


  const createCredMutation = useMutation({
    mutationFn: (name: string) => agentsApi.createCredential(agentId, name),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["agents", agentId, "credentials"] });
      queryClient.invalidateQueries({ queryKey: ["agents", agentId, "activity"] });
      setGeneratedSecret({ clientId: data.client_id, secret: data.client_secret });
      setIsCreateCredModalOpen(false);
      setNewCredName("");
      setIsSubmittingCred(false);
      toast.success("API key generated successfully");
    },
    onError: (err: any) => {
      setIsSubmittingCred(false);
      toast.error(err.response?.data?.detail || "Failed to generate API key");
    }
  });

  const revokeCredMutation = useMutation({
    mutationFn: (credentialId: string) => agentsApi.revokeCredential(agentId, credentialId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agents", agentId, "credentials"] });
      queryClient.invalidateQueries({ queryKey: ["agents", agentId, "activity"] });
      toast.success("API key revoked");
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || "Failed to revoke API key");
    }
  });

  useEffect(() => {
    if (agent) {
      setSelectedCapabilities(agent.capabilities || []);
      setMaxTxn(agent.max_transaction_amount?.toString() || "");
      setMonthlyLimit(agent.monthly_limit?.toString() || "");
      setDailyLimit(agent.daily_limit?.toString() || "");
      setApprovalThreshold(agent.approval_threshold?.toString() || "");
      setCurrency(agent.currency || "INR");
    }
  }, [agent]);

  const updateMutation = useMutation({
    mutationFn: (data: AgentUpdate) => agentsApi.update(agentId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agents", agentId] });
      queryClient.invalidateQueries({ queryKey: ["agents"] });
      setIsEditModalOpen(false);
      toast.success("Agent updated successfully");
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || "Failed to update agent");
    }
  });

  const statusMutation = useMutation({
    mutationFn: (status: "ACTIVE" | "PAUSED" | "REVOKED") => agentsApi.updateStatus(agentId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agents", agentId] });
      queryClient.invalidateQueries({ queryKey: ["agents", agentId, "activity"] });
      queryClient.invalidateQueries({ queryKey: ["agents"] });
      toast.success("Agent status updated");
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || "Failed to update agent status");
    }
  });

  const canManage = true; // Temporary default until role is correctly typed in AuthContext

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-24 text-muted-foreground animate-in fade-in">
        <Loader2 className="size-8 animate-spin" />
      </div>
    );
  }

  if (isError || !agent) {
    return (
      <div className="p-8 text-center animate-in fade-in">
        <AlertTriangle className="size-10 text-danger mx-auto mb-4" />
        <h2 className="text-xl font-bold mb-4">Agent not found or unable to load</h2>
        <Button onClick={() => navigate({ to: "/app/agents" })}>Back to Agents</Button>
      </div>
    );
  }

  const Icon = getAgentIcon(agent.type);

  const openEditModal = () => {
    setEditName(agent.name);
    setEditDescription(agent.description || "");
    setIsEditModalOpen(true);
  };

  const handleEditSave = () => {
    updateMutation.mutate({ name: editName, description: editDescription });
  };

  const handleCapabilityToggle = (cap: AgentCapability, checked: boolean) => {
    if (checked) {
      setSelectedCapabilities(prev => [...prev, cap]);
    } else {
      setSelectedCapabilities(prev => prev.filter(c => c !== cap));
    }
  };

  const saveCapabilities = () => {
    updateMutation.mutate({ capabilities: selectedCapabilities });
  };

  const saveFinancialLimits = () => {
    updateMutation.mutate({
      currency: currency || "INR",
      max_transaction_amount: maxTxn ? parseInt(maxTxn) : null,
      monthly_limit: monthlyLimit ? parseInt(monthlyLimit) : null,
      daily_limit: dailyLimit ? parseInt(dailyLimit) : null,
      approval_threshold: approvalThreshold ? parseInt(approvalThreshold) : null,
    });
  };

  return (
    <div className="space-y-6 animate-rise">
      {/* Header */}
      <div className="flex items-center text-sm text-muted-foreground mb-2">
        <Link to="/app/agents" className="hover:text-foreground transition-colors flex items-center">
          <ArrowLeft className="mr-1 size-4" />
          Agents
        </Link>
        <span className="mx-2">/</span>
        <span className="text-foreground">{agent.name}</span>
      </div>

      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4 pb-6 border-b border-border">
        <div className="flex items-start gap-4">
          <div className="flex size-14 items-center justify-center rounded-xl bg-surface border border-border shrink-0">
            <Icon className="size-7 text-foreground" />
          </div>
          <div>
            <h2 className="text-2xl font-bold tracking-tight">{agent.name}</h2>
            <div className="flex items-center gap-3 mt-2 text-sm">
              <span className="font-mono text-muted-foreground">{agent.id}</span>
              <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-surface-raised border border-border">
                {agent.status === 'ACTIVE' && <div className="size-2 rounded-full bg-safe animate-pulse-dot" />}
                <span className={`font-semibold tracking-wider text-xs ${
                  agent.status === 'ACTIVE' ? 'text-safe' : 
                  agent.status === 'PAUSED' ? 'text-warn' : 
                  agent.status === 'REVOKED' ? 'text-danger' : 'text-muted-foreground'
                }`}>
                  {agent.status}
                </span>
              </div>
            </div>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          {canManage && (
            <>
              {agent.status === 'ACTIVE' ? (
                <Button 
                  variant="outline" 
                  className="border-border bg-surface hover:text-warn hover:border-warn/50"
                  onClick={() => statusMutation.mutate("PAUSED")}
                  disabled={statusMutation.isPending}
                >
                  <Pause className="mr-2 size-4" /> Pause
                </Button>
              ) : agent.status === 'PAUSED' || agent.status === 'DRAFT' ? (
                <Button 
                  variant="outline" 
                  className="border-border bg-surface hover:text-safe hover:border-safe/50"
                  onClick={() => statusMutation.mutate("ACTIVE")}
                  disabled={statusMutation.isPending}
                >
                  <Play className="mr-2 size-4" /> Resume
                </Button>
              ) : null}
              
              <Button variant="outline" className="border-border bg-surface" onClick={openEditModal}>
                <Edit className="mr-2 size-4" /> Edit
              </Button>
            </>
          )}
          
          <Link to={`/app/agents/${agentId}/console/`}>
            <Button className="bg-primary text-primary-foreground hover:bg-primary/90">
              <Terminal className="mr-2 size-4" /> Open Console
            </Button>
          </Link>
        </div>
      </div>

      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="bg-surface border border-border p-1 w-full justify-start overflow-x-auto">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="capabilities">Capabilities</TabsTrigger>
          <TabsTrigger value="financial">Financial Authority</TabsTrigger>
          <TabsTrigger value="credentials">API Keys</TabsTrigger>
          <TabsTrigger value="activity">Activity</TabsTrigger>
        </TabsList>

        <div className="mt-6">
          <TabsContent value="overview" className="space-y-6 outline-none">
            <div className="grid md:grid-cols-2 gap-6">
              <Card className="bg-surface border-border">
                <CardHeader>
                  <CardTitle className="text-base font-semibold">Agent Details</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-y-6 gap-x-8 text-sm">
                    <div className="col-span-2">
                      <div className="text-muted-foreground mb-1">Description</div>
                      <div className="text-foreground">{agent.description || "No description provided."}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground mb-1">Type</div>
                      <div className="capitalize font-medium">{agent.type.toLowerCase()}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground mb-1">Created By</div>
                      <div>{agent.created_by || "System"}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground mb-1">Created</div>
                      <div>{new Date(agent.created_at).toLocaleString()}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground mb-1">Last Active</div>
                      <div>{agent.last_active_at ? new Date(agent.last_active_at).toLocaleString() : "Never"}</div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-surface border-border">
                <CardHeader>
                  <CardTitle className="text-base font-semibold">Financial Summary</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <div className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Max Transaction</div>
                      <div className="font-mono text-sm">{agent.max_transaction_amount !== null ? `${agent.currency || 'INR'} ${agent.max_transaction_amount.toLocaleString()}` : 'No limit'}</div>
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Require Approval Above</div>
                      <div className="font-mono text-sm">{agent.approval_threshold !== null ? `${agent.currency || 'INR'} ${agent.approval_threshold.toLocaleString()}` : 'No limit'}</div>
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Monthly Limit</div>
                      <div className="font-mono text-sm">{agent.monthly_limit !== null ? `${agent.currency || 'INR'} ${agent.monthly_limit.toLocaleString()}` : 'No limit'}</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="capabilities" className="outline-none">
            <Card className="bg-surface border-border max-w-3xl">
              <CardHeader>
                <CardTitle className="text-base font-semibold">Execution Boundary</CardTitle>
                <CardDescription>Select which tools and permissions this agent is authorized to use autonomously.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-8">
                <div>
                  <h3 className="text-sm font-semibold mb-4 text-foreground">Shopping Capabilities</h3>
                  <div className="space-y-3">
                    {SHOPPING_CAPABILITIES.map(cap => (
                      <div key={cap.value} className="flex items-center space-x-2">
                        <Checkbox 
                          id={`cap-${cap.value}`} 
                          checked={selectedCapabilities.includes(cap.value)}
                          onCheckedChange={(c) => handleCapabilityToggle(cap.value, c as boolean)}
                          disabled={!canManage}
                        />
                        <Label htmlFor={`cap-${cap.value}`} className="cursor-pointer">{cap.label}</Label>
                      </div>
                    ))}
                  </div>
                </div>
                
                <div>
                  <h3 className="text-sm font-semibold mb-4 text-foreground">Financial Capabilities</h3>
                  <div className="space-y-3">
                    {FINANCIAL_CAPABILITIES.map(cap => (
                      <div key={cap.value} className="flex items-center space-x-2">
                        <Checkbox 
                          id={`cap-${cap.value}`} 
                          checked={selectedCapabilities.includes(cap.value)}
                          onCheckedChange={(c) => handleCapabilityToggle(cap.value, c as boolean)}
                          disabled={!canManage}
                        />
                        <Label htmlFor={`cap-${cap.value}`} className="cursor-pointer">{cap.label}</Label>
                      </div>
                    ))}
                  </div>
                </div>

                {canManage && (
                  <div className="pt-4 border-t border-border flex justify-end">
                    <Button 
                      onClick={saveCapabilities} 
                      disabled={updateMutation.isPending}
                      className="bg-primary text-primary-foreground"
                    >
                      {updateMutation.isPending ? <Loader2 className="mr-2 size-4 animate-spin" /> : <Save className="mr-2 size-4" />}
                      Save Capabilities
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="financial" className="outline-none">
            <Card className="bg-surface border-border max-w-3xl">
              <CardHeader>
                <CardTitle className="text-base font-semibold">Authority Limits</CardTitle>
                <CardDescription>Define the maximum financial exposure allowed for this agent.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2 sm:col-span-2">
                    <Label htmlFor="currency">Authority Currency</Label>
                    <Select 
                      value={currency} 
                      onValueChange={(val) => setCurrency(val)} 
                      disabled={!canManage}
                    >
                      <SelectTrigger id="currency" className="bg-surface border-border font-mono max-w-xs">
                        <SelectValue placeholder="Select Currency" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="INR">INR (₹ - Indian Rupee)</SelectItem>
                        <SelectItem value="USD">USD ($ - US Dollar)</SelectItem>
                        <SelectItem value="EUR">EUR (€ - Euro)</SelectItem>
                        <SelectItem value="GBP">GBP (£ - British Pound)</SelectItem>
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground">All transaction caps and approval thresholds below are enforced in this currency.</p>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="monthlyLimit">Monthly Limit ({currency})</Label>
                    <Input 
                      id="monthlyLimit" 
                      type="number" 
                      className="bg-surface border-border font-mono" 
                      value={monthlyLimit}
                      onChange={e => setMonthlyLimit(e.target.value)}
                      disabled={!canManage}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="dailyLimit">Daily Limit ({currency})</Label>
                    <Input 
                      id="dailyLimit" 
                      type="number" 
                      className="bg-surface border-border font-mono" 
                      value={dailyLimit}
                      onChange={e => setDailyLimit(e.target.value)}
                      disabled={!canManage}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="maxTxn">Maximum Transaction ({currency})</Label>
                    <Input 
                      id="maxTxn" 
                      type="number" 
                      className="bg-surface border-border font-mono" 
                      value={maxTxn}
                      onChange={e => setMaxTxn(e.target.value)}
                      disabled={!canManage}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="approvalThreshold">Require Approval Above ({currency})</Label>
                    <Input 
                      id="approvalThreshold" 
                      type="number" 
                      className="bg-surface border-border font-mono text-warn" 
                      value={approvalThreshold}
                      onChange={e => setApprovalThreshold(e.target.value)}
                      disabled={!canManage}
                    />
                  </div>
                </div>

                {canManage && (
                  <div className="pt-4 border-t border-border flex justify-end">
                    <Button 
                      onClick={saveFinancialLimits} 
                      disabled={updateMutation.isPending}
                      className="bg-primary text-primary-foreground"
                    >
                      {updateMutation.isPending ? <Loader2 className="mr-2 size-4 animate-spin" /> : <Save className="mr-2 size-4" />}
                      Save Financial Limits
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="credentials" className="outline-none">
            <Card className="bg-surface border-border max-w-4xl">
              <CardHeader className="flex flex-row justify-between items-start">
                <div>
                  <CardTitle className="text-base font-semibold">API Credentials</CardTitle>
                  <CardDescription>Manage the API keys that allow external code to authenticate as this agent.</CardDescription>
                </div>
                {canManage && (
                  <Button 
                    onClick={() => setIsCreateCredModalOpen(true)}
                    className="bg-primary text-primary-foreground"
                    size="sm"
                  >
                    <Plus className="mr-2 size-4" /> Generate Key
                  </Button>
                )}
              </CardHeader>
              <CardContent>
                {credsLoading ? (
                  <div className="flex justify-center p-8"><Loader2 className="animate-spin size-6 text-muted-foreground" /></div>
                ) : credentials.length === 0 ? (
                  <div className="text-center text-muted-foreground py-12 border border-dashed border-border rounded-lg bg-background/50">
                    <Key className="size-8 mx-auto mb-3 opacity-20" />
                    <p>No active API credentials.</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {credentials.map(cred => (
                      <div key={cred.id} className="flex flex-col sm:flex-row justify-between items-start sm:items-center p-4 border border-border rounded-lg bg-background">
                        <div>
                          <div className="font-semibold text-sm flex items-center gap-2">
                            {cred.name}
                            {cred.status === "ACTIVE" ? (
                              <span className="text-[10px] bg-safe/10 text-safe px-2 py-0.5 rounded-full font-bold">ACTIVE</span>
                            ) : (
                              <span className="text-[10px] bg-danger/10 text-danger px-2 py-0.5 rounded-full font-bold">REVOKED</span>
                            )}
                          </div>
                          <div className="text-xs text-muted-foreground font-mono mt-1">Client ID: {cred.client_id}</div>
                          <div className="text-xs text-muted-foreground mt-1">
                            Created: {new Date(cred.created_at).toLocaleDateString()}
                          </div>
                        </div>
                        {canManage && cred.status === "ACTIVE" && (
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            className="text-danger hover:text-danger hover:bg-danger/10 mt-3 sm:mt-0"
                            onClick={() => {
                              if (confirm("Are you sure you want to revoke this credential? Any systems using it will immediately lose access.")) {
                                revokeCredMutation.mutate(cred.id);
                              }
                            }}
                            disabled={revokeCredMutation.isPending}
                          >
                            <Trash2 className="size-4 mr-2" /> Revoke
                          </Button>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="activity" className="outline-none">
            <Card className="bg-surface border-border">
              <CardHeader>
                <CardTitle className="text-base font-semibold">Audit Log</CardTitle>
                <CardDescription>Immutable record of all lifecycle and security events for this agent.</CardDescription>
              </CardHeader>
              <CardContent>
                {activitiesLoading ? (
                  <div className="flex justify-center p-8"><Loader2 className="animate-spin size-6 text-muted-foreground" /></div>
                ) : activities.length === 0 ? (
                  <div className="text-center text-muted-foreground py-12 border border-dashed border-border rounded-lg bg-background/50">
                    <Clock className="size-8 mx-auto mb-3 opacity-20" />
                    <p>No activity recorded yet.</p>
                  </div>
                ) : (
                  <div className="space-y-4 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-border before:to-transparent">
                    {activities.map((activity, i) => (
                      <div key={activity.id} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                        <div className="flex items-center justify-center w-10 h-10 rounded-full border border-border bg-surface shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 shadow-sm z-10 text-muted-foreground">
                          {activity.action === "CREATED" && <CheckCircle2 className="size-4" />}
                          {activity.action === "UPDATED" && <Edit className="size-4" />}
                          {activity.action === "STATUS_CHANGED" && <Pause className="size-4" />}
                          {activity.action === "CREDENTIAL_CREATED" && <Plus className="size-4" />}
                          {activity.action === "CREDENTIAL_REVOKED" && <Trash2 className="size-4" />}
                        </div>
                        <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] p-4 rounded-lg border border-border bg-background shadow-sm">
                          <div className="flex items-center justify-between mb-1">
                            <h4 className="font-semibold text-sm">
                              {activity.action.replace("_", " ")}
                            </h4>
                            <time className="text-xs text-muted-foreground">
                              {activity.created_at ? new Date(activity.created_at).toLocaleString() : "Timestamp unavailable"}
                            </time>
                          </div>
                          <div className="text-sm text-muted-foreground">
                            {activity.action === "STATUS_CHANGED" && (
                              <span>Changed status from <strong className="text-foreground">{activity.details.old_status}</strong> to <strong className="text-foreground">{activity.details.new_status}</strong>.</span>
                            )}
                            {activity.action === "CREDENTIAL_CREATED" && (
                              <span>Generated API key <strong className="text-foreground">{activity.details.credential_name}</strong>.</span>
                            )}
                            {activity.action === "CREDENTIAL_REVOKED" && (
                              <span>Revoked API key <strong className="text-foreground">{activity.details.credential_name}</strong>.</span>
                            )}
                            {activity.action === "CREATED" && (
                              <span>Created agent of type <strong className="text-foreground">{activity.details.type}</strong>.</span>
                            )}
                            {activity.action === "UPDATED" && (
                              <span>Updated capabilities and limits.</span>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </div>
      </Tabs>

      {/* Create Credential Modal */}
      <Dialog open={isCreateCredModalOpen} onOpenChange={setIsCreateCredModalOpen}>
        <DialogContent className="sm:max-w-[425px] bg-background border-border">
          <DialogHeader>
            <DialogTitle>Generate API Key</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm text-muted-foreground mb-4">
              Create a new set of credentials for this agent. You will only be shown the secret key once.
            </p>
            <div className="space-y-2">
              <Label htmlFor="credName">Key Name</Label>
              <Input
                id="credName"
                placeholder="e.g. Production Microservice"
                value={newCredName}
                onChange={(e) => setNewCredName(e.target.value)}
                className="bg-surface border-border"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => { setIsCreateCredModalOpen(false); setIsSubmittingCred(false); }}>Cancel</Button>
            <Button 
              onClick={() => {
                if (isSubmittingCred || !newCredName.trim()) return;
                setIsSubmittingCred(true);
                createCredMutation.mutate(newCredName);
              }} 
              disabled={isSubmittingCred || !newCredName.trim()}
              className="bg-primary text-primary-foreground"
            >
              {isSubmittingCred ? "Generating..." : "Generate Key"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Show Secret Modal */}
      <Dialog open={!!generatedSecret} onOpenChange={() => setGeneratedSecret(null)}>
        <DialogContent className="sm:max-w-[500px] bg-background border-border">
          <DialogHeader>
            <DialogTitle>API Key Generated</DialogTitle>
          </DialogHeader>
          <div className="py-4 space-y-6">
            <div className="p-3 bg-warn/10 text-warn border border-warn/20 rounded-md text-sm">
              <AlertTriangle className="size-4 inline mr-2 -mt-0.5" />
              <strong>Important:</strong> Please copy this secret key now. You will not be able to see it again.
            </div>
            
            <div className="space-y-2">
              <Label>Client ID</Label>
              <div className="flex">
                <Input readOnly value={generatedSecret?.clientId || ""} className="bg-surface border-border font-mono rounded-r-none" />
                <Button 
                  variant="outline" 
                  className="rounded-l-none border-l-0 bg-surface border-border"
                  onClick={() => navigator.clipboard.writeText(generatedSecret?.clientId || "")}
                >
                  <Copy className="size-4" />
                </Button>
              </div>
            </div>

            <div className="space-y-2">
              <Label>Client Secret</Label>
              <div className="flex">
                <Input readOnly value={generatedSecret?.secret || ""} className="bg-surface border-border font-mono rounded-r-none" />
                <Button 
                  variant="outline" 
                  className="rounded-l-none border-l-0 bg-surface border-border"
                  onClick={() => navigator.clipboard.writeText(generatedSecret?.secret || "")}
                >
                  <Copy className="size-4" />
                </Button>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button onClick={() => setGeneratedSecret(null)} className="bg-primary text-primary-foreground">
              I have copied the secret
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Modal */}
      <Dialog open={isEditModalOpen} onOpenChange={setIsEditModalOpen}>
        <DialogContent className="sm:max-w-[425px] bg-background border-border">
          <DialogHeader>
            <DialogTitle>Edit Agent</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="name" className="text-right">
                Name
              </Label>
              <Input
                id="name"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                className="col-span-3 bg-surface border-border"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="description" className="text-right">
                Description
              </Label>
              <Input
                id="description"
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                className="col-span-3 bg-surface border-border"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setIsEditModalOpen(false)}>Cancel</Button>
            <Button 
              onClick={handleEditSave} 
              disabled={updateMutation.isPending || !editName.trim()}
              className="bg-primary text-primary-foreground"
            >
              {updateMutation.isPending ? "Saving..." : "Save changes"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
