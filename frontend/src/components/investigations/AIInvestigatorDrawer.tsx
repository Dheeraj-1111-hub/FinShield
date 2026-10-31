import { useState } from "react";
import { X, ArrowRight, Sparkles, Search, CheckCircle2, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

interface AIInvestigatorDrawerProps {
  onClose: () => void;
}

export function AIInvestigatorDrawer({ onClose }: AIInvestigatorDrawerProps) {
  const [query, setQuery] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<boolean>(false);

  const handleInvestigate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query) return;
    
    setIsAnalyzing(true);
    setResult(false);
    
    setTimeout(() => {
      setIsAnalyzing(false);
      setResult(true);
    }, 2000); // Simulate AI thinking time
  };

  const handleExampleClick = (text: string) => {
    setQuery(text);
  };

  return (
    <div className="absolute inset-y-0 right-0 w-[600px] bg-background border-l border-border shadow-2xl flex flex-col z-50 animate-in slide-in-from-right duration-300">
      
      {/* Header */}
      <div className="h-14 border-b border-border flex items-center justify-between px-5 bg-surface shrink-0">
        <div className="flex items-center gap-3">
          <div className="text-sm font-semibold text-primary flex items-center gap-2">
            <Sparkles className="size-4" />
            AI Investigator
          </div>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} className="size-8 rounded-full">
          <X className="size-4" />
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-8 custom-scrollbar">
        
        {/* Intro */}
        {!result && !isAnalyzing && (
          <div className="animate-in fade-in">
            <h2 className="text-2xl font-bold tracking-tight mb-2">What do you want to investigate?</h2>
            <p className="text-sm text-muted-foreground mb-6">
              Analyze an autonomous financial action and reconstruct the complete chain of decisions in natural language.
            </p>

            <form onSubmit={handleInvestigate} className="relative mb-8">
              <Search className="size-5 absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input 
                type="text" 
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search transaction, agent, order or event..." 
                className="w-full bg-surface border border-border rounded-xl pl-12 pr-4 py-4 text-base focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all shadow-sm"
              />
              <Button type="submit" className="absolute right-2 top-1/2 -translate-y-1/2 h-10 px-4 shadow-[0_0_15px_rgba(var(--primary),0.3)]">
                Investigate
              </Button>
            </form>

            <div>
              <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Examples</div>
              <div className="space-y-2">
                {[
                  "Why was PAY-92829 blocked?",
                  "What caused the Shopping Agent to diverge?",
                  "Show all blocked actions from the Finance Agent.",
                  "Why was this transaction considered high risk?"
                ].map((example, idx) => (
                  <button 
                    key={idx}
                    onClick={() => handleExampleClick(example)}
                    className="block w-full text-left px-4 py-3 bg-surface hover:bg-surface-raised border border-border rounded-lg text-sm transition-colors text-foreground/80 hover:text-foreground"
                  >
                    "{example}"
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Loading State */}
        {isAnalyzing && (
          <div className="flex flex-col items-center justify-center py-20 text-center animate-in fade-in duration-300">
            <div className="size-16 rounded-full bg-primary/10 flex items-center justify-center mb-6 relative">
              <div className="absolute inset-0 rounded-full border-2 border-primary border-t-transparent animate-spin" />
              <Sparkles className="size-6 text-primary animate-pulse" />
            </div>
            <h3 className="text-lg font-semibold mb-6">Analyzing SEC-99382...</h3>
            
            <div className="w-64 space-y-3 text-left">
              <div className="flex items-center gap-3 text-sm text-muted-foreground animate-pulse">
                <CheckCircle2 className="size-4 text-primary" /> Reconstructing agent trajectory...
              </div>
              <div className="flex items-center gap-3 text-sm text-muted-foreground animate-pulse" style={{ animationDelay: "200ms" }}>
                <CheckCircle2 className="size-4 text-primary" /> Comparing original intent...
              </div>
              <div className="flex items-center gap-3 text-sm text-muted-foreground animate-pulse" style={{ animationDelay: "400ms" }}>
                <CheckCircle2 className="size-4 text-primary" /> Evaluating policy decisions...
              </div>
              <div className="flex items-center gap-3 text-sm text-muted-foreground opacity-50">
                <div className="size-4 rounded-full border-2 border-muted-foreground border-t-transparent animate-spin" /> Correlating payment events...
              </div>
            </div>
          </div>
        )}

        {/* Result State */}
        {result && (
          <div className="space-y-8 animate-in slide-in-from-bottom-4 duration-500">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xs font-semibold text-primary uppercase tracking-wider mb-1">Investigation Result</div>
                <h2 className="text-2xl font-bold tracking-tight">PAY-92829</h2>
              </div>
              <Button variant="ghost" size="sm" onClick={() => {setResult(false); setQuery("");}} className="text-muted-foreground">
                New Query
              </Button>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="bg-danger/10 border border-danger/20 rounded-xl p-4">
                <div className="text-xs font-semibold text-danger uppercase tracking-wider mb-1">Decision</div>
                <div className="text-xl font-bold font-mono text-danger">BLOCKED</div>
              </div>
              <div className="bg-surface border border-border rounded-xl p-4">
                <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">AI Confidence</div>
                <div className="text-xl font-bold font-mono">97%</div>
              </div>
            </div>

            <div className="bg-surface border border-border rounded-xl p-6 shadow-sm">
              <h3 className="text-base font-bold mb-4 uppercase tracking-wider text-muted-foreground text-xs">Why was this blocked?</h3>
              
              <div className="space-y-6">
                <div className="flex gap-4 items-start">
                  <div className="size-6 rounded-full bg-danger/10 flex items-center justify-center shrink-0 mt-0.5">
                    <span className="text-xs font-bold text-danger">1</span>
                  </div>
                  <div>
                    <div className="font-semibold mb-1">Intent divergence</div>
                    <div className="text-sm text-muted-foreground">User intent was to purchase a laptop under ₹80K. Agent executed a purchase for an investment product.</div>
                  </div>
                </div>
                
                <div className="flex gap-4 items-start">
                  <div className="size-6 rounded-full bg-danger/10 flex items-center justify-center shrink-0 mt-0.5">
                    <span className="text-xs font-bold text-danger">2</span>
                  </div>
                  <div>
                    <div className="font-semibold mb-1">Capability violation</div>
                    <div className="text-sm text-muted-foreground">The Shopping Agent attempted a financial product transaction outside its authorized commerce capabilities.</div>
                  </div>
                </div>

                <div className="flex gap-4 items-start">
                  <div className="size-6 rounded-full bg-danger/10 flex items-center justify-center shrink-0 mt-0.5">
                    <span className="text-xs font-bold text-danger">3</span>
                  </div>
                  <div>
                    <div className="font-semibold mb-1">Authority violation</div>
                    <div className="text-sm text-muted-foreground">The requested amount of ₹1,50,000 exceeded the agent's permitted transaction authority limit (₹1,00,000).</div>
                  </div>
                </div>

                <div className="flex gap-4 items-start">
                  <div className="size-6 rounded-full bg-danger/10 flex items-center justify-center shrink-0 mt-0.5">
                    <span className="text-xs font-bold text-danger">4</span>
                  </div>
                  <div>
                    <div className="font-semibold mb-1">Policy violation</div>
                    <div className="text-sm text-muted-foreground">The <span className="font-mono bg-surface-raised px-1 py-0.5 rounded text-foreground">Financial Product Restrictions v4</span> policy explicitly prohibits this action.</div>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-safe/5 border border-safe/20 rounded-xl p-5">
              <div className="flex items-start gap-3">
                <CheckCircle2 className="size-5 text-safe mt-0.5 shrink-0" />
                <div>
                  <div className="font-bold text-safe mb-1">Conclusion</div>
                  <div className="text-sm text-foreground/80 mb-4">The transaction was correctly blocked by FINSHIELD deterministic controls based on severe intent divergence and policy violations.</div>
                  
                  <div className="flex gap-3">
                    <Button variant="outline" className="bg-background border-border">Open Full Investigation</Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
