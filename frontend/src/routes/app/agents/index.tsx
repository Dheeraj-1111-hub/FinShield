import { useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator } from "@/components/ui/dropdown-menu";
import { Popover, PopoverTrigger, PopoverContent } from "@/components/ui/popover";
import { CreateAgentWizard } from "@/components/agents/CreateAgentWizard";
import { agentsApi, Agent } from "@/api/agents";
import { useAuth } from "@/lib/auth-context";
import { 
  Bot, Plane, LineChart, Search, Filter, ArrowDownUp, 
  LayoutGrid, List, MoreVertical, Play, Pause, 
  Ban, AlertTriangle, ArrowRight, ShoppingBag, Loader2
} from "lucide-react";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";

export const Route = createFileRoute("/app/agents/")({
  component: AgentsRoute,
});

function getAgentIcon(type: string) {
  switch (type) {
    case "SHOPPING": return ShoppingBag;
    case "PAYMENT": return LineChart; // Use LineChart for payment for now, or something else
    case "FINANCE": return LineChart;
    case "OPERATIONS": return Bot;
    default: return Bot;
  }
}

function getStatusDisplay(status: string) {
  switch (status) {
    case "ACTIVE": return { icon: Play, color: "text-safe", bg: "bg-safe", text: "ACTIVE" };
    case "DRAFT": return { icon: Pause, color: "text-muted-foreground", bg: "bg-muted-foreground", text: "DRAFT" };
    case "PAUSED": return { icon: Pause, color: "text-warn", bg: "bg-warn", text: "PAUSED" };
    case "REVOKED": return { icon: Ban, color: "text-danger", bg: "bg-danger", text: "REVOKED" };
    case "ARCHIVED": return { icon: AlertTriangle, color: "text-muted-foreground", bg: "bg-muted-foreground", text: "ARCHIVED" };
    default: return { icon: Bot, color: "text-muted-foreground", bg: "bg-muted-foreground", text: status };
  }
}

