import { useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { authoritiesApi } from "@/api/authorities";
import { agentsApi } from "@/api/agents";
import { 
  ShieldCheck, Search, Plus, Filter, LayoutGrid, List,
  Play, Ban, AlertTriangle, Clock
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

export const Route = createFileRoute("/app/authorities/")({
  component: AuthoritiesRoute,
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

function formatCurrency(amount: number | null, currency: string) {
  if (amount === null) return "Unlimited";
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: currency }).format(amount);
}

function AuthoritiesRoute() {
  const [viewMode, setViewMode] = useState<"grid" | "list">("list");
  const [searchQuery, setSearchQuery] = useState("");
  const navigate = useNavigate();

  const { data: authorities = [], isLoading: authLoading } = useQuery({
    queryKey: ["authorities"],
    queryFn: () => authoritiesApi.list()
  });

  const { data: agents = [], isLoading: agentsLoading } = useQuery({
    queryKey: ["agents"],
    queryFn: agentsApi.list
  });

  const isLoading = authLoading || agentsLoading;

  const agentMap = new Map(agents.map(a => [a.id, a]));

  const filteredAuthorities = authorities.filter(auth => {
    const agent = agentMap.get(auth.agent_id);
    const agentName = agent ? agent.name.toLowerCase() : "";
    return auth.id.toLowerCase().includes(searchQuery.toLowerCase()) || agentName.includes(searchQuery.toLowerCase());
  });

  return (
    <div className="w-full max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <ShieldCheck className="h-8 w-8 text-primary" />
            Authority Center
          </h1>
          <p className="text-muted-foreground mt-1">
            Manage permissions, limits, and constraints granted to your AI agents.
          </p>
        </div>
        <Button onClick={() => navigate({ to: "/app/authorities/new" })}>
          <Plus className="h-4 w-4 mr-2" />
          Delegate Authority
        </Button>
      </div>

      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-card border rounded-lg p-3">
        <div className="relative w-full sm:w-96">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input 
            placeholder="Search by agent name..." 
            className="pl-9 bg-background"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <Button variant="outline" size="sm" className="hidden sm:flex">
            <Filter className="h-4 w-4 mr-2" />
            Filter
          </Button>
          <div className="flex bg-muted p-1 rounded-md ml-auto">
            <Button 
              variant="ghost" 
              size="icon" 
              className={`h-7 w-7 rounded-sm ${viewMode === 'grid' ? 'bg-background shadow-sm' : ''}`}
              onClick={() => setViewMode("grid")}
            >
              <LayoutGrid className="h-4 w-4" />
            </Button>
            <Button 
              variant="ghost" 
              size="icon" 
              className={`h-7 w-7 rounded-sm ${viewMode === 'list' ? 'bg-background shadow-sm' : ''}`}
              onClick={() => setViewMode("list")}
            >
              <List className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3, 4, 5, 6].map(i => (
            <Skeleton key={i} className="h-48 w-full rounded-xl" />
          ))}
        </div>
      ) : filteredAuthorities.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 text-center border rounded-xl border-dashed bg-card/30">
          <div className="bg-primary/10 p-4 rounded-full mb-4">
            <ShieldCheck className="h-8 w-8 text-primary" />
          </div>
          <h3 className="text-xl font-semibold mb-2">No authorities found</h3>
          <p className="text-muted-foreground max-w-md mb-6">
            You haven't delegated any authorities to your agents yet. Authorities link an Agent with an Intent and specify limits.
          </p>
          <Button onClick={() => navigate({ to: "/app/authorities/new" })}>
            Delegate Authority
          </Button>
        </div>
      ) : viewMode === "grid" ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredAuthorities.map(auth => {
            const status = getStatusDisplay(auth.status);
            const StatusIcon = status.icon;
            const agent = agentMap.get(auth.agent_id);
            
            return (
              <Card 
                key={auth.id} 
                className="overflow-hidden hover:border-primary/50 transition-colors cursor-pointer group"
                onClick={() => navigate({ to: `/app/authorities/${auth.id}` })}
              >
                <CardHeader className="pb-3 flex flex-row items-start justify-between">
                  <div>
                    <CardTitle className="text-lg line-clamp-1 group-hover:text-primary transition-colors">
                      {agent ? agent.name : "Unknown Agent"}
                    </CardTitle>
                    <div className="flex items-center gap-2 mt-2">
                      <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${status.bg} ${status.color}`}>
                        <StatusIcon className="h-3 w-3" />
                        {status.text}
                      </span>
                      <span className="text-xs text-muted-foreground border px-2 py-0.5 rounded-full">
                        v{auth.version}
                      </span>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="text-sm">
                      <span className="text-muted-foreground block text-xs mb-1">Capabilities</span>
                      <div className="flex flex-wrap gap-1">
                        {auth.allowed_capabilities.length > 0 ? (
                          auth.allowed_capabilities.slice(0, 3).map(cap => (
                            <span key={cap} className="px-1.5 py-0.5 bg-secondary text-secondary-foreground text-[10px] rounded">
                              {cap}
                            </span>
                          ))
                        ) : (
                          <span className="text-muted-foreground text-xs">None</span>
                        )}
                        {auth.allowed_capabilities.length > 3 && (
                          <span className="px-1.5 py-0.5 bg-secondary text-secondary-foreground text-[10px] rounded">
                            +{auth.allowed_capabilities.length - 3} more
                          </span>
                        )}
                      </div>
                    </div>
                    
                    <div className="flex justify-between items-center text-sm pt-2 border-t">
                      <span className="text-muted-foreground text-xs">Limit</span>
                      <span className="font-medium">
                        {formatCurrency(auth.monetary_limit, auth.currency)}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      ) : (
        <div className="border rounded-xl bg-card overflow-hidden">
          <table className="w-full text-sm text-left">
            <thead className="bg-muted/50 text-muted-foreground uppercase text-xs">
              <tr>
                <th className="px-4 py-3 font-medium">Agent</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Capabilities</th>
                <th className="px-4 py-3 font-medium">Limit</th>
                <th className="px-4 py-3 font-medium">Intent Attached</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {filteredAuthorities.map(auth => {
                const status = getStatusDisplay(auth.status);
                const StatusIcon = status.icon;
                const agent = agentMap.get(auth.agent_id);
                
                return (
                  <tr 
                    key={auth.id} 
                    className="hover:bg-muted/30 cursor-pointer transition-colors"
                    onClick={() => navigate({ to: `/app/authorities/${auth.id}` })}
                  >
                    <td className="px-4 py-3">
                      <div className="font-medium text-foreground">{agent ? agent.name : auth.agent_id}</div>
                      <div className="text-xs text-muted-foreground font-mono mt-0.5">{auth.id.substring(0, 12)}...</div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${status.bg} ${status.color}`}>
                        <StatusIcon className="h-3 w-3" />
                        {status.text}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-1 flex-wrap">
                        {auth.allowed_capabilities.length} capabilities
                      </div>
                    </td>
                    <td className="px-4 py-3 font-medium text-foreground">
                      {formatCurrency(auth.monetary_limit, auth.currency)}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {auth.intent_id ? (
                        <span className="px-2 py-1 bg-primary/10 text-primary text-xs rounded-full">Yes</span>
                      ) : (
                        <span className="px-2 py-1 bg-muted text-muted-foreground text-xs rounded-full">No</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
