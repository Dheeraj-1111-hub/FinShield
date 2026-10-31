import { useState } from "react";
import { Code2, Copy, Check } from "lucide-react";
import { Card } from "@/components/ui/card";

const SNIPPETS: Record<string, string> = {
  "Node.js": `import Finshield from "@finshield/node";

const client = new Finshield({
  apiKey: process.env.FINSHIELD_API_KEY,
  environment: "sandbox",
});

const decision = await client.actions.evaluate({
  agentId: "AGT-7F31A9",
  action: "payment.request",
  amount: 150000,
  currency: "INR",
  merchantId: "m_8291",
});

// decision.result → "ALLOW" | "REVIEW" | "BLOCK"
console.log(decision.result, decision.riskScore);`,

  Python: `from finshield import Finshield

client = Finshield(
    api_key=os.environ["FINSHIELD_API_KEY"],
    environment="sandbox",
)

decision = client.actions.evaluate(
    agent_id="AGT-7F31A9",
    action="payment.request",
    amount=150000,
    currency="INR",
    merchant_id="m_8291",
)

# decision.result → "ALLOW" | "REVIEW" | "BLOCK"
print(decision.result, decision.risk_score)`,

  cURL: `curl -X POST https://api.finshield.io/v1/agents/actions/evaluate \\
  -H "Authorization: Bearer $FINSHIELD_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "agent_id": "AGT-7F31A9",
    "action": "payment.request",
    "amount": 150000,
    "currency": "INR",
    "merchant_id": "m_8291"
  }'`,
};

export function DeveloperResources() {
  const [tab, setTab]     = useState("Node.js");
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(SNIPPETS[tab] ?? "").catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Quick Start */}
      <div className="lg:col-span-2">
        <Card className="border-border bg-surface shadow-sm overflow-hidden">
          <div className="flex items-center justify-between px-6 py-4 border-b border-border">
            <div className="flex items-center gap-3">
              <Code2 className="size-4 text-primary" />
              <div>
                <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Integration</div>
                <div className="font-bold text-foreground">Quick Start</div>
              </div>
            </div>
            <div className="flex gap-1">
              {Object.keys(SNIPPETS).map(t => (
                <button key={t} onClick={() => setTab(t)}
                  className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${tab === t ? "bg-primary/15 text-primary" : "text-muted-foreground hover:text-foreground hover:bg-muted"}`}>
                  {t}
                </button>
              ))}
            </div>
          </div>

          <div className="relative">
            <button
              onClick={handleCopy}
              className={`absolute top-4 right-4 z-10 size-8 rounded-lg flex items-center justify-center transition-colors ${copied ? "bg-safe/15 text-safe" : "bg-muted text-muted-foreground hover:text-foreground"}`}
            >
              {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
            </button>
            <pre className="bg-background m-0 p-6 text-xs font-mono text-foreground overflow-x-auto leading-relaxed">
              <code>{SNIPPETS[tab]}</code>
            </pre>
          </div>
        </Card>
      </div>

      {/* Docs links */}
      <div>
        <Card className="border-border bg-surface shadow-sm overflow-hidden h-full">
          <div className="px-6 py-4 border-b border-border">
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-0.5">Docs</div>
            <div className="font-bold text-foreground">Developer Resources</div>
          </div>
          <div className="divide-y divide-border">
            {[
              { label: "API Reference",         desc: "Complete REST API documentation" },
              { label: "SDKs",                  desc: "Node.js · Python · Java" },
              { label: "Authentication",        desc: "API keys, scopes and signing" },
              { label: "Webhooks",              desc: "Events, retries and signatures" },
              { label: "Agent Integration",     desc: "Protect your first autonomous action" },
              { label: "Changelog",             desc: "API v1.9 — current" },
            ].map(link => (
              <div key={link.label} className="px-5 py-3.5 flex items-center justify-between hover:bg-muted/40 transition-colors cursor-pointer group">
                <div>
                  <div className="text-sm font-medium text-foreground group-hover:text-primary transition-colors">{link.label}</div>
                  <div className="text-xs text-muted-foreground">{link.desc}</div>
                </div>
                <svg className="size-4 text-muted-foreground group-hover:text-primary transition-colors" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path d="M9 18l6-6-6-6" />
                </svg>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
