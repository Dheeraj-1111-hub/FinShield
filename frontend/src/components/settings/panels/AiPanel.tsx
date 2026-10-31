import { useState } from "react";
import { Info } from "lucide-react";
import { Card } from "@/components/ui/card";

function Toggle({ checked, onChange }: { checked: boolean; onChange: () => void }) {
  return (
    <button onClick={onChange}
      className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ${checked ? "bg-primary" : "bg-muted-foreground/30"}`}>
      <span className={`pointer-events-none inline-block size-4 rounded-full bg-white shadow transition-transform duration-200 ${checked ? "translate-x-4" : "translate-x-0"}`} />
    </button>
  );
}

function ToggleRow({ label, desc, checked, onChange }: { label: string; desc?: string; checked: boolean; onChange: () => void }) {
  return (
    <div className="flex items-center justify-between py-4 border-b border-border last:border-0 gap-4">
      <div>
        <div className="text-sm font-medium text-foreground">{label}</div>
        {desc && <div className="text-xs text-muted-foreground mt-0.5">{desc}</div>}
      </div>
      <Toggle checked={checked} onChange={onChange} />
    </div>
  );
}

export function AiPanel() {
  const [investigator, setInvestigator]  = useState(true);
  const [explanations, setExplanations]  = useState(true);
  const [anomaly, setAnomaly]            = useState(true);
  const [recommendations, setRecs]       = useState(true);
  const [useEvents, setUseEvents]        = useState(true);
  const [useHistory, setUseHistory]      = useState(true);
  const [humanReview, setHumanReview]    = useState(true);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-foreground mb-0.5">AI & Intelligence</h2>
        <p className="text-sm text-muted-foreground">Configure AI-assisted security and analysis features.</p>
      </div>

      {/* Features */}
      <Card className="border-border bg-surface p-6">
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">AI Features</div>
        <ToggleRow
          label="AI Investigator"
          desc="Automatically analyze suspicious investigations and generate findings."
          checked={investigator} onChange={() => setInvestigator(v => !v)}
        />
        <ToggleRow
          label="AI Explanations"
          desc="Show reasoning summaries for policy decisions and risk scores."
          checked={explanations} onChange={() => setExplanations(v => !v)}
        />
        <ToggleRow
          label="AI Anomaly Detection"
          desc="Detect unusual agent behavior and flag intent drift."
          checked={anomaly} onChange={() => setAnomaly(v => !v)}
        />
        <ToggleRow
          label="AI Recommendations"
          desc="Suggest policy improvements based on historical decisions."
          checked={recommendations} onChange={() => setRecs(v => !v)}
        />
      </Card>

      {/* Data Controls */}
      <Card className="border-border bg-surface p-6">
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">AI Data Controls</div>
        <ToggleRow
          label="Use workspace events for anomaly detection"
          desc="Real-time event stream is analyzed by the anomaly detection model."
          checked={useEvents} onChange={() => setUseEvents(v => !v)}
        />
        <ToggleRow
          label="Use historical decisions to improve recommendations"
          desc="Policy decisions are used to calibrate AI recommendation models."
          checked={useHistory} onChange={() => setUseHistory(v => !v)}
        />
        <ToggleRow
          label="Require human review for critical actions"
          desc="AI-flagged critical actions always require a human sign-off."
          checked={humanReview} onChange={() => setHumanReview(v => !v)}
        />
      </Card>

      {/* Important note */}
      <div className="flex items-start gap-3 p-4 bg-primary/8 border border-primary/20 rounded-xl">
        <Info className="size-4 text-primary shrink-0 mt-0.5" />
        <p className="text-sm text-foreground">
          <span className="font-semibold">FINSHIELD AI recommendations never bypass deterministic policy controls.</span>{" "}
          AI analysis is advisory — all financial decisions are still enforced by the policy engine.
        </p>
      </div>
    </div>
  );
}
