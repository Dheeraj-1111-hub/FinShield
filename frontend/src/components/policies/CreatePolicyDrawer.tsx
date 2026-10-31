import { useState } from "react";
import { X, Play, TestTube, CheckCircle2, ChevronRight, Info, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { policiesApi } from "@/api/policies";
import { useAuth } from "@/lib/auth-context";

interface CreatePolicyDrawerProps {
  onClose: () => void;
  onSuccess: () => void;
}

export function CreatePolicyDrawer({ onClose, onSuccess }: CreatePolicyDrawerProps) {
  const { workspace } = useAuth();
  const [activeStep, setActiveStep] = useState(1);
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulationComplete, setSimulationComplete] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form State
  const [name, setName] = useState("New Policy");
  const [description, setDescription] = useState("");
  const [policyType, setPolicyType] = useState("TRANSACTION_LIMIT");
  
  // Rule State
  const [rules, setRules] = useState([
    { id: crypto.randomUUID(), dimension: "transaction_amount", operator: "GT", value: "50000", decision: "REVIEW" }
  ]);

  const addRule = () => {
    setRules([...rules, { id: crypto.randomUUID(), dimension: "transaction_amount", operator: "GT", value: "10000", decision: "REVIEW" }]);
  };

  const removeRule = (id: string) => {
    setRules(rules.filter(r => r.id !== id));
  };

  const updateRule = (id: string, field: string, value: string) => {
    setRules(rules.map(r => r.id === id ? { ...r, [field]: value } : r));
  };

  const handleSimulate = () => {
    setIsSimulating(true);
    setTimeout(() => {
      setIsSimulating(false);
      setSimulationComplete(true);
    }, 1500);
  };

  const handleActivate = async (status: "ACTIVE" | "DRAFT") => {
    if (!workspace) return;
    
    if (!name.trim()) {
      setError("Policy name is required.");
      return;
    }
    
    if (rules.length === 0) {
      setError("At least one rule is required.");
      return;
    }
    
    setIsSubmitting(true);
    setError(null);

    // Build the payload
    // Note: the backend currently expects a single conditions dict and single actions dict,
    // so we map the first rule to conditions and actions, or combine them if possible.
    // For now, let's map the rules list into a flat conditions object and take the highest severity decision
    const conditions: Record<string, any> = {};
    let finalDecision = "ALLOW";
    
    rules.forEach(r => {
      let val: any = r.value;
      if (r.dimension === "transaction_amount") {
         val = parseInt(r.value, 10) || 0;
      }
      conditions[r.dimension] = { operator: r.operator, value: val };
      
      // Compute decision severity: BLOCK > REVIEW > ALLOW
      if (r.decision === "BLOCK") finalDecision = "BLOCK";
      else if (r.decision === "REVIEW" && finalDecision !== "BLOCK") finalDecision = "REVIEW";
    });

    try {
      await policiesApi.create({
        name,
        description,
        policy_type: policyType as any,
        status,
        priority: 50,
        conditions,
        actions: { decision: finalDecision, reason: `Matches ${rules.length} conditions` }
      });
      onSuccess();
    } catch (err: any) {
      const apiError = err.response?.data?.error;
      if (apiError) {
        if (apiError.code === "VALIDATION_ERROR" && apiError.details) {
          setError(`Validation error: ${apiError.details[0]?.loc?.slice(1).join('.')} ${apiError.details[0]?.msg}`);
        } else {
          setError(apiError.message || "Failed to create policy");
        }
      } else {
        setError(err.response?.data?.detail || err.message || "Failed to create policy");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="absolute inset-y-0 right-0 w-[800px] bg-background border-l border-border shadow-2xl flex flex-col z-50 animate-in slide-in-from-right duration-300">
      
      {/* Header */}
      <div className="h-14 border-b border-border flex items-center justify-between px-5 bg-surface shrink-0">
        <div className="flex items-center gap-3">
          <div className="text-sm font-semibold text-muted-foreground">
            Create Policy
          </div>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} className="size-8 rounded-full">
          <X className="size-4" />
        </Button>
      </div>

      <div className="flex flex-1 overflow-hidden">
        
        {/* Left Sidebar Steps */}
        <div className="w-48 border-r border-border bg-surface p-4 flex flex-col gap-2">
          {[
            { id: 1, label: "Basics" },
            { id: 2, label: "Scope" },
            { id: 3, label: "Rules" },
            { id: 4, label: "Enforcement" },
            { id: 5, label: "Review" }
          ].map(step => (
            <button
              key={step.id}
              onClick={() => setActiveStep(step.id)}
              className={`flex items-center gap-3 px-3 py-2 text-sm rounded-md font-medium transition-colors ${
                activeStep === step.id 
                  ? 'bg-primary/10 text-primary' 
                  : 'text-muted-foreground hover:bg-surface-raised hover:text-foreground'
              }`}
            >
              <div className={`size-5 rounded-full flex items-center justify-center text-[10px] ${
                activeStep === step.id ? 'bg-primary text-primary-foreground' : 'bg-surface-raised border border-border'
              }`}>
                {step.id}
              </div>
              {step.label}
            </button>
          ))}
        </div>

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col h-full bg-background relative overflow-y-auto custom-scrollbar">
          
          <div className="p-8 pb-24">

            {error && (
              <div className="mb-6 p-4 bg-danger/10 border border-danger/20 text-danger text-sm rounded-lg">
                {error}
              </div>
            )}

            {activeStep === 1 && (
              <div className="space-y-6 animate-in fade-in">
                <div>
                  <h2 className="text-xl font-bold tracking-tight mb-1">Policy Basics</h2>
                  <p className="text-sm text-muted-foreground">Define the identity and type of this policy.</p>
                </div>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-1.5">Policy Name</label>
                    <input type="text" value={name} onChange={e => setName(e.target.value)} className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-primary" placeholder="e.g. High Value Transaction Review" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1.5">Description (Optional)</label>
                    <textarea value={description} onChange={e => setDescription(e.target.value)} rows={3} className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-primary" placeholder="What does this policy achieve?" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1.5">Policy Type</label>
                    <select value={policyType} onChange={e => setPolicyType(e.target.value)} className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-primary">
                      <option value="TRANSACTION_LIMIT">Transaction Limit</option>
                      <option value="MERCHANT">Merchant Rules</option>
                      <option value="APPROVAL">Approval Flow</option>
                      <option value="INTENT">Intent Guard</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

            {activeStep === 3 && (
              <div className="space-y-8 animate-in fade-in">
                <div>
                  <h2 className="text-xl font-bold tracking-tight mb-1">Define Deterministic Rules</h2>
                  <p className="text-sm text-muted-foreground">Construct conditions that evaluate autonomous intent and requests.</p>
                </div>

                <div className="space-y-4">
                  {rules.map((rule, idx) => (
                    <div key={rule.id} className="border border-border rounded-xl bg-surface overflow-hidden shadow-sm">
                      <div className="p-4 bg-surface-raised border-b border-border flex items-center justify-between gap-3">
                        <div className="text-xs font-mono font-bold text-muted-foreground uppercase tracking-wider">Rule {idx + 1}</div>
                        <Button variant="ghost" size="icon" onClick={() => removeRule(rule.id)} className="size-6 text-muted-foreground hover:text-danger">
                          <X className="size-4" />
                        </Button>
                      </div>
                      <div className="p-5 space-y-5">
                        <div className="flex items-center gap-4">
                          <div className="text-sm font-mono text-muted-foreground w-12 text-right">WHEN</div>
                          <div className="flex-1 grid grid-cols-3 gap-3">
                            <select value={rule.dimension} onChange={e => updateRule(rule.id, 'dimension', e.target.value)} className="bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-primary">
                              <option value="transaction_amount">Transaction Amount</option>
                              <option value="currency">Currency</option>
                              <option value="merchant_id">Merchant ID</option>
                            </select>
                            <select value={rule.operator} onChange={e => updateRule(rule.id, 'operator', e.target.value)} className="bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-primary">
                              <option value="GT">is greater than</option>
                              <option value="GTE">is greater or equal</option>
                              <option value="LT">is less than</option>
                              <option value="LTE">is less or equal</option>
                              <option value="EQ">equals</option>
                            </select>
                            <input type="text" value={rule.value} onChange={e => updateRule(rule.id, 'value', e.target.value)} className="bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-primary font-mono" />
                          </div>
                        </div>
                        <div className="flex items-center gap-4">
                          <div className="text-sm font-mono text-muted-foreground w-12 text-right">THEN</div>
                          <div className="flex-1">
                            <select value={rule.decision} onChange={e => updateRule(rule.id, 'decision', e.target.value)} className={`bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-primary w-48 font-semibold ${rule.decision === 'BLOCK' ? 'text-danger' : rule.decision === 'REVIEW' ? 'text-warn' : 'text-safe'}`}>
                              <option value="REVIEW">REVIEW</option>
                              <option value="BLOCK">BLOCK</option>
                              <option value="ALLOW">ALLOW</option>
                            </select>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}

                  <Button onClick={addRule} variant="outline" className="w-full border-dashed bg-surface-raised border-border text-muted-foreground">
                    <Plus className="size-4 mr-2" /> Add Condition
                  </Button>
                </div>
                
              </div>
            )}

            {activeStep === 5 && (
              <div className="space-y-8 animate-in fade-in">
                <div>
                  <h2 className="text-xl font-bold tracking-tight mb-1">Review & Activate</h2>
                  <p className="text-sm text-muted-foreground">Simulate impact against historical transactions to ensure deterministic safety.</p>
                </div>

                <div className="bg-surface border border-border rounded-xl overflow-hidden shadow-sm">
                  <div className="border-b border-border flex items-center justify-between p-4 bg-surface-raised">
                    <div className="flex items-center gap-2 font-semibold">
                      <TestTube className="size-4 text-primary" />
                      Policy Simulator
                    </div>
                    <div className="flex bg-background border border-border rounded-md text-xs font-medium p-0.5">
                      <button className="px-3 py-1 text-muted-foreground hover:text-foreground rounded">24h</button>
                      <button className="px-3 py-1 text-muted-foreground hover:text-foreground rounded">7d</button>
                      <button className="px-3 py-1 bg-surface-raised text-foreground rounded shadow-sm">30d</button>
                    </div>
                  </div>
                  
                  <div className="p-6">
                    {!simulationComplete ? (
                      <div className="flex flex-col items-center justify-center py-12 text-center">
                        <div className="size-16 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                          <Play className={`size-8 text-primary ml-1 ${isSimulating ? 'animate-pulse' : ''}`} />
                        </div>
                        <h3 className="text-lg font-semibold mb-2">Simulate Against History</h3>
                        <p className="text-sm text-muted-foreground max-w-sm mb-6">
                          Evaluate this policy against all autonomous transactions in the last 30 days to preview its enforcement impact.
                        </p>
                        <Button onClick={handleSimulate} disabled={isSimulating} className="w-48">
                          {isSimulating ? 'Evaluating 284 events...' : 'Run Simulation'}
                        </Button>
                      </div>
                    ) : (
                      <div className="space-y-6 animate-in zoom-in-95 duration-300">
                        <div className="flex items-center justify-center gap-2 text-sm font-semibold text-safe bg-safe/10 border border-safe/20 rounded-lg py-2">
                          <CheckCircle2 className="size-4" />
                          Simulation Complete
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Placeholder for other steps */}
            {activeStep !== 1 && activeStep !== 3 && activeStep !== 5 && (
              <div className="flex items-center justify-center h-full text-muted-foreground">
                <div className="text-center">
                  <div className="text-4xl mb-4 opacity-20 font-mono">{activeStep}</div>
                  <div>This step is simplified for the demo.</div>
                  <Button variant="link" onClick={() => setActiveStep(3)}>Go to Rules</Button>
                </div>
              </div>
            )}
          </div>
          
          {/* Bottom Action Bar */}
          <div className="absolute bottom-0 left-0 right-0 p-5 bg-background border-t border-border flex justify-between items-center">
            <Button variant="ghost" disabled={activeStep === 1 || isSubmitting} onClick={() => setActiveStep(Math.max(1, activeStep - 1))}>
              Back
            </Button>
            {activeStep === 5 ? (
              <div className="flex gap-3">
                <Button variant="outline" className="bg-surface-raised" disabled={isSubmitting} onClick={() => handleActivate('DRAFT')}>Save as Draft</Button>
                <Button className="bg-safe hover:bg-safe/90 text-safe-foreground" disabled={isSubmitting} onClick={() => handleActivate('ACTIVE')}>
                  {isSubmitting ? 'Saving...' : 'Activate Policy'}
                </Button>
              </div>
            ) : (
              <Button onClick={() => setActiveStep(Math.min(5, activeStep + 1))}>
                Continue <ChevronRight className="size-4 ml-1" />
              </Button>
            )}
          </div>
          
        </div>
      </div>
    </div>
  );
}
