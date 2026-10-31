import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Code2, BookOpen, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";

// Data
import { ApiKey, WebhookEndpoint } from "@/data/mock-developers";

// Components
import { KpiCards }              from "@/components/developers/KpiCards";
import { GetStartedCard }        from "@/components/developers/GetStartedCard";
import { ApiKeysTable }          from "@/components/developers/ApiKeysTable";
import { AgentsSection }         from "@/components/developers/AgentsSection";
import { WebhooksSection }       from "@/components/developers/WebhooksSection";
import { ApiActivityChart }      from "@/components/developers/ApiActivityChart";
import { RecentRequestsTable }   from "@/components/developers/RecentRequestsTable";
import { ApiExplorer }           from "@/components/developers/ApiExplorer";
import { DeveloperResources }    from "@/components/developers/DeveloperResources";
import { IntegrationHealth }     from "@/components/developers/IntegrationHealth";

// Modals / Drawers
import { CreateApiKeyModal }     from "@/components/developers/CreateApiKeyModal";
import { ApiKeyDrawer }          from "@/components/developers/ApiKeyDrawer";
import { WebhookDrawer }         from "@/components/developers/WebhookDrawer";
import { RegisterAgentModal }    from "@/components/developers/RegisterAgentModal";

export const Route = createFileRoute("/app/developers")({
  component: DevelopersPage,
});

function DevelopersPage() {
  const [showCreateKey,      setShowCreateKey]      = useState(false);
  const [selectedKey,        setSelectedKey]        = useState<ApiKey | null>(null);
  const [selectedWebhook,    setSelectedWebhook]    = useState<WebhookEndpoint | null>(null);
  const [showRegisterAgent,  setShowRegisterAgent]  = useState(false);

  return (
    <div className="max-w-7xl mx-auto space-y-8 py-8 animate-in fade-in duration-500 pb-16">

      {/* ── Header ───────────────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Code2 className="size-6 text-primary" />
            <h1 className="text-3xl font-bold tracking-tight text-foreground">Developer Portal</h1>
            <span className="flex items-center gap-1.5 px-2.5 py-1 bg-warn/10 border border-warn/20 rounded-md text-warn text-xs font-bold uppercase tracking-wider ml-2">
              <span className="size-1.5 rounded-full bg-warn" /> Sandbox
            </span>
          </div>
          <p className="text-muted-foreground font-medium max-w-2xl">
            Connect autonomous agents to FINSHIELD. Manage API access, webhooks, SDKs, environments, and integration health.
          </p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <Button variant="outline" className="border-border bg-background gap-2">
            <BookOpen className="size-4" /> API Docs
          </Button>
          <Button className="bg-primary hover:bg-primary/90 text-primary-foreground gap-2" onClick={() => setShowCreateKey(true)}>
            <Plus className="size-4" /> Create API Key
          </Button>
        </div>
      </div>

      {/* ── KPI Cards ────────────────────────────────────────────────────────── */}
      <KpiCards />

      {/* ── Get Started ──────────────────────────────────────────────────────── */}
      <GetStartedCard />

      {/* ── API Keys + Agents (side-by-side on lg) ───────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ApiKeysTable
          onCreateKey={() => setShowCreateKey(true)}
          onSelectKey={setSelectedKey}
        />
        <AgentsSection onRegisterAgent={() => setShowRegisterAgent(true)} />
      </div>

      {/* ── Webhooks ─────────────────────────────────────────────────────────── */}
      <WebhooksSection onSelectWebhook={setSelectedWebhook} />

      {/* ── API Activity ─────────────────────────────────────────────────────── */}
      <ApiActivityChart />

      {/* ── Recent Requests ──────────────────────────────────────────────────── */}
      <RecentRequestsTable />

      {/* ── API Explorer ─────────────────────────────────────────────────────── */}
      <ApiExplorer />

      {/* ── Quick Start + Docs ───────────────────────────────────────────────── */}
      <DeveloperResources />

      {/* ── Integration Health ───────────────────────────────────────────────── */}
      <IntegrationHealth />

      {/* ── Modals & Drawers ─────────────────────────────────────────────────── */}
      <CreateApiKeyModal
        open={showCreateKey}
        onClose={() => setShowCreateKey(false)}
      />
      <ApiKeyDrawer
        apiKey={selectedKey}
        onClose={() => setSelectedKey(null)}
      />
      <WebhookDrawer
        webhook={selectedWebhook}
        onClose={() => setSelectedWebhook(null)}
      />
      <RegisterAgentModal
        open={showRegisterAgent}
        onClose={() => setShowRegisterAgent(false)}
      />
    </div>
  );
}
