import { useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { authoritiesApi } from "@/api/authorities";
import { agentsApi } from "@/api/agents";
import { intentsApi } from "@/api/intents";
import { ShieldCheck, ArrowLeft, Loader2, Check } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/app/authorities/new")({
  component: NewAuthorityRoute,
});

export const ALL_CAPABILITIES = [
  "SEARCH_PRODUCTS",
  "COMPARE_PRODUCTS",
  "CREATE_CART",
  "MANAGE_CART",
  "ADD_CART_ITEM",
  "UPDATE_CART",
  "CREATE_ORDER",
  "CANCEL_ORDER",
  "PAY_ORDER",
  "REQUEST_PAYMENT",
  "EXECUTE_PAYMENT",
  "REQUEST_REFUND"
];

function NewAuthorityRoute() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  
  const [agentId, setAgentId] = useState<string>("");
  const [intentId, setIntentId] = useState<string>("");
  const [capabilities, setCapabilities] = useState<string[]>([]);
  const [monetaryLimit, setMonetaryLimit] = useState<string>("");
  const [currency, setCurrency] = useState<string>("INR");

  const { data: agents = [] } = useQuery({
    queryKey: ["agents"],
    queryFn: agentsApi.list
  });

  const { data: intents = [] } = useQuery({
    queryKey: ["intents"],
    queryFn: () => intentsApi.list()
  });

  const createMutation = useMutation({
    mutationFn: (data: any) => authoritiesApi.create(data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["authorities"] });
      toast.success("Authority delegated successfully");
      navigate({ to: `/app/authorities/${data.id}` });
    },
    onError: (err) => {
      toast.error("Failed to delegate authority");
    }
  });

  const handleToggleCapability = (cap: string) => {
    setCapabilities(prev => 
      prev.includes(cap) ? prev.filter(c => c !== cap) : [...prev, cap]
    );
  };

  const handleCreate = () => {
    if (!agentId) {
      toast.error("Please select an Agent");
      return;
    }
    if (capabilities.length === 0) {
      toast.error("Please select at least one capability");
      return;
    }

    createMutation.mutate({
      agent_id: agentId,
      intent_id: intentId || undefined,
      allowed_capabilities: capabilities,
      monetary_limit: monetaryLimit ? parseFloat(monetaryLimit) : undefined,
      currency: currency
    });
  };

  return (
    <div className="w-full max-w-3xl mx-auto space-y-6">
      <div className="flex items-center gap-4 mb-6">
        <Button variant="ghost" size="icon" onClick={() => window.history.back()}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Delegate Authority</h1>
          <p className="text-muted-foreground mt-1">
            Grant specific capabilities and limits to an agent, optionally bound to an Intent.
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-primary">
            <ShieldCheck className="h-5 w-5" />
            Authority Configuration
          </CardTitle>
          <CardDescription>
            This creates an immutable versioned authority record.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label>Select Agent *</Label>
            <select 
              className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
              value={agentId}
              onChange={(e) => setAgentId(e.target.value)}
            >
              <option value="">-- Select an Agent --</option>
              {agents.map(agent => (
                <option key={agent.id} value={agent.id}>{agent.name}</option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <Label>Attach Intent (Optional)</Label>
            <select 
              className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
              value={intentId}
              onChange={(e) => setIntentId(e.target.value)}
            >
              <option value="">-- No Intent --</option>
              {intents.filter(i => i.status === "ACTIVE" || i.status === "DRAFT").map(intent => (
                <option key={intent.id} value={intent.id}>{intent.title} (v{intent.version})</option>
              ))}
            </select>
            <p className="text-xs text-muted-foreground">
              If an intent is attached, the agent will also be evaluated for intent alignment.
            </p>
          </div>

          <div className="space-y-3">
            <Label>Allowed Capabilities *</Label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-4 border rounded-md bg-muted/20">
              {ALL_CAPABILITIES.map(cap => (
                <div key={cap} className="flex items-center space-x-2">
                  <Checkbox 
                    id={`cap-${cap}`} 
                    checked={capabilities.includes(cap)}
                    onCheckedChange={() => handleToggleCapability(cap)}
                  />
                  <Label htmlFor={`cap-${cap}`} className="text-sm font-medium cursor-pointer">
                    {cap}
                  </Label>
                </div>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Monetary Limit</Label>
              <Input 
                type="number" 
                placeholder="e.g. 5000"
                value={monetaryLimit}
                onChange={(e) => setMonetaryLimit(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">Leave empty for no limit</p>
            </div>
            <div className="space-y-2">
              <Label>Currency</Label>
              <select 
                className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
              >
                <option value="INR">INR (₹)</option>
                <option value="USD">USD ($)</option>
                <option value="EUR">EUR (€)</option>
              </select>
            </div>
          </div>
        </CardContent>
        <CardFooter className="border-t pt-6">
          <Button 
            className="w-full" 
            onClick={handleCreate}
            disabled={createMutation.isPending || !agentId || capabilities.length === 0}
          >
            {createMutation.isPending ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Check className="h-4 w-4 mr-2" />
            )}
            Delegate Authority
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
