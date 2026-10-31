import { createFileRoute, Link } from "@tanstack/react-router";
import {
  ArrowRight,
  Ban,
  Braces,
  FileSearch,
  Gauge,
  ScrollText,
  ShieldCheck,
  Target,
  Activity,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { SiteShell, Section } from "@/components/site/SiteShell";
import { HeroDemo } from "@/components/site/HeroDemo";
import { Pipeline } from "@/components/site/Pipeline";
import { AttackDemo } from "@/components/site/AttackDemo";

const TITLE = "FINSHIELD — Trust infrastructure for autonomous finance";
const DESCRIPTION =
  "FINSHIELD is runtime security for AI agents that spend money. It verifies intent, agent behaviour, transaction risk and financial policy before any payment is allowed.";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: TITLE },
      { name: "description", content: DESCRIPTION },
      { property: "og:title", content: TITLE },
      { property: "og:description", content: DESCRIPTION },
    ],
  }),
  component: Landing,
});

const FEATURES = [
  {
    icon: Target,
    title: "Intent Verification",
    body: "Does the transaction match what the user actually asked for? Every payment is scored against a structured, signed intent object.",
  },
  {
    icon: Activity,
    title: "Agent Behavior",
    body: "Is the agent behaving normally? Tool usage, pacing and merchant patterns are modelled per agent so drift is measurable.",
  },
  {
    icon: Gauge,
    title: "Transaction Intelligence",
    body: "Does the transaction look risky? Classic fraud signals fused with graph features across accounts, merchants and agents.",
  },
  {
    icon: ScrollText,
    title: "Policy Enforcement",
    body: "Does it satisfy financial constraints? Deterministic limits, categories, geographies and approval thresholds.",
  },
  {
    icon: ShieldCheck,
    title: "Runtime Protection",
    body: "Can we stop unsafe actions before payment? Decisions are made in the authorization path, not in a nightly batch job.",
  },
  {
    icon: FileSearch,
    title: "Auditability",
    body: "Can we explain exactly what happened? Intent, trajectory, risk, policy and decision are replayable evidence.",
  },
];

const RESEARCH = [
  {
    title: "Intent Alignment",
    body: "Measuring the distance between an authorized objective and a proposed transaction, including partial and drifting intents.",
  },
  {
    title: "Trajectory Security",
    body: "Detecting untrusted external influence inside an agent's action sequence without inspecting private reasoning.",
  },
  {
    title: "Agentic Payment Safety",
    body: "Authorization semantics for non-human principals: scoped credentials, revocation, and delegated spending envelopes.",
  },
  {
    title: "Financial Risk",
    body: "Graph and behavioural modelling of merchants, accounts and agents to catch coordinated abuse a single transaction hides.",
  },
  {
    title: "Adversarial Evaluation",
    body: "A benchmark of prompt injection, intent manipulation, budget escalation and transaction splitting, scored end to end.",
  },
];

