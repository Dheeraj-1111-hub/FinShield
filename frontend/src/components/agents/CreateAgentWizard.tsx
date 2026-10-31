import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { 
  Dialog, DialogContent, DialogDescription, DialogFooter, 
  DialogHeader, DialogTitle, DialogTrigger 
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, ShieldCheck } from "lucide-react";
import { agentsApi, AgentCreate, AgentType } from "@/api/agents";

export function CreateAgentWizard() {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [type, setType] = useState<AgentType>("SHOPPING");
  const [currency, setCurrency] = useState<string>("INR");

  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: (data: AgentCreate) => agentsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agents"] });
      setOpen(false);
      resetForm();
    },
  });

  const resetForm = () => {
    setName("");
    setDescription("");
    setType("SHOPPING");
    setCurrency("INR");
  };

  const handleOpenChange = (val: boolean) => {
    setOpen(val);
    if (!val) {
      setTimeout(resetForm, 300);
    }
  };

  const handleCreate = () => {
    createMutation.mutate({
      name,
      description,
      type,
      currency
    });
  };

  const isFormValid = name.trim().length > 0;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button className="shrink-0 bg-primary text-primary-foreground hover:bg-primary/90">
          <Plus className="mr-2 size-4" />
          Create Agent
        </Button>
      </DialogTrigger>
      
      <DialogContent className="sm:max-w-[500px] bg-background border-border">
        <DialogHeader>
          <DialogTitle className="text-xl">Create Agent</DialogTitle>
          <DialogDescription>
            Define a new autonomous agent. Advanced capabilities and financial authority will be configured later.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="name">Agent Name</Label>
            <Input 
              id="name"
              placeholder="e.g. Shopping Agent" 
              className="bg-surface border-border" 
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="type">Agent Type</Label>
            <Select value={type} onValueChange={(val) => setType(val as AgentType)}>
              <SelectTrigger className="bg-surface border-border">
                <SelectValue placeholder="Select type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="SHOPPING">Shopping</SelectItem>
                <SelectItem value="PAYMENT">Payment</SelectItem>
                <SelectItem value="FINANCE">Finance</SelectItem>
                <SelectItem value="OPERATIONS">Operations</SelectItem>
                <SelectItem value="CUSTOM">Custom</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="currency">Operational Currency</Label>
            <Select value={currency} onValueChange={(val) => setCurrency(val)}>
              <SelectTrigger className="bg-surface border-border">
                <SelectValue placeholder="Select currency" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="INR">INR (₹ - Indian Rupee)</SelectItem>
                <SelectItem value="USD">USD ($ - US Dollar)</SelectItem>
                <SelectItem value="EUR">EUR (€ - Euro)</SelectItem>
                <SelectItem value="GBP">GBP (£ - British Pound)</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Input 
              id="description"
              placeholder="What does this agent do?" 
              className="bg-surface border-border" 
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
        </div>
        
        <DialogFooter className="mt-4">
          <Button 
            variant="ghost" 
            onClick={() => setOpen(false)}
            className="text-muted-foreground"
            disabled={createMutation.isPending}
          >
            Cancel
          </Button>
          <Button 
            onClick={handleCreate} 
            disabled={!isFormValid || createMutation.isPending}
            className="bg-primary text-primary-foreground"
          >
            {createMutation.isPending ? "Creating..." : (
              <>
                <ShieldCheck className="mr-2 size-4" /> Create Agent
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
