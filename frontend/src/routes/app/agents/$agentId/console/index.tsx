import { useState, useEffect, useRef, useMemo } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { runtimeApi, AgentRun, AgentAction } from "@/api/runtime";
import { agentsApi } from "@/api/agents";
import { 
  ArrowLeft, Terminal, Loader2, Play, Pause, AlertTriangle, 
  CheckCircle2, XCircle, Code, List
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";

export const Route = createFileRoute("/app/agents/$agentId/console/")({
  component: AgentConsoleRoute,
});

function AgentConsoleRoute() {
  const { agentId } = Route.useParams();
  const queryClient = useQueryClient();
  const [inputText, setInputText] = useState("");
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string>(() => crypto.randomUUID());
  const scrollRef = useRef<HTMLDivElement>(null);

  const { data: agent, isLoading: agentLoading } = useQuery({
    queryKey: ["agents", agentId],
    queryFn: () => agentsApi.get(agentId),
  });

  const { data: runs = [], isLoading: runsLoading } = useQuery({
    queryKey: ["agents", agentId, "runs"],
    queryFn: () => runtimeApi.listRuns(agentId),
    refetchInterval: activeRunId ? 2000 : false,
  });

  const { data: activeRun, isLoading: runLoading } = useQuery({
    queryKey: ["agents", agentId, "runs", activeRunId],
    queryFn: () => runtimeApi.getRun(activeRunId!),
    enabled: !!activeRunId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data && ["QUEUED", "RUNNING", "WAITING"].includes(data.status)) {
        return 1000;
      }
      return false;
    }
  });

  const createRunMutation = useMutation({
    mutationFn: (input: string) => runtimeApi.createRun({ agent_id: agentId, input, session_id: sessionId }),
    onSuccess: (data) => {
      setActiveRunId(data.id);
      setInputText("");
      queryClient.invalidateQueries({ queryKey: ["agents", agentId, "runs"] });
      toast.success("Execution started");
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || "Failed to start execution");
    }
  });

  const cancelRunMutation = useMutation({
    mutationFn: (runId: string) => runtimeApi.cancelRun(runId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agents", agentId, "runs"] });
      queryClient.invalidateQueries({ queryKey: ["agents", agentId, "runs", activeRunId] });
      toast.success("Run cancelled");
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || "Failed to cancel run");
    }
  });

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [activeRun?.actions, activeRun?.status]);

  const sessions = useMemo(() => {
    const grouped = new Map<string, AgentRun[]>();
    runs.forEach(run => {
      const sid = run.session_id || run.id;
      if (!grouped.has(sid)) grouped.set(sid, []);
      grouped.get(sid)!.push(run);
    });
    return Array.from(grouped.entries()).map(([sid, sessionRuns]) => {
      sessionRuns.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
      return {
        id: sid,
        runs: sessionRuns,
        latestRun: sessionRuns[sessionRuns.length - 1]
      };
    }).sort((a, b) => {
      const timeB = b.latestRun ? new Date(b.latestRun.created_at).getTime() : 0;
      const timeA = a.latestRun ? new Date(a.latestRun.created_at).getTime() : 0;
      return timeB - timeA;
    });
  }, [runs]);

  if (agentLoading) {
    return (
      <div className="flex items-center justify-center p-24 text-muted-foreground animate-in fade-in">
        <Loader2 className="size-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] space-y-4 animate-rise">
      <div className="flex items-center justify-between border-b border-border pb-4 shrink-0">
        <div className="flex items-center">
          <Link to={`/app/agents/${agentId}`} className="hover:text-foreground transition-colors mr-4">
            <ArrowLeft className="size-5" />
          </Link>
          <div>
            <h2 className="text-xl font-bold tracking-tight flex items-center">
              <Terminal className="size-5 mr-2 text-primary" />
              Agent Console
            </h2>
            <p className="text-sm text-muted-foreground">Monitoring runtime for {agent?.name}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => { setSessionId(crypto.randomUUID()); setActiveRunId(null); }}>
             New Session
          </Button>
          {activeRun && ["QUEUED", "RUNNING", "WAITING"].includes(activeRun.status) && (
            <Button 
              variant="destructive" 
              size="sm" 
              onClick={() => cancelRunMutation.mutate(activeRun.id)}
              disabled={cancelRunMutation.isPending}
            >
              <Pause className="size-4 mr-2" /> Abort Run
            </Button>
          )}
        </div>
      </div>

      <div className="flex gap-4 flex-1 min-h-0">
        {/* Left Sidebar: Runs History */}
        <div className="w-1/3 flex flex-col gap-4 min-h-0">
          <Card className="flex flex-col bg-surface border-border flex-1 min-h-0">
            <CardHeader className="py-4">
              <CardTitle className="text-sm flex items-center">
                <List className="size-4 mr-2" /> Recent Sessions
              </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 overflow-auto p-0 px-4 pb-4">
              {runsLoading ? (
                <div className="flex justify-center py-8"><Loader2 className="size-6 animate-spin text-muted-foreground" /></div>
              ) : sessions.length === 0 ? (
                <div className="text-center text-muted-foreground py-8 text-sm">No sessions recorded.</div>
              ) : (
                <div className="space-y-4">
                  {sessions.map(session => (
                    <div key={session.id} className="space-y-2 border rounded-lg p-2 bg-background/50">
                      <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider px-2">Session</div>
                      {session.runs.map((run, idx) => (
                        <button
                          key={run.id}
                          onClick={() => { setActiveRunId(run.id); setSessionId(session.id); }}
                          className={`w-full text-left p-3 rounded-lg border text-sm transition-colors ${
                            activeRunId === run.id 
                              ? "bg-primary/10 border-primary/30" 
                              : "bg-background border-border hover:border-muted-foreground/30"
                          }`}
                        >
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-semibold text-xs text-muted-foreground">Run {idx + 1}</span>
                            <span className="text-muted-foreground text-xs">{new Date(run.created_at).toLocaleTimeString()}</span>
                          </div>
                          <div className="font-medium line-clamp-2 mb-2 text-sm">{run.input}</div>
                          <div className="flex justify-end text-xs">
                            <span className={`font-semibold ${
                              ["COMPLETED", "SUCCESS"].includes(run.status) ? "text-safe" :
                              ["FAILED", "CANCELLED", "BLOCKED"].includes(run.status) ? "text-danger" : "text-warn"
                            }`}>
                              {run.status}
                            </span>
                          </div>
                        </button>
                      ))}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Area: Run Details */}
        <div className="w-2/3 flex flex-col gap-4 min-h-0">
          <Card className="flex flex-col bg-surface border-border flex-1 min-h-0">
            {activeRun ? (
              <>
                <CardHeader className="py-4 border-b border-border bg-background/50 shrink-0">
                  <div className="flex justify-between items-start">
                    <div>
                      <CardTitle className="text-base font-medium">Run: {activeRun.id}</CardTitle>
                      <CardDescription className="mt-1 font-mono text-xs">{activeRun.input}</CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                       <span className={`px-2 py-1 text-xs font-bold rounded bg-background border ${
                        ["COMPLETED", "SUCCESS"].includes(activeRun.status) ? "text-safe border-safe/30" :
                        ["FAILED", "CANCELLED", "BLOCKED"].includes(activeRun.status) ? "text-danger border-danger/30" : "text-warn border-warn/30 animate-pulse"
                      }`}>
                        {activeRun.status}
                      </span>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="flex-1 overflow-auto p-4 space-y-4" ref={scrollRef}>
                  {runLoading ? (
                    <div className="flex justify-center py-12"><Loader2 className="size-8 animate-spin text-muted-foreground" /></div>
                  ) : (
                    <>
                      {activeRun.actions?.length === 0 ? (
                        <div className="text-center text-muted-foreground py-12 text-sm italic">Initializing pipeline...</div>
                      ) : (
                        <div className="space-y-4 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-border before:to-transparent">
                          {activeRun.actions?.map((action: AgentAction, idx: number) => (
                            <div key={action.id} className="relative flex items-start gap-4">
                              <div className="flex items-center justify-center w-10 h-10 rounded-full border border-border bg-surface shadow-sm z-10 shrink-0">
                                {action.status === "SUCCESS" && <CheckCircle2 className="size-5 text-safe" />}
                                {action.status === "FAILED" || action.status === "DENIED" ? <XCircle className="size-5 text-danger" /> : null}
                                {action.status === "RUNNING" || action.status === "QUEUED" ? <Loader2 className="size-5 text-warn animate-spin" /> : null}
                              </div>
                              <div className="flex-1 bg-background border border-border rounded-lg p-4 shadow-sm">
                                <div className="flex justify-between items-center mb-2">
                                  <div className="font-semibold text-sm font-mono flex items-center">
                                    <Code className="size-4 mr-2 text-muted-foreground" />
                                    {action.tool_name}
                                  </div>
                                  <div className="text-xs text-muted-foreground">Seq: {action.sequence_number}</div>
                                </div>
                                
                                {action.input && (
                                  <div className="mb-3">
                                    <div className="text-xs text-muted-foreground mb-1 uppercase tracking-wider font-semibold">Input</div>
                                    <pre className="text-xs bg-surface border border-border p-2 rounded text-foreground overflow-x-auto">
                                      {JSON.stringify(action.input, null, 2)}
                                    </pre>
                                  </div>
                                )}
                                
                                {action.output && (
                                  <div>
                                    <div className="text-xs text-muted-foreground mb-1 uppercase tracking-wider font-semibold">Output</div>
                                    <pre className="text-xs bg-surface border border-border p-2 rounded text-foreground overflow-x-auto">
                                      {JSON.stringify(action.output, null, 2)}
                                    </pre>
                                  </div>
                                )}

                                {(action.error_code || action.error_message) && (
                                  <div className="mt-3 p-3 bg-danger/10 border border-danger/20 rounded text-danger text-sm flex items-start">
                                    <AlertTriangle className="size-4 mr-2 mt-0.5 shrink-0" />
                                    <div>
                                      <strong>{action.error_code}</strong>: {action.error_message}
                                    </div>
                                  </div>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                      
                      {activeRun.error_code && (
                        <div className="p-4 bg-danger/10 border border-danger/30 rounded-lg text-danger mt-4 flex items-start">
                           <AlertTriangle className="size-5 mr-3 mt-0.5 shrink-0" />
                           <div>
                             <h4 className="font-bold">{activeRun.error_code}</h4>
                             <p className="text-sm opacity-90">{activeRun.error_message}</p>
                           </div>
                        </div>
                      )}
                      
                      {activeRun.output && (
                        <div className={`p-4 rounded-lg mt-4 flex items-start border ${
                          activeRun.status === 'BLOCKED' || activeRun.status === 'FAILED'
                            ? 'bg-danger/10 border-danger/30 text-danger'
                            : 'bg-safe/10 border-safe/30 text-safe'
                        }`}>
                           {activeRun.status === 'BLOCKED' || activeRun.status === 'FAILED' ? (
                             <AlertTriangle className="size-5 mr-3 mt-0.5 text-danger shrink-0" />
                           ) : (
                             <CheckCircle2 className="size-5 mr-3 mt-0.5 text-safe shrink-0" />
                           )}
                           <div className="text-sm">
                             <div className={`font-bold mb-1 ${
                               activeRun.status === 'BLOCKED' || activeRun.status === 'FAILED' ? 'text-danger' : 'text-safe'
                             }`}>
                               {activeRun.status === 'BLOCKED' ? 'Run Blocked' : activeRun.status === 'FAILED' ? 'Run Failed' : 'Final Result'}
                             </div>
                             <div className="text-foreground">
                               {activeRun.output}
                             </div>
                           </div>
                        </div>
                      )}
                    </>
                  )}
                </CardContent>
              </>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground p-8">
                <Terminal className="size-12 opacity-20 mb-4" />
                <h3 className="text-lg font-medium">No Run Selected</h3>
                <p className="text-sm text-center max-w-sm mt-2">
                  Select a run from the history or start a new execution to view the agent console.
                </p>
              </div>
            )}
            
            <div className="p-4 border-t border-border bg-background shrink-0">
               <div className="flex gap-2">
                 <Input 
                   placeholder="Instruct the agent (e.g. 'Find a laptop and create a cart')..." 
                   className="bg-surface border-border flex-1"
                   value={inputText}
                   onChange={e => setInputText(e.target.value)}
                   onKeyDown={e => {
                     if (e.key === 'Enter' && inputText.trim() && !createRunMutation.isPending) {
                       createRunMutation.mutate(inputText);
                     }
                   }}
                   disabled={createRunMutation.isPending}
                 />
                 <Button 
                   onClick={() => createRunMutation.mutate(inputText)}
                   disabled={!inputText.trim() || createRunMutation.isPending}
                 >
                   {createRunMutation.isPending ? <Loader2 className="size-4 animate-spin mr-2" /> : <Play className="size-4 mr-2" />}
                   Execute
                 </Button>
               </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