function AgentsRoute() {
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [searchQuery, setSearchQuery] = useState("");
  const navigate = useNavigate();
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string, status: "ACTIVE" | "PAUSED" | "REVOKED" }) => agentsApi.updateStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agents"] });
      toast.success("Agent status updated");
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || "Failed to update agent status");
    }
  });

  const { data: agents = [], isLoading, isError, refetch } = useQuery({
    queryKey: ["agents"],
    queryFn: agentsApi.list,
  });

  const activeCount = agents.filter(a => a.status === "ACTIVE").length;
  const revokedCount = agents.filter(a => a.status === "REVOKED").length;
  
  const filteredAgents = agents.filter(a => 
    a.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
    a.type.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const canManage = true; // Temporary default until role is correctly typed in AuthContext

  if (isLoading) {
    return (
      <div className="space-y-8 animate-in fade-in">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-semibold text-foreground">Agents</h2>
            <p className="text-sm text-muted-foreground mt-1">Manage autonomous financial agents</p>
          </div>
        </div>
        <div className="flex gap-4 mb-8">
          <Skeleton className="h-10 w-24 rounded-lg" />
          <Skeleton className="h-10 w-24 rounded-lg" />
          <Skeleton className="h-10 w-24 rounded-lg" />
        </div>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map(i => (
            <Card key={i} className="bg-surface border-border h-[200px] flex flex-col p-6 space-y-4">
              <div className="flex items-start gap-4">
                <Skeleton className="size-10 rounded-lg shrink-0" />
                <div className="space-y-2 flex-1">
                  <Skeleton className="h-5 w-1/2" />
                  <Skeleton className="h-3 w-1/4" />
                </div>
              </div>
              <Skeleton className="h-3 w-full mt-4" />
              <Skeleton className="h-3 w-2/3" />
              <div className="mt-auto flex justify-between">
                <Skeleton className="h-4 w-1/4" />
                <Skeleton className="h-4 w-1/4" />
              </div>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="space-y-8 animate-in fade-in">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-semibold text-foreground">Agents</h2>
            <p className="text-sm text-muted-foreground mt-1">Manage autonomous financial agents</p>
          </div>
        </div>
        <div className="flex flex-col items-center justify-center p-24 border border-danger/20 rounded-lg bg-danger/5">
          <AlertTriangle className="size-10 text-danger mb-4" />
          <h3 className="text-xl font-semibold text-danger mb-2">Unable to load agents.</h3>
          <p className="text-muted-foreground mb-6">Something went wrong while retrieving your workspace agents.</p>
          <Button onClick={() => refetch()} variant="outline">Retry</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-rise">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-foreground">Agents</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Manage autonomous financial agents, capabilities, and financial authority.
          </p>
        </div>
        
        <div className="flex items-center gap-2 w-full md:w-auto">
          {agents.length > 0 && (
            <div className="relative flex-1 md:w-64">
              <Search className="absolute left-2.5 top-2.5 size-4 text-muted-foreground" />
              <Input 
                type="text" 
                placeholder="Search agents..." 
                className="pl-9 bg-surface border-border"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
              />
            </div>
          )}
          
          {canManage && <CreateAgentWizard />}
        </div>
      </div>

      {agents.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-32 px-4 border border-dashed border-border rounded-xl bg-surface/50">
          <div className="size-16 rounded-full bg-primary/10 flex items-center justify-center mb-6">
            <Bot className="size-8 text-primary" />
          </div>
          <h3 className="text-xl font-semibold text-foreground mb-2">No agents yet</h3>
          <p className="text-muted-foreground text-center max-w-md mb-8">
            Create your first autonomous agent and define exactly what it is allowed to do.
          </p>
          {canManage ? (
            <CreateAgentWizard />
          ) : (
            <p className="text-sm font-medium text-warn">You do not have permission to create agents.</p>
          )}
        </div>
      ) : (
        <>
          {/* System Summary Strip */}
          <div className="flex flex-wrap items-center gap-4 p-4 rounded-lg border border-border bg-surface text-sm">
            <div className="flex items-center gap-2 px-2">
              <span className="font-semibold text-foreground">{agents.length}</span>
              <span className="text-muted-foreground uppercase text-xs tracking-wider">Total</span>
            </div>
            <div className="w-px h-4 bg-border" />
            <div className="flex items-center gap-2 px-2">
              <span className="font-semibold text-foreground">{activeCount}</span>
              <span className="text-muted-foreground uppercase text-xs tracking-wider">Active</span>
            </div>
            <div className="w-px h-4 bg-border" />
            <div className="flex items-center gap-2 px-2">
              <span className="font-semibold text-foreground">{revokedCount}</span>
              <span className="text-muted-foreground uppercase text-xs tracking-wider">Revoked</span>
            </div>
          </div>

          {/* Agents Grid */}
          <div className={`grid gap-6 ${viewMode === 'grid' ? 'md:grid-cols-2 lg:grid-cols-3' : 'grid-cols-1'}`}>
            {filteredAgents.map(agent => {
              const Icon = getAgentIcon(agent.type);
              const status = getStatusDisplay(agent.status);

              return (
                <Card 
                  key={agent.id} 
                  className="relative overflow-hidden bg-surface hover:bg-surface-raised transition-colors border-border flex flex-col group cursor-pointer"
                  onClick={() => navigate({ to: `/app/agents/${agent.id}` })}
                >
                  <CardHeader className="pb-4">
                    <div className="flex justify-between items-start">
                      <div className="flex items-center gap-3">
                        <div className={`flex size-10 items-center justify-center rounded-lg bg-background border border-border`}>
                          <Icon className="size-5 text-foreground" />
                        </div>
                        <div>
                          <CardTitle className="text-base font-semibold group-hover:text-primary transition-colors">{agent.name}</CardTitle>
                          <div className="text-xs text-muted-foreground font-mono mt-1 capitalize">{agent.type.toLowerCase()}</div>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        <div className="flex items-center gap-1.5">
                          {agent.status === "ACTIVE" && <div className="size-2 rounded-full bg-safe animate-pulse-dot" />}
                          <span className={`text-xs font-semibold tracking-wider ${status.color}`}>
                            {status.text}
                          </span>
                        </div>
                        
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild onClick={e => e.stopPropagation()}>
                            <Button variant="ghost" size="icon" className="size-8 text-muted-foreground">
                              <MoreVertical className="size-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={e => { e.stopPropagation(); navigate({ to: `/app/agents/${agent.id}` }); }}>
                              View Details
                            </DropdownMenuItem>
                            
                            {canManage && (
                              <>
                                <DropdownMenuSeparator />
                                {agent.status === 'ACTIVE' ? (
                                  <DropdownMenuItem onClick={e => { e.stopPropagation(); statusMutation.mutate({ id: agent.id, status: 'PAUSED' }); }} className="text-warn focus:text-warn">Pause Agent</DropdownMenuItem>
                                ) : agent.status === 'PAUSED' || agent.status === 'DRAFT' ? (
                                  <DropdownMenuItem onClick={e => { e.stopPropagation(); statusMutation.mutate({ id: agent.id, status: 'ACTIVE' }); }} className="text-safe focus:text-safe">Activate Agent</DropdownMenuItem>
                                ) : null}
                                <DropdownMenuSeparator />
                                <DropdownMenuItem onClick={e => { e.stopPropagation(); statusMutation.mutate({ id: agent.id, status: 'REVOKED' }); }} className="text-danger focus:text-danger">Revoke Authority</DropdownMenuItem>
                              </>
                            )}
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                    </div>
                    
                    <div className="text-sm text-muted-foreground mt-3 line-clamp-2 min-h-[40px]">
                      {agent.description || "No description provided."}
                    </div>
                  </CardHeader>
                  
                  <div className="px-6 pb-4 flex-1">
                    <div className="h-px bg-border w-full mb-4" />
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-1">Capabilities</div>
                        <div className="text-xs font-medium">{agent.capabilities.length} granted</div>
                      </div>
                      <div>
                        <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-1">Created</div>
                        <div className="text-xs font-medium">{new Date(agent.created_at).toLocaleDateString()}</div>
                      </div>
                    </div>
                  </div>
                  
                  <CardContent className="pt-0">
                    <div className="flex items-center justify-between mt-2 pt-4 border-t border-border">
                      <span className="text-xs text-muted-foreground">
                        Last active: {agent.last_active_at ? new Date(agent.last_active_at).toLocaleDateString() : 'Never'}
                      </span>
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        className="h-8 text-xs font-medium group-hover:bg-primary/10 group-hover:text-primary transition-colors"
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate({ to: `/app/agents/${agent.id}` });
                        }}
                      >
                        Open <ArrowRight className="ml-1.5 size-3" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