function Landing() {
  return (
    <SiteShell>
      {/* 1 — HERO */}
      <section className="relative overflow-hidden border-b border-border">
        <div className="pointer-events-none absolute inset-0 grid-backdrop" aria-hidden />
        <div className="relative mx-auto grid max-w-7xl items-center gap-16 px-6 py-20 lg:grid-cols-[1.05fr_minmax(0,460px)] lg:py-28">
          <div>
            <p className="eyebrow">FINSHIELD</p>
            <h1 className="mt-5 text-4xl font-semibold leading-[1.05] tracking-tight text-balance sm:text-5xl lg:text-6xl">
              Trust infrastructure
              <br />
              for autonomous finance
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-relaxed text-muted-foreground">
              AI agents can act on your behalf. FINSHIELD makes sure they act within your intent —
              verifying every action and every rupee before money moves.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button asChild size="lg">
                <Link to="/signup">
                  Start Building <ArrowRight className="size-4" />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <a href="/how-it-works">See How It Works</a>
              </Button>
            </div>
            <ul className="mt-10 flex flex-wrap gap-x-8 gap-y-3 text-sm text-muted-foreground">
              {["Runtime protection", "Intent verification", "Financial policy enforcement"].map(
                (t) => (
                  <li key={t} className="flex items-center gap-2">
                    <span className="size-1.5 rounded-full bg-primary" aria-hidden />
                    {t}
                  </li>
                ),
              )}
            </ul>
          </div>
          <HeroDemo />
        </div>
      </section>

      {/* 2 — PROBLEM */}
      <Section
        eyebrow="The problem"
        title="AI can reason. AI can act. AI can spend. But who controls the decision?"
        description="A traditional payment system sees a technically authorized transaction. A traditional fraud model sees only the final amount. Neither sees the chain of decisions that produced it."
      >
        <div className="grid gap-6 md:grid-cols-2">
          <ChainCard
            label="Traditional payment"
            tone="muted"
            nodes={["Human", "Pay", "Payment"]}
            note="One principal. One decision. The authorizing party and the acting party are the same."
          />
          <ChainCard
            label="Agentic payment"
            tone="danger"
            nodes={["Human", "Agent", "Tools", "Web", "Decision", "Payment"]}
            note="Five hops between the person and the money. Any of them can be manipulated — and the payment still looks authorized."
          />
        </div>
      </Section>

      {/* 3 — HOW IT WORKS */}
      <Section
        eyebrow="How FINSHIELD works"
        title="Six stages between an instruction and a payment"
        description="Hover or select a stage to see what FINSHIELD evaluates at that point in the chain."
      >
        <Pipeline />
      </Section>

      {/* 4 — DEMO */}
      <Section
        eyebrow="Product demo"
        title="Watch the same instruction succeed, then get blocked"
        description="This is the golden path of the product: intent, agent activity, FINSHIELD evaluation, decision."
      >
        <AttackDemo />
      </Section>

      {/* 5 — FEATURES */}
      <Section
        eyebrow="Capabilities"
        title="Four questions, evaluated continuously"
        description="Intent, behaviour, risk and policy — fused into a single allow, review or block decision."
      >
        <div className="grid gap-px overflow-hidden rounded-xl border border-border bg-border sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <div key={f.title} className="bg-surface p-6 transition-colors hover:bg-surface-raised">
              <f.icon className="size-5 text-primary" aria-hidden />
              <h3 className="mt-4 text-base font-medium">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{f.body}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* 6 — DEVELOPERS */}
      <Section
        eyebrow="For developers"
        title="One call in the authorization path"
        description="Drop the SDK between your agent and your payment provider. FINSHIELD returns a decision, a risk score and the evidence behind it."
      >
        <div className="grid gap-8 lg:grid-cols-[300px_minmax(0,1fr)]">
          <ol className="space-y-3">
            {["Your AI agent", "FINSHIELD SDK", "Risk + policy + intent", "Payment"].map((n, i) => (
              <li
                key={n}
                className="flex items-center gap-3 rounded-lg border border-border bg-surface px-4 py-3 text-sm"
              >
                <span className="font-mono text-xs text-muted-foreground">0{i + 1}</span>
                {n}
              </li>
            ))}
          </ol>
          <CodeBlock
            filename="authorize.ts"
            code={`import { Finshield } from "@finshield/sdk";

const fs = new Finshield({ apiKey: process.env.FINSHIELD_KEY });

const decision = await fs.authorization.check({
  agent_id: "agt_shopping_01",
  intent_id: "int_9f22a1",
  transaction: {
    amount: 74999,
    currency: "INR",
    merchant_id: "mrc_dell_in",
    category: "electronics",
  },
});

if (decision.decision !== "ALLOW") {
  throw new BlockedByPolicy(decision.reasons);
}`}
          />
        </div>
        <div className="mt-6">
          <Button asChild variant="outline">
            <a href="/developers">
              <Braces className="size-4" /> Read the API reference
            </a>
          </Button>
        </div>
      </Section>

      {/* 7 — RESEARCH */}
      <Section
        eyebrow="Research"
        title="Built on measurable results, not claims"
        description="FINSHIELD is evaluated against rules engines, transaction ML, LLM judges and trajectory models on a 10,000-scenario adversarial benchmark."
      >
        <div className="grid gap-px overflow-hidden rounded-xl border border-border bg-border md:grid-cols-2 lg:grid-cols-3">
          {RESEARCH.map((r) => (
            <div key={r.title} className="bg-surface p-6">
              <h3 className="font-mono text-xs tracking-wide text-primary">
                {r.title.toUpperCase()}
              </h3>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{r.body}</p>
            </div>
          ))}
          <div className="flex items-center bg-surface p-6">
            <Button asChild variant="ghost">
              <a href="/research">
                Explore the research <ArrowRight className="size-4" />
              </a>
            </Button>
          </div>
        </div>
      </Section>

      {/* 8 — CTA */}
      <section>
        <div className="mx-auto max-w-7xl px-6 py-24">
          <div className="panel relative overflow-hidden px-8 py-16 text-center">
            <div className="pointer-events-none absolute inset-0 grid-backdrop opacity-40" aria-hidden />
            <div className="relative">
              <Ban className="mx-auto size-6 text-primary" aria-hidden />
              <h2 className="mt-6 text-3xl font-semibold tracking-tight text-balance md:text-4xl">
                Build agents that can act without losing control
              </h2>
              <p className="mx-auto mt-4 max-w-xl text-muted-foreground">
                Create your first agent, set its financial permissions, and watch FINSHIELD evaluate
                every transaction it attempts.
              </p>
              <Button asChild size="lg" className="mt-8">
                <Link to="/signup">
                  Create your first agent <ArrowRight className="size-4" />
                </Link>
              </Button>
            </div>
          </div>
        </div>
      </section>
    </SiteShell>
  );
}

function ChainCard({
  label,
  nodes,
  note,
  tone,
}: {
  label: string;
  nodes: string[];
  note: string;
  tone: "muted" | "danger";
}) {
  return (
    <div className="panel p-6">
      <p className="eyebrow">{label}</p>
      <ol className="mt-6 space-y-2">
        {nodes.map((n, i) => (
          <li key={n}>
            <div
              className={
                "rounded-lg border px-4 py-2.5 text-sm " +
                (tone === "danger" && i > 0 && i < nodes.length - 1
                  ? "border-warn/30 bg-warn-muted text-foreground"
                  : "border-border bg-surface-raised text-foreground")
              }
            >
              {n}
            </div>
            {i < nodes.length - 1 ? (
              <div className="ml-4 h-3 w-px bg-border-strong" aria-hidden />
            ) : null}
          </li>
        ))}
      </ol>
      <p className="mt-6 text-sm leading-relaxed text-muted-foreground">{note}</p>
    </div>
  );
}

export function CodeBlock({ filename, code }: { filename: string; code: string }) {
  return (
    <div className="overflow-hidden rounded-xl border border-border bg-surface">
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <span className="font-mono text-xs text-muted-foreground">{filename}</span>
        <span className="flex gap-1.5" aria-hidden>
          <span className="size-2 rounded-full bg-muted-foreground/30" />
          <span className="size-2 rounded-full bg-muted-foreground/30" />
          <span className="size-2 rounded-full bg-muted-foreground/30" />
        </span>
      </div>
      <pre className="overflow-x-auto p-5 font-mono text-[13px] leading-relaxed text-foreground/90">
        <code>{code}</code>
      </pre>
    </div>
  );
}
