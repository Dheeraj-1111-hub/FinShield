import { useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { intentsApi, Intent } from "@/api/intents";
import { 
  Target, Search, Plus, Filter, LayoutGrid, List,
  Play, Pause, Ban, AlertTriangle, CheckCircle, FileText
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

export const Route = createFileRoute("/app/intents/")({
  component: IntentsRoute,
});

function getStatusDisplay(status: string) {
  switch (status) {
    case "ACTIVE": return { icon: Play, color: "text-safe", bg: "bg-safe/20", text: "ACTIVE" };
    case "DRAFT": return { icon: FileText, color: "text-muted-foreground", bg: "bg-muted/50", text: "DRAFT" };
    case "PAUSED": return { icon: Pause, color: "text-warn", bg: "bg-warn/20", text: "PAUSED" };
    case "REVOKED": return { icon: Ban, color: "text-danger", bg: "bg-danger/20", text: "REVOKED" };
    case "COMPLETED": return { icon: CheckCircle, color: "text-safe", bg: "bg-safe/20", text: "COMPLETED" };
    case "ARCHIVED": return { icon: AlertTriangle, color: "text-muted-foreground", bg: "bg-muted/50", text: "ARCHIVED" };
    default: return { icon: Target, color: "text-muted-foreground", bg: "bg-muted/50", text: status };
  }
}

function IntentsRoute() {
  const [viewMode, setViewMode] = useState<"grid" | "list">("list");
  const [searchQuery, setSearchQuery] = useState("");
  const navigate = useNavigate();

  const { data: intents = [], isLoading } = useQuery({
    queryKey: ["intents"],
    queryFn: () => intentsApi.list()
  });

  const filteredIntents = intents.filter(i => 
    i.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (i.natural_language_request && i.natural_language_request.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div className="w-full max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <Target className="h-8 w-8 text-primary" />
            Intent Center
          </h1>
          <p className="text-muted-foreground mt-1">
            Define and track user objectives to constrain agent behavior.
          </p>
        </div>
        <Button onClick={() => navigate({ to: "/app/intents/new" })}>
          <Plus className="h-4 w-4 mr-2" />
          Create Intent
        </Button>
      </div>

      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-card border rounded-lg p-3">
        <div className="relative w-full sm:w-96">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input 
            placeholder="Search intents..." 
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
      ) : filteredIntents.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 text-center border rounded-xl border-dashed bg-card/30">
          <div className="bg-primary/10 p-4 rounded-full mb-4">
            <Target className="h-8 w-8 text-primary" />
          </div>
          <h3 className="text-xl font-semibold mb-2">No intents found</h3>
          <p className="text-muted-foreground max-w-md mb-6">
            You haven't defined any user intents yet. Intents define the boundaries of what an agent is trying to accomplish.
          </p>
          <Button onClick={() => navigate({ to: "/app/intents/new" })}>
            Create your first Intent
          </Button>
        </div>
      ) : viewMode === "grid" ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredIntents.map(intent => {
            const status = getStatusDisplay(intent.status);
            const StatusIcon = status.icon;
            
            return (
              <Card 
                key={intent.id} 
                className="overflow-hidden hover:border-primary/50 transition-colors cursor-pointer group"
                onClick={() => navigate({ to: `/app/intents/${intent.id}` })}
              >
                <CardHeader className="pb-3 flex flex-row items-start justify-between">
                  <div>
                    <CardTitle className="text-lg line-clamp-1 group-hover:text-primary transition-colors">
                      {intent.title}
                    </CardTitle>
                    <div className="flex items-center gap-2 mt-2">
                      <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${status.bg} ${status.color}`}>
                        <StatusIcon className="h-3 w-3" />
                        {status.text}
                      </span>
                      <span className="text-xs text-muted-foreground border px-2 py-0.5 rounded-full">
                        v{intent.version}
                      </span>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground line-clamp-2 mb-4 h-10">
                    {intent.natural_language_request || "No description provided."}
                  </p>
                  <div className="flex items-center justify-between text-xs text-muted-foreground pt-4 border-t">
                    <span>Type: {intent.intent_type}</span>
                    <span>{new Date(intent.created_at).toLocaleDateString()}</span>
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
                <th className="px-4 py-3 font-medium">Intent</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Type</th>
                <th className="px-4 py-3 font-medium">Version</th>
                <th className="px-4 py-3 font-medium">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {filteredIntents.map(intent => {
                const status = getStatusDisplay(intent.status);
                const StatusIcon = status.icon;
                
                return (
                  <tr 
                    key={intent.id} 
                    className="hover:bg-muted/30 cursor-pointer transition-colors"
                    onClick={() => navigate({ to: `/app/intents/${intent.id}` })}
                  >
                    <td className="px-4 py-3">
                      <div className="font-medium text-foreground">{intent.title}</div>
                      <div className="text-xs text-muted-foreground truncate max-w-md">{intent.natural_language_request}</div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${status.bg} ${status.color}`}>
                        <StatusIcon className="h-3 w-3" />
                        {status.text}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">{intent.intent_type}</td>
                    <td className="px-4 py-3 text-muted-foreground">v{intent.version}</td>
                    <td className="px-4 py-3 text-muted-foreground">{new Date(intent.created_at).toLocaleDateString()}</td>
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
