import { useState } from "react";
import { X, Bot, Check, ChevronRight, ChevronLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Props {
  open: boolean;
  onClose: () => void;
}

const CAPABILITIES = [
  { id: "browse",    label: "Browse merchants",  desc: "Search and browse merchant catalogues" },
  { id: "orders",    label: "Create orders",      desc: "Place and manage purchase orders" },
  { id: "payments",  label: "Request payments",   desc: "Initiate payment requests" },
  { id: "transfers", label: "Initiate transfers", desc: "Transfer funds between accounts" },
  { id: "policies",  label: "Modify policies",    desc: "Update policy configuration" },
];

const AGENT_TYPES = ["Shopping", "Finance", "Travel", "Research", "Custom"];
const ENVS = ["Sandbox", "Production"];

export function RegisterAgentModal({ open, onClose }: Props) {
  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [agentType, setAgentType] = useState("Shopping");
  const [env, setEnv] = useState("Sandbox");
  const [caps, setCaps] = useState<Record<string, boolean>>({ browse: true, orders: true, payments: true });
  const [maxTx, setMaxTx] = useState("50000");
  const [dailyAuth, setDailyAuth] = useState("200000");
  const [reviewAbove, setReviewAbove] = useState("25000");
  const [registered, setRegistered] = useState(false);

  if (!open) return null;

  const steps = ["Identity", "Capabilities", "Authority", "Verify"];

  const handleClose = () => {
    setStep(0); setName(""); setDescription(""); setAgentType("Shopping");
    setEnv("Sandbox"); setCaps({ browse: true, orders: true, payments: true });
    setMaxTx("50000"); setDailyAuth("200000"); setReviewAbove("25000");
    setRegistered(false);
    onClose();
  };

  const agentId = `AGT-${Math.random().toString(36).substr(2,6).toUpperCase()}`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={handleClose}>
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      <div className="relative w-full max-w-xl bg-surface border border-border rounded-2xl shadow-2xl" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-6 pb-4 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="size-8 rounded-lg bg-primary/15 flex items-center justify-center">
              <Bot className="size-4 text-primary" />
            </div>
            <h2 className="text-lg font-bold text-foreground">
              {registered ? "Agent Registered" : "Register Agent"}
            </h2>
          </div>
          <button onClick={handleClose} className="text-muted-foreground hover:text-foreground transition-colors">
            <X className="size-5" />
          </button>
        </div>

        {!registered ? (
          <div className="p-6 space-y-6">
            {/* Step indicator */}
            <div className="flex items-center gap-2">
              {steps.map((s, i) => (
                <div key={s} className="flex items-center gap-2 flex-1">
                  <div className={`size-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 transition-colors ${
                    i < step ? "bg-primary text-primary-foreground" :
                    i === step ? "bg-primary/20 text-primary border border-primary/50" :
                    "bg-muted text-muted-foreground border border-border"
                  }`}>
                    {i < step ? <Check className="size-3.5" /> : i + 1}
                  </div>
                  <span className={`text-xs font-medium ${i === step ? "text-foreground" : "text-muted-foreground"}`}>{s}</span>
                  {i < steps.length - 1 && <div className={`flex-1 h-px ${i < step ? "bg-primary/40" : "bg-border"}`} />}
                </div>
              ))}
            </div>

            {/* Step 0 — Identity */}
            {step === 0 && (
              <div className="space-y-4">
                <div>
                  <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-2">Agent Name</label>
                  <input value={name} onChange={e => setName(e.target.value)} placeholder="My Shopping Agent"
                    className="w-full bg-muted border border-border rounded-lg px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50" />
                </div>
                <div>
                  <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-2">Description</label>
                  <input value={description} onChange={e => setDescription(e.target.value)} placeholder="Autonomous shopping assistant"
                    className="w-full bg-muted border border-border rounded-lg px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50" />
                </div>
                <div>
                  <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-2">Agent Type</label>
                  <div className="grid grid-cols-3 gap-2">
                    {AGENT_TYPES.map(t => (
                      <button key={t} onClick={() => setAgentType(t)}
                        className={`px-3 py-2 rounded-lg border text-sm font-medium transition-colors ${agentType === t ? "border-primary/50 bg-primary/10 text-primary" : "border-border bg-muted text-muted-foreground hover:border-border-strong"}`}>
                        {t}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-2">Environment</label>
                  <div className="flex gap-3">
                    {ENVS.map(e => (
                      <label key={e} className={`flex items-center gap-2.5 flex-1 px-4 py-3 rounded-lg border cursor-pointer transition-colors ${env === e ? "border-primary/50 bg-primary/10 text-primary" : "border-border bg-muted text-muted-foreground"}`}>
                        <div className={`size-4 rounded-full border-2 flex items-center justify-center shrink-0 ${env === e ? "border-primary" : "border-muted-foreground/40"}`}>
                          {env === e && <div className="size-2 rounded-full bg-primary" />}
                        </div>
                        <input type="radio" className="sr-only" checked={env === e} onChange={() => setEnv(e)} />
                        <span className="text-sm font-medium">{e}</span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Step 1 — Capabilities */}
            {step === 1 && (
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">What can this agent do?</p>
                {CAPABILITIES.map(c => (
                  <label key={c.id} className="flex items-start gap-3 p-3 rounded-lg border border-border bg-muted cursor-pointer hover:border-border-strong transition-colors">
                    <div className={`size-4 rounded border-2 flex items-center justify-center shrink-0 mt-0.5 transition-colors ${caps[c.id] ? "bg-primary border-primary" : "border-muted-foreground/40"}`}>
                      {caps[c.id] && <Check className="size-3 text-primary-foreground" strokeWidth={3} />}
                    </div>
                    <input type="checkbox" className="sr-only" checked={!!caps[c.id]} onChange={() => setCaps(p => ({ ...p, [c.id]: !p[c.id] }))} />
                    <div>
                      <div className="text-sm font-medium text-foreground">{c.label}</div>
                      <div className="text-xs text-muted-foreground">{c.desc}</div>
                    </div>
                  </label>
                ))}
              </div>
            )}

            {/* Step 2 — Authority */}
            {step === 2 && (
              <div className="space-y-4">
                <p className="text-sm text-muted-foreground">Set financial authority limits. These are enforced by FINSHIELD's policy engine.</p>
                {[
                  { label: "Maximum transaction (₹)", value: maxTx, set: setMaxTx },
                  { label: "Daily authority (₹)",     value: dailyAuth, set: setDailyAuth },
                  { label: "Requires review above (₹)", value: reviewAbove, set: setReviewAbove },
                ].map(f => (
                  <div key={f.label}>
                    <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-2">{f.label}</label>
                    <input value={f.value} onChange={e => f.set(e.target.value)} type="number"
                      className="w-full bg-muted border border-border rounded-lg px-3 py-2.5 text-sm text-foreground font-mono focus:outline-none focus:ring-2 focus:ring-primary/50" />
                  </div>
                ))}
                <div className="p-3 bg-info/10 border border-info/20 rounded-lg text-xs text-info">
                  These limits create automatic policy rules. Actions exceeding them are blocked or queued for review.
                </div>
              </div>
            )}

            {/* Step 3 — Verify */}
            {step === 3 && (
              <div className="space-y-4">
                <p className="text-sm text-muted-foreground">Review your agent configuration before registering.</p>
                {[
                  { label: "Name",        value: name || "—" },
                  { label: "Type",        value: agentType },
                  { label: "Environment", value: env },
                  { label: "Capabilities", value: Object.entries(caps).filter(([,v]) => v).map(([k]) => CAPABILITIES.find(c => c.id === k)?.label).join(", ") || "None" },
                  { label: "Max Tx",      value: `₹${parseInt(maxTx).toLocaleString("en-IN")}` },
                  { label: "Daily Auth",  value: `₹${parseInt(dailyAuth).toLocaleString("en-IN")}` },
                  { label: "Review ≥",    value: `₹${parseInt(reviewAbove).toLocaleString("en-IN")}` },
                ].map(row => (
                  <div key={row.label} className="flex justify-between text-sm border-b border-border pb-2 last:border-0">
                    <span className="text-muted-foreground">{row.label}</span>
                    <span className="font-medium text-foreground text-right max-w-[60%]">{row.value}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Nav */}
            <div className="flex gap-3 pt-2">
              {step > 0 && (
                <Button variant="outline" className="gap-2 border-border bg-background" onClick={() => setStep(s => s - 1)}>
                  <ChevronLeft className="size-4" /> Back
                </Button>
              )}
              <Button
                className="flex-1 bg-primary hover:bg-primary/90 text-primary-foreground gap-2"
                disabled={step === 0 && !name.trim()}
                onClick={() => step < steps.length - 1 ? setStep(s => s + 1) : setRegistered(true)}
              >
                {step < steps.length - 1 ? <>Continue <ChevronRight className="size-4" /></> : "Register Agent"}
              </Button>
            </div>
          </div>
        ) : (
          /* ── REGISTERED ── */
          <div className="p-6 space-y-5">
            <div className="flex items-center gap-3 p-4 bg-safe/10 border border-safe/25 rounded-xl">
              <Check className="size-5 text-safe shrink-0" />
              <div>
                <p className="text-sm font-semibold text-safe">Agent registered successfully</p>
                <p className="text-xs text-muted-foreground mt-0.5">Your agent is now under FINSHIELD protection.</p>
              </div>
            </div>
            <div className="bg-muted rounded-xl border border-border p-4 space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-muted-foreground">Agent ID</span><code className="text-primary font-mono">{agentId}</code></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Name</span><span className="font-medium">{name}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Environment</span><span className="font-medium">{env}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Status</span><span className="text-safe font-medium">● CONNECTED</span></div>
            </div>
            <Button className="w-full bg-primary hover:bg-primary/90 text-primary-foreground" onClick={handleClose}>Done</Button>
          </div>
        )}
      </div>
    </div>
  );
}
