import { useState } from "react";
import { Zap, ChevronDown, Send, Loader2 } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const ENDPOINTS = [
  { label: "POST /api/v1/agents/actions/evaluate", path: "/api/v1/agents/actions/evaluate" },
  { label: "POST /api/v1/policies/evaluate",        path: "/api/v1/policies/evaluate" },
  { label: "GET  /api/v1/audit/events",             path: "/api/v1/audit/events" },
  { label: "GET  /api/v1/agents",                   path: "/api/v1/agents" },
];

const DEFAULT_BODY = `{
  "action": "payment.request",
  "amount": 150000,
  "currency": "INR",
  "merchant_id": "m_8291",
  "agent_id": "AGT-7F31A9"
}`;

function simulateDecision(body: string): { decision: string; risk_score: number; policy: string; reason: string; latency: number } {
  let amount = 0;
  try { amount = JSON.parse(body).amount ?? 0; } catch { amount = 0; }
  const latency = 140 + Math.floor(Math.random() * 120);

  if (amount > 80000) {
    return { decision: "BLOCK",  risk_score: 91, policy: "POL-001", reason: "transaction_limit_exceeded", latency };
  } else if (amount > 50000) {
    return { decision: "REVIEW", risk_score: 64, policy: "POL-001", reason: "requires_manual_review",      latency };
  } else {
    return { decision: "ALLOW",  risk_score: 12, policy: "POL-002", reason: "within_policy_limits",        latency };
  }
}

export function ApiExplorer() {
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [showEnds, setShowEnds]       = useState(false);
  const [body, setBody]               = useState(DEFAULT_BODY);
  const [loading, setLoading]         = useState(false);
  const [response, setResponse]       = useState<null | ReturnType<typeof simulateDecision>>(null);

  const handleSend = () => {
    setLoading(true);
    setResponse(null);
    const result = simulateDecision(body);
    setTimeout(() => { setResponse(result); setLoading(false); }, result.latency);
  };

  const decisionColor = (d?: string) => {
    if (!d) return "text-foreground";
    if (d === "BLOCK")  return "text-danger";
    if (d === "REVIEW") return "text-warn";
    return "text-safe";
  };

  return (
    <Card className="border-border bg-surface shadow-sm overflow-hidden">
      <div className="flex items-center gap-3 px-6 py-4 border-b border-border">
        <Zap className="size-4 text-primary" />
        <div>
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Interactive</div>
          <div className="font-bold text-foreground">API Explorer</div>
        </div>
        <div className="ml-auto text-xs px-2 py-0.5 rounded-md bg-warn/10 border border-warn/20 text-warn font-semibold">SANDBOX</div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-border">
        {/* Left — Request */}
        <div className="p-6 space-y-4">
          <div>
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-2">Endpoint</label>
            <div className="relative">
              <button
                onClick={() => setShowEnds(s => !s)}
                className="w-full flex items-center justify-between bg-muted border border-border rounded-lg px-3 py-2.5 text-xs font-mono text-foreground hover:border-border-strong transition-colors"
              >
                <span className="truncate">{ENDPOINTS[selectedIdx]!.label}</span>
                <ChevronDown className="size-4 text-muted-foreground shrink-0 ml-2" />
              </button>
              {showEnds && (
                <div className="absolute z-10 top-full mt-1 w-full bg-popover border border-border rounded-lg shadow-xl overflow-hidden">
                  {ENDPOINTS.map((e, i) => (
                    <button key={i} onClick={() => { setSelectedIdx(i); setShowEnds(false); }}
                      className={`w-full text-left px-4 py-2.5 text-xs font-mono hover:bg-muted transition-colors ${i === selectedIdx ? "text-primary" : "text-foreground"}`}>
                      {e.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-2">Request Body</label>
            <textarea
              value={body}
              onChange={e => setBody(e.target.value)}
              rows={10}
              className="w-full bg-background border border-border rounded-xl p-4 text-xs font-mono text-foreground resize-none focus:outline-none focus:ring-2 focus:ring-primary/40 leading-relaxed"
              spellCheck={false}
            />
          </div>

          <Button
            className="w-full bg-primary hover:bg-primary/90 text-primary-foreground gap-2"
            onClick={handleSend}
            disabled={loading}
          >
            {loading ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
            {loading ? "Evaluating…" : "Send Request"}
          </Button>
        </div>

        {/* Right — Response */}
        <div className="p-6 space-y-4">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Response</div>

          {!response && !loading && (
            <div className="h-64 flex items-center justify-center border-2 border-dashed border-border rounded-xl">
              <p className="text-sm text-muted-foreground">Send a request to see the response</p>
            </div>
          )}

          {loading && (
            <div className="h-64 flex items-center justify-center border-2 border-dashed border-border rounded-xl">
              <div className="text-center space-y-3">
                <Loader2 className="size-6 animate-spin text-primary mx-auto" />
                <p className="text-sm text-muted-foreground">FINSHIELD evaluating request…</p>
              </div>
            </div>
          )}

          {response && (
            <div className="space-y-4">
              {/* Decision badge */}
              <div className={`flex items-center gap-3 p-4 rounded-xl border ${
                response.decision === "BLOCK"  ? "bg-danger/8 border-danger/20"  :
                response.decision === "REVIEW" ? "bg-warn/8 border-warn/20"     :
                                                 "bg-safe/8 border-safe/20"
              }`}>
                <div className={`text-2xl font-black font-mono ${decisionColor(response.decision)}`}>
                  {response.decision === "BLOCK" ? "✕" : response.decision === "REVIEW" ? "⚠" : "✓"}
                </div>
                <div>
                  <div className={`text-lg font-bold ${decisionColor(response.decision)}`}>{response.decision}</div>
                  <div className="text-xs text-muted-foreground">Risk score: {response.risk_score} · {response.latency}ms</div>
                </div>
              </div>

              {/* JSON response */}
              <div className="bg-background border border-border rounded-xl p-4">
                <pre className="text-xs font-mono text-foreground leading-relaxed">{JSON.stringify({
                  decision:   response.decision,
                  risk_score: response.risk_score,
                  policy:     response.policy,
                  reason:     response.reason,
                  latency_ms: response.latency,
                  trace_id:   `trc_${Math.random().toString(36).substr(2, 9)}`,
                }, null, 2)}</pre>
              </div>

              <div className="text-xs text-muted-foreground">
                Status <span className="text-safe font-mono font-semibold">200 OK</span> · {response.latency}ms · Policy {response.policy}
              </div>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}
