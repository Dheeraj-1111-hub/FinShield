import { FileText, Code, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";

export function DevelopersHeader() {
  return (
    <header className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 pb-6 border-b border-border">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-2">
          <Code className="size-6 text-primary" />
          Developer Portal
        </h1>
        <p className="text-muted-foreground mt-1 max-w-2xl">
          Connect autonomous agents to FINSHIELD. Manage API access, webhooks, SDKs, environments, and integration health.
        </p>
      </div>
      <div className="flex items-center gap-2">
        <Button variant="outline" className="border-border bg-background" onClick={() => { window.open("/api/docs", "_blank"); }}>
          <FileText className="size-4 mr-2" /> API Docs
        </Button>
        <Button className="bg-primary hover:bg-primary/90 text-primary-foreground">
          + Create API Key
        </Button>
      </div>
      <div className="mt-2 sm:mt-0 text-sm font-medium text-muted-foreground">
        <span className="px-2 py-0.5 rounded bg-safe/10 text-safe border border-safe/20">SANDBOX</span>
      </div>
    </header>
  );
}
