import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { intentsApi } from "@/api/intents";
import { 
  Target, ArrowLeft, Play, Pause, Ban,
  CheckCircle, FileText, AlertTriangle, History
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";

export const Route = createFileRoute("/app/intents/$intentId/")({
  component: IntentDetailRoute,
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

function IntentDetailRoute() {
  const { intentId } = Route.useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: intent, isLoading } = useQuery({
    queryKey: ["intents", intentId],
    queryFn: () => intentsApi.get(intentId)
  });

  const { data: versions = [], isLoading: versionsLoading } = useQuery({
    queryKey: ["intents", intentId, "versions"],
    queryFn: () => intentsApi.getVersions(intentId)
  });

  const confirmMutation = useMutation({
    mutationFn: () => intentsApi.confirm(intentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["intents", intentId] });
      toast.success("Intent confirmed and marked as ACTIVE");
    }
  });

  const pauseMutation = useMutation({
    mutationFn: () => intentsApi.pause(intentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["intents", intentId] });
      toast.success("Intent paused");
    }
  });

  const revokeMutation = useMutation({
    mutationFn: () => intentsApi.revoke(intentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["intents", intentId] });
      toast.success("Intent revoked");
    }
  });

  if (isLoading || !intent) {
    return (
      <div className="w-full max-w-5xl mx-auto space-y-6">
        <Skeleton className="h-12 w-1/3" />
        <Skeleton className="h-[400px] w-full" />
      </div>
    );
  }

  const status = getStatusDisplay(intent.status);
  const StatusIcon = status.icon;

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
              v{intent.version}
            </span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight">{intent.title}</h1>
          <p className="text-muted-foreground mt-1 font-mono text-sm">ID: {intent.id}</p>
        </div>
        
        <div className="flex items-center gap-2">
          {intent.status === "DRAFT" && (
            <Button onClick={() => confirmMutation.mutate()} disabled={confirmMutation.isPending}>
              <CheckCircle className="h-4 w-4 mr-2" /> Confirm Intent
            </Button>
          )}
          {intent.status === "ACTIVE" && (
            <Button variant="outline" className="text-warn" onClick={() => pauseMutation.mutate()} disabled={pauseMutation.isPending}>
              <Pause className="h-4 w-4 mr-2" /> Pause
            </Button>
          )}
          {["DRAFT", "ACTIVE", "PAUSED"].includes(intent.status) && (
            <Button variant="destructive" onClick={() => revokeMutation.mutate()} disabled={revokeMutation.isPending}>
              <Ban className="h-4 w-4 mr-2" /> Revoke
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Details & Constraints */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Natural Language Request</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="p-4 bg-muted/30 rounded-lg border text-sm italic">
                "{intent.natural_language_request || "No natural language request provided."}"
              </div>
              <div className="mt-4 flex items-center gap-6 text-sm text-muted-foreground">
                <div>
                  <span className="font-semibold block text-foreground">Type</span>
                  {intent.intent_type}
                </div>
                <div>
                  <span className="font-semibold block text-foreground">Created</span>
                  {new Date(intent.created_at).toLocaleString()}
                </div>
                <div>
                  <span className="font-semibold block text-foreground">Updated</span>
                  {new Date(intent.updated_at).toLocaleString()}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Structured Constraints</CardTitle>
              <CardDescription>
                The exact rules FINSHIELD evaluates actions against.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <pre className="p-4 bg-muted/50 rounded-lg border text-sm overflow-x-auto">
                <code>{JSON.stringify(intent.structured_constraints, null, 2)}</code>
              </pre>
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
              ) : (
                <div className="relative border-l border-muted ml-3 space-y-6">
                  {versions.sort((a, b) => b.version - a.version).map((v) => (
                    <div key={v.id} className="relative pl-6">
                      <div className={`absolute -left-[5px] top-1.5 h-2 w-2 rounded-full ${v.version === intent.version ? 'bg-primary ring-4 ring-primary/20' : 'bg-muted-foreground'}`} />
                      <div className="flex items-center justify-between">
                        <h4 className="text-sm font-semibold">Version {v.version}</h4>
                        <span className="text-xs text-muted-foreground">
                          {new Date(v.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">
                        {v.change_reason || "Initial creation"}
                      </p>
                      {v.version !== intent.version && (
                        <div className="mt-2 text-xs font-mono bg-muted/30 p-2 rounded truncate">
                          {Object.keys(v.structured_constraints).join(", ")}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
