import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Play, Activity } from "lucide-react";
import { riskApi, RiskAssessment, RiskEvaluateRequest } from "@/api/risk";
import { toast } from "sonner";
import { ThreatDetailsDrawer } from "./ThreatDetailsDrawer";

export function RiskSimulator() {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<RiskAssessment | null>(null);

  const [formData, setFormData] = useState<RiskEvaluateRequest>({
    agent_id: "ag_test",
    merchant_id: "m_new",
    product_category: "ELECTRONICS",
    transaction: {
      amount: 50000,
      currency: "INR"
    }
  });

  const handleSimulate = async () => {
    try {
      setLoading(true);
      // Pass false to not persist in db, or true to see it in the log
      const res = await riskApi.evaluateRisk(formData, true);
      setResult(res);
      toast.success("Simulation Complete", {
        description: `Risk Level: ${res.risk_level} (Score: ${res.risk_score})`,
      });
      setOpen(false); // Close dialog
    } catch (e: any) {
      toast.error("Simulation Failed", {
        description: e.message
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogTrigger asChild>
          <Button variant="default" className="gap-2">
            <Play className="size-4" />
            Risk Simulator
          </Button>
        </DialogTrigger>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Activity className="size-5 text-primary" />
              Risk Engine Simulator
            </DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label>Agent ID</Label>
              <Input 
                value={formData.agent_id} 
                onChange={e => setFormData({...formData, agent_id: e.target.value})} 
                placeholder="ag_..."
              />
              <p className="text-xs text-muted-foreground">Try: "ag_velocity_high" or "ag_behavior_erratic"</p>
            </div>
            <div className="space-y-2">
              <Label>Merchant ID</Label>
              <Input 
                value={formData.merchant_id || ""} 
                onChange={e => setFormData({...formData, merchant_id: e.target.value})} 
                placeholder="m_..."
              />
              <p className="text-xs text-muted-foreground">Try: "m_trusted", "m_new", "m_high_risk"</p>
            </div>
            <div className="space-y-2">
              <Label>Transaction Amount</Label>
              <Input 
                type="number"
                value={formData.transaction?.amount || ""} 
                onChange={e => setFormData({
                  ...formData, 
                  transaction: { ...formData.transaction!, amount: Number(e.target.value) }
                })} 
              />
            </div>
            <Button onClick={handleSimulate} disabled={loading} className="w-full mt-4">
              {loading ? "Evaluating..." : "Run Evaluation"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Show the drawer immediately when result is available */}
      <ThreatDetailsDrawer 
        open={result !== null}
        onOpenChange={(open) => !open && setResult(null)}
        assessment={result}
      />
    </>
  );
}
