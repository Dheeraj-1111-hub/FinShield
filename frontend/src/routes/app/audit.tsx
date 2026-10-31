import { useState, useMemo, useEffect } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { 
  FileText, Download, Search, CheckCircle2, 
  Activity, ChevronDown, Link2, AlertTriangle, AlertCircle
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { AuditDetailDrawer } from "@/components/audit/AuditDetailDrawer";
import { useAuditEvents, useVerifyAuditIntegrity } from "@/hooks/useAudit";
import { useWorkspace } from "@/hooks/useWorkspace";
import { AuditEvent } from "@/api/audit";
import { api as apiClient } from "@/lib/api-client";

export const Route = createFileRoute("/app/audit")({
  component: AuditLogPage,
});

const getSeverityColor = (severity: string) => {
  switch(severity) {
    case 'CRITICAL': return 'text-danger bg-danger/10 border-danger/20';
    case 'HIGH': return 'text-warn bg-warn/10 border-warn/20';
    case 'WARNING': return 'text-amber-500 bg-amber-500/10 border-amber-500/20';
    case 'NOTICE': return 'text-blue-400 bg-blue-400/10 border-blue-400/20';
    case 'INFO': default: return 'text-muted-foreground bg-muted border-border';
  }
};

const getCategoryColor = (category: string) => {
  switch(category) {
    case 'GATE': return 'text-danger';
    case 'AUTH': return 'text-safe';
    case 'AGENT': return 'text-primary';
    case 'WORKSPACE': return 'text-blue-400';
    case 'PAYMENT': return 'text-emerald-400';
    case 'ORDER': return 'text-cyan-400';
    case 'INVESTIGATION': return 'text-purple-400';
    case 'APPROVAL': return 'text-amber-400';
    default: return 'text-safe';
  }
};

const formatTime = (ts: string) => {
  try {
    const d = new Date(ts);
    return isNaN(d.getTime()) ? ts : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return ts;
  }
};

function AuditLogPage() {
  const [selectedEvent, setSelectedEvent] = useState<AuditEvent | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("ALL");
  const [isExporting, setIsExporting] = useState(false);
  
  const { workspace } = useWorkspace();
  const { data: auditData, isLoading, refetch } = useAuditEvents({ size: 100 });
  const verifyMutation = useVerifyAuditIntegrity();

  useEffect(() => {
    if (workspace?.id) {
      verifyMutation.mutate();
    }
  }, [workspace?.id]);

  const events: AuditEvent[] = useMemo(() => {
    if (!auditData) return [];
    if (Array.isArray(auditData)) return auditData;
    return auditData.items || [];
  }, [auditData]);
  
  const filteredEvents = useMemo(() => {
    return events.filter(e => {
      const matchesCategory = categoryFilter === "ALL" || e.event_category === categoryFilter;
      if (!matchesCategory) return false;
      if (!searchQuery) return true;
      const q = searchQuery.toLowerCase();
      return (
        e.event_type.toLowerCase().includes(q) || 
        (e.actor_id && e.actor_id.toLowerCase().includes(q)) ||
        (e.agent_id && e.agent_id.toLowerCase().includes(q)) ||
        (e.entity_id && e.entity_id.toLowerCase().includes(q)) ||
        (e.entity_type && e.entity_type.toLowerCase().includes(q))
      );
    });
  }, [events, searchQuery, categoryFilter]);

  // Derived stats from real events
  const eventsCount = events.length;
  const criticalEventsCount = events.filter(e => e.severity === 'CRITICAL' || e.severity === 'HIGH').length;
  const agentActionsCount = events.filter(e => 
    e.event_category === 'AGENT' || 
    e.actor_type === 'AGENT' || 
    Boolean(e.agent_id)
  ).length;
  
  const eventDistribution = useMemo(() => {
    const counts: Record<string, number> = {};
    events.forEach(e => counts[e.event_category] = (counts[e.event_category] || 0) + 1);
    return Object.entries(counts).map(([cat, count]) => ({
      category: cat,
      count,
      width: `${(count / Math.max(1, events.length)) * 100}%`
    })).sort((a, b) => b.count - a.count).slice(0, 5);
  }, [events]);

  const criticalEvents = useMemo(() => {
    return events.filter(e => e.severity === 'CRITICAL' || e.severity === 'HIGH').slice(0, 5);
  }, [events]);

  const integrityCard = useMemo(() => {
    if (verifyMutation.isPending) {
      return {
        badge: "VERIFYING",
        title: "CHECKING...",
        subtitle: "Verifying chain...",
        borderClass: "border-primary/30 bg-primary/5",
        textClass: "text-primary",
        icon: <Activity className="size-6 animate-pulse" />,
        note: "Checking cryptographic hash chain across workspace events...",
        completenessTag: "CHECKING"
      };
    }
    if (verifyMutation.isError) {
      return {
        badge: "ERROR",
        title: "CHECK FAILED",
        subtitle: "Verification error",
        borderClass: "border-danger/30 bg-danger/5",
        textClass: "text-danger",
        icon: <AlertTriangle className="size-6" />,
        note: "Failed to communicate with audit verification service.",
        completenessTag: "ERROR"
      };
    }
    if (verifyMutation.isSuccess) {
      const data = verifyMutation.data;
      if (data.checked_events === 0) {
        if (data.completeness_status === 'INCOMPLETE_INGESTION') {
          return {
            badge: "INGESTION BROKEN",
            title: "EVENTS MISSING",
            subtitle: "0 events for existing records",
            borderClass: "border-danger/30 bg-danger/5",
            textClass: "text-danger",
            icon: <AlertTriangle className="size-6" />,
            note: data.completeness_note || "Workspace has active records but 0 audit events.",
            completenessTag: "INCOMPLETE"
          };
        }
        return {
          badge: "CHAIN EMPTY",
          title: "NO AUDIT LOGS",
          subtitle: "0 events recorded • Unverified",
          borderClass: "border-amber-500/30 bg-amber-500/5",
          textClass: "text-amber-500",
          icon: <AlertCircle className="size-6" />,
          note: "No audit events recorded in this workspace. Completeness cannot be established.",
          completenessTag: "EMPTY"
        };
      }
      if (data.valid) {
        return {
          badge: "CHAIN INTACT",
          title: "CHAIN VALID",
          subtitle: `${data.checked_events} recorded events verified`,
          borderClass: "border-safe/30 bg-safe/5",
          textClass: "text-safe",
          icon: <CheckCircle2 className="size-6" />,
          note: "Available chain is valid (unbroken hashes). Valid chain confirms ledger immutability, not operational completeness.",
          completenessTag: "CHAIN VALID"
        };
      }
      const brokenCount = data.broken_links?.length || 0;
      return {
        badge: "CHAIN TAMPERED",
        title: "INTEGRITY VIOLATION",
        subtitle: `${brokenCount} issue${brokenCount === 1 ? '' : 's'} detected`,
        borderClass: "border-danger/30 bg-danger/5",
        textClass: "text-danger",
        icon: <AlertTriangle className="size-6" />,
        note: data.completeness_note || "Cryptographic integrity violation detected in audit ledger.",
        completenessTag: "VIOLATION"
      };
    }
    return {
      badge: "INTEGRITY",
      title: "UNVERIFIED",
      subtitle: "Click to run check",
      borderClass: "border-border bg-surface",
      textClass: "text-muted-foreground",
      icon: <Link2 className="size-6" />,
      note: "Audit log chain has not yet been checked for this session.",
      completenessTag: "PENDING"
    };
  }, [verifyMutation.isPending, verifyMutation.isError, verifyMutation.isSuccess, verifyMutation.data]);


  const handleExport = async () => {
    try {
      setIsExporting(true);
      const res = await apiClient.get('/audit/export', {
        headers: { 'X-Workspace-ID': workspace?.id || '' },
        params: { workspace_id: workspace?.id }
      });
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `finshield-audit-export-${workspace?.id || "events"}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to export audit logs", err);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500 pb-12">
      
      {/* 1. Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground mb-2 flex items-center gap-2">
            <FileText className="size-6 text-primary" />
            Audit Log
          </h1>
          <p className="text-muted-foreground font-medium max-w-2xl">
            Immutable record of critical activity across FINSHIELD. Trace agent actions, policy decisions, transactions, investigations, configuration changes, and security events.
          </p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-safe/10 border border-safe/20 rounded-md text-safe text-xs font-bold tracking-wider uppercase mr-2">
            <div className="size-2 rounded-full bg-safe animate-pulse" /> LIVE
          </div>
          <select 
            aria-label="Filter events by category"
            className="border border-border bg-background h-10 px-3 py-1 rounded text-sm text-foreground focus:outline-none"
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
          >
            <option value="ALL">All Categories</option>
            <option value="GATE">Gate Decisions</option>
            <option value="PAYMENT">Payments</option>
            <option value="ORDER">Orders</option>
            <option value="APPROVAL">Approvals</option>
            <option value="INVESTIGATION">Investigations</option>
            <option value="AGENT">Agent Actions</option>
            <option value="AUTH">Authentication</option>
          </select>
          <Button 
            className="bg-primary hover:bg-primary/90 text-primary-foreground h-10"
            onClick={handleExport}
            disabled={isExporting}
          >
            <Download className="size-4 mr-2" /> {isExporting ? "Exporting..." : "Export"}
          </Button>
        </div>
      </div>

      {/* 2. Executive Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-5 border-border bg-surface shadow-sm">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Events Fetched</div>
          <div className="text-3xl font-bold font-mono text-foreground mb-1">{eventsCount}</div>
          <div className="text-sm text-safe font-medium flex items-center gap-1">
            <Activity className="size-4" /> Live Tracking
          </div>
        </Card>

        <Card className="p-5 border-border bg-surface shadow-sm">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Critical/High Events</div>
          <div className="text-3xl font-bold font-mono text-foreground mb-1">{criticalEventsCount}</div>
          <div className="text-sm text-warn font-medium flex items-center gap-1">
            <AlertCircle className="size-4" /> Needs attention
          </div>
        </Card>

        <Card className="p-5 border-border bg-surface shadow-sm">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Agent Actions</div>
          <div className="text-3xl font-bold font-mono text-foreground mb-1">{agentActionsCount}</div>
          <div className="text-sm text-muted-foreground font-medium flex items-center gap-1">
            {events.length ? Math.round((agentActionsCount / events.length) * 100) : 0}% of events
          </div>
        </Card>

        <Card className={`p-5 shadow-sm relative overflow-hidden flex flex-col justify-between ${integrityCard.borderClass}`}>
          <div>
            <div className="text-xs font-semibold uppercase tracking-wider mb-2 flex items-center justify-between">
              <span className="flex items-center gap-1"><Link2 className="size-3.5" /> {integrityCard.badge}</span>
              {integrityCard.completenessTag && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-background/60 border border-border/60 font-mono font-bold">
                  {integrityCard.completenessTag}
                </span>
              )}
            </div>
            <div className={`text-2xl font-bold font-mono mb-1 flex items-center gap-2 ${integrityCard.textClass}`}>
              {integrityCard.icon}
              {integrityCard.title}
            </div>
            <div className={`text-xs font-medium font-mono ${integrityCard.textClass}`}>
              {integrityCard.subtitle}
            </div>
          </div>
          {integrityCard.note && (
            <div className="mt-3 pt-2 border-t border-border/40 text-[11px] leading-snug text-muted-foreground">
              {integrityCard.note}
            </div>
          )}
        </Card>

      </div>

      {/* Main Content Area */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        
        {/* Left Column (Span 3): Audit Stream */}
        <div className="lg:col-span-3 space-y-6">
          
          {/* Audit Stream */}
          <div>
            <div className="flex items-center justify-between mb-4 gap-4">
              <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider whitespace-nowrap">Audit Stream</h2>
              <div className="flex-1 max-w-md relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                <Input 
                  placeholder="Search events, agents, transactions, policies..." 
                  className="pl-9 h-9 bg-surface border-border text-sm"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
            </div>
            
            <Card className="bg-surface border-border overflow-hidden shadow-sm">
              <table className="w-full text-sm">
                <thead className="bg-surface-raised border-b border-border">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">Time</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">Event</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">Actor</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">Category</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">Severity</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {isLoading ? (
                    <tr>
                      <td colSpan={5} className="text-center py-8 text-muted-foreground">Loading events...</td>
                    </tr>
                  ) : filteredEvents.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="text-center py-8 text-muted-foreground">No events found</td>
                    </tr>
                  ) : filteredEvents.map((event) => (
                    <tr 
                      key={event.id} 
                      className="hover:bg-surface-raised/50 transition-colors cursor-pointer group"
                      onClick={() => setSelectedEvent(event)}
                    >
                      <td className="px-4 py-3 font-mono text-xs text-muted-foreground whitespace-nowrap">{formatTime(event.created_at)}</td>
                      <td className="px-4 py-3 font-medium text-foreground group-hover:text-primary transition-colors">{event.event_type}</td>
                      <td className="px-4 py-3 text-muted-foreground text-xs">{event.agent_id || event.actor_id || 'SYSTEM'}</td>
                      <td className="px-4 py-3 font-mono font-bold">
                        <span className={getCategoryColor(event.event_category)}>{event.event_category}</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase border ${getSeverityColor(event.severity)}`}>
                          {event.severity}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          </div>

          {/* Lower Section: Distribution and Integrity */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4">
            
            {/* Event Distribution */}
            <div>
              <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4">Event Distribution</h2>
              <Card className="bg-surface border-border p-5 h-full">
                <div className="space-y-4">
                  {eventDistribution.length === 0 && <div className="text-muted-foreground text-sm">No data</div>}
                  {eventDistribution.map((dist, idx) => (
                    <div key={idx}>
                      <div className="flex justify-between text-xs mb-1.5">
                        <span className="font-medium text-foreground">{dist.category}</span>
                        <span className="font-mono text-muted-foreground">{dist.count}</span>
                      </div>
                      <div className="w-full h-2 bg-surface-raised rounded-full overflow-hidden">
                        <div className="h-full bg-primary/70" style={{ width: dist.width }} />
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            </div>

            {/* Audit Integrity & Health */}
            <div>
              <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4">Audit Integrity Tool</h2>
              <Card className="bg-surface border-border p-5 h-full flex flex-col justify-between">
                <div className="space-y-4">
                  <div className="text-sm text-muted-foreground mb-4">
                    Cryptographically verify the integrity of the audit log chain in the current workspace.
                  </div>
                  
                  <Button 
                    className="w-full bg-safe/10 text-safe hover:bg-safe/20 border-safe/20 font-mono" 
                    variant="outline"
                    onClick={() => {
                      verifyMutation.mutate();
                      refetch();
                    }}
                    disabled={verifyMutation.isPending}
                  >
                    {verifyMutation.isPending ? 'Verifying...' : 'Verify Cryptographic Chain'}
                  </Button>

                  {verifyMutation.isSuccess && (
                    <div className={`mt-4 p-3 rounded border text-sm ${
                      verifyMutation.data.checked_events === 0
                        ? 'bg-amber-500/10 border-amber-500/30 text-amber-500'
                        : verifyMutation.data.valid
                          ? 'bg-safe/10 border-safe/30 text-safe'
                          : 'bg-danger/10 border-danger/30 text-danger'
                    }`}>
                      {verifyMutation.data.checked_events === 0 ? (
                        <div className="flex flex-col gap-1">
                          <div className="flex items-center gap-2 font-bold">
                            <AlertCircle className="size-4" /> 
                            {verifyMutation.data.completeness_status === 'INCOMPLETE_INGESTION' 
                              ? 'Missing Event Ingestion' 
                              : 'No events recorded in workspace chain'}
                          </div>
                          <div className="text-xs opacity-90">
                            {verifyMutation.data.completeness_note || 'Empty audit ledger: no chain exists to verify.'}
                          </div>
                        </div>
                      ) : verifyMutation.data.valid ? (
                        <div className="flex flex-col gap-1">
                          <div className="flex items-center gap-2 font-bold">
                            <CheckCircle2 className="size-4" /> Chain Verified ({verifyMutation.data.checked_events} events checked)
                          </div>
                          <div className="text-xs opacity-85 mt-1 border-t border-safe/20 pt-1">
                            {verifyMutation.data.completeness_note || 'Available cryptographic hash chain is valid. Note: Confirms ledger immutability, not operational completeness.'}
                          </div>
                        </div>
                      ) : (
                        <div className="flex flex-col gap-1">
                          <div className="flex items-center gap-2 font-bold">
                            <AlertTriangle className="size-4" /> Integrity Violation Detected!
                          </div>
                          <div className="text-xs">
                            Broken links: {verifyMutation.data.broken_links.map((l: any) => `${l.event_id} (${l.reason})`).join(', ')}
                          </div>
                          <div className="text-[11px] opacity-80 mt-1">
                            {verifyMutation.data.completeness_note}
                          </div>
                        </div>
                      )}

                    </div>
                  )}
                  {verifyMutation.isError && (
                    <div className="mt-4 p-3 rounded border bg-danger/10 border-danger/30 text-danger text-sm flex items-center gap-2">
                      <AlertTriangle className="size-4" /> Error verifying chain
                    </div>
                  )}
                </div>
              </Card>
            </div>

          </div>
        </div>

        {/* Right Column: Critical Events Panel */}
        <div className="space-y-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Critical Events</h2>
            <div className="text-[10px] font-bold tracking-wider text-danger uppercase">{criticalEvents.length} events</div>
          </div>
          
          <div className="space-y-3">
            {criticalEvents.length === 0 && <div className="text-muted-foreground text-sm">No critical events</div>}
            {criticalEvents.map((evt, idx) => (
              <Card 
                key={idx} 
                className="bg-surface border-border p-4 hover:border-danger/30 transition-colors cursor-pointer relative overflow-hidden"
                onClick={() => setSelectedEvent(evt)}
              >
                <div className="absolute left-0 top-0 bottom-0 w-1 bg-danger" />
                <div className="flex items-start gap-3">
                  <div className="mt-0.5">
                    <div className="size-2 rounded-full bg-danger animate-pulse shadow-[0_0_8px_rgba(var(--danger),0.8)]" />
                  </div>
                  <div className="flex-1">
                    <div className="font-bold text-sm text-foreground mb-1">{evt.event_type}</div>
                    <div className="text-xs text-muted-foreground mb-1">{evt.agent_id || evt.actor_id || 'SYSTEM'}</div>
                    <div className="text-[10px] text-muted-foreground mt-2">{new Date(evt.created_at).toLocaleString()}</div>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      </div>

      {selectedEvent && (
        <AuditDetailDrawer 
          event={selectedEvent} 
          onClose={() => setSelectedEvent(null)} 
        />
      )}
      
    </div>
  );
}
