import { useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { intentsApi, IntentExtractionResult } from "@/api/intents";
import { Bot, Target, Wand2, Check, ArrowLeft, Loader2 } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/app/intents/new")({
  component: NewIntentRoute,
});

function NewIntentRoute() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  
  const [naturalLanguage, setNaturalLanguage] = useState("");
  const [extractionResult, setExtractionResult] = useState<IntentExtractionResult | null>(null);
  
  const [title, setTitle] = useState("");
  const [constraintsJson, setConstraintsJson] = useState("{}");
  const [intentType, setIntentType] = useState<"PURCHASE" | "SEARCH" | "COMPARE" | "BOOKING" | "TRANSFER" | "PAYMENT" | "OTHER">("OTHER");

  const extractMutation = useMutation({
    mutationFn: (text: string) => intentsApi.extract(text),
    onSuccess: (data) => {
      setExtractionResult(data);
      setTitle(data.proposed_title || "Extracted Intent");
      setIntentType(data.proposed_type);
      setConstraintsJson(JSON.stringify(data.proposed_constraints, null, 2));
      toast.success("Intent extracted successfully");
    },
    onError: (err) => {
      toast.error("Failed to extract intent");
    }
  });

  const createMutation = useMutation({
    mutationFn: (data: { title: string; natural_language_request: string; structured_constraints: any; intent_type: any }) => 
      intentsApi.create(data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["intents"] });
      toast.success("Intent created successfully");
      navigate({ to: `/app/intents/${data.id}` });
    },
    onError: (err: any) => {
      const errorData = err?.response?.data;
      const details = errorData?.error?.details || errorData?.detail;
      if (Array.isArray(details)) {
        const msg = details.map((d: any) => `${d.loc?.join(".") || "field"}: ${d.msg}`).join("; ");
        toast.error(`Validation error: ${msg}`);
      } else if (typeof details === "string") {
        toast.error(details);
      } else if (errorData?.error?.message) {
        toast.error(errorData.error.message);
      } else {
        toast.error("Failed to create intent");
      }
    }
  });

  const handleExtract = () => {
    if (!naturalLanguage.trim()) {
      toast.error("Please enter a natural language request first");
      return;
    }
    extractMutation.mutate(naturalLanguage);
  };

  const handleCreate = () => {
    let constraints = {};
    try {
      constraints = JSON.parse(constraintsJson);
    } catch (e) {
      toast.error("Invalid JSON in constraints");
      return;
    }

    if (!title.trim()) {
      toast.error("Please provide a title");
      return;
    }

    const nlRequest = naturalLanguage.trim() || title.trim();

    createMutation.mutate({
      title: title.trim(),
      natural_language_request: nlRequest,
      structured_constraints: constraints,
      intent_type: intentType
    });
  };

  return (
    <div className="w-full max-w-5xl mx-auto space-y-6">
      <div className="flex items-center gap-4 mb-6">
        <Button variant="ghost" size="icon" onClick={() => window.history.back()}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Create Intent</h1>
          <p className="text-muted-foreground mt-1">
            Define boundaries and constraints for an agent using natural language.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left Side: NL Extraction */}
        <Card className="flex flex-col">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-primary">
              <Bot className="h-5 w-5" />
              1. Extract from Natural Language
            </CardTitle>
            <CardDescription>
              Describe what the user wants to do, and FINSHIELD will automatically extract the constraints.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex-1 space-y-4">
            <div className="space-y-2">
              <Label>User's Request</Label>
              <Textarea 
                placeholder="e.g., I want to buy a laptop for college under ₹80,000. It must be Lenovo or Dell, and from Amazon or Flipkart."
                className="min-h-[150px] resize-y"
                value={naturalLanguage}
                onChange={(e) => setNaturalLanguage(e.target.value)}
              />
            </div>
            
            <Button 
              className="w-full bg-secondary text-secondary-foreground hover:bg-secondary/80" 
              onClick={handleExtract}
              disabled={extractMutation.isPending || !naturalLanguage.trim()}
            >
              {extractMutation.isPending ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Wand2 className="h-4 w-4 mr-2" />
              )}
              Extract Constraints
            </Button>

            {extractionResult && (
              <div className="mt-6 p-4 bg-muted/30 rounded-lg border text-sm">
                <h4 className="font-semibold mb-2">Extraction Explanation</h4>
                <p className="text-muted-foreground">{extractionResult.explanation}</p>
                
                <div className="mt-4">
                  <h4 className="font-semibold mb-2">Detected Signals</h4>
                  <div className="flex flex-wrap gap-2">
                    {extractionResult.signals?.map((s, idx) => (
                      <span key={idx} className="px-2 py-1 bg-background border rounded-md text-xs">
                        <span className="text-muted-foreground mr-1">{s.field}:</span>
                        <span className="font-mono">{JSON.stringify(s.value)}</span>
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Right Side: Manual Editing */}
        <Card className="flex flex-col">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-primary">
              <Target className="h-5 w-5" />
              2. Review & Refine
            </CardTitle>
            <CardDescription>
              Review the extracted intent, edit the JSON constraints directly if needed, and save.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex-1 space-y-4">
            <div className="space-y-2">
              <Label>Intent Title</Label>
              <Input 
                placeholder="e.g., College Laptop Purchase"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>
            
            <div className="space-y-2">
              <Label>Intent Type</Label>
              <select 
                className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                value={intentType}
                onChange={(e) => setIntentType(e.target.value as any)}
              >
                <option value="PURCHASE">Purchase</option>
                <option value="SEARCH">Search</option>
                <option value="COMPARE">Compare</option>
                <option value="BOOKING">Booking</option>
                <option value="TRANSFER">Transfer</option>
                <option value="PAYMENT">Payment</option>
                <option value="OTHER">Other</option>
              </select>
            </div>

            <div className="space-y-2 flex-1 flex flex-col">
              <Label>Structured Constraints (JSON)</Label>
              <Textarea 
                className="flex-1 font-mono text-sm min-h-[250px]"
                value={constraintsJson}
                onChange={(e) => setConstraintsJson(e.target.value)}
              />
            </div>
          </CardContent>
          <CardFooter className="border-t pt-6">
            <Button 
              className="w-full" 
              onClick={handleCreate}
              disabled={createMutation.isPending || !title.trim() || !constraintsJson.trim()}
            >
              {createMutation.isPending ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Check className="h-4 w-4 mr-2" />
              )}
              Create Intent
            </Button>
          </CardFooter>
        </Card>
      </div>
    </div>
  );
}
