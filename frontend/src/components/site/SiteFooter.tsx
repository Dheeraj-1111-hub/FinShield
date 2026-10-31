import { Link } from "@tanstack/react-router";
import { Logo } from "./Logo";

const COLUMNS = [
  {
    title: "Product",
    links: [
      { to: "/product", label: "Overview" },
      { to: "/how-it-works", label: "How it works" },
      { to: "/pricing", label: "Pricing" },
    ],
  },
  {
    title: "Platform",
    links: [
      { to: "/developers", label: "Developers" },
      { to: "/security", label: "Security" },
      { to: "/research", label: "Research" },
    ],
  },
  {
    title: "Account",
    links: [
      { to: "/login", label: "Sign in" },
      { to: "/signup", label: "Create account" },
    ],
  },
] as const;

export function SiteFooter() {
  return (
    <footer className="border-t border-border bg-surface/40">
      <div className="mx-auto grid max-w-7xl gap-12 px-6 py-16 md:grid-cols-[1.5fr_repeat(3,1fr)]">
        <div>
          <Logo />
          <p className="mt-4 max-w-xs text-sm leading-relaxed text-muted-foreground">
            Runtime trust and risk infrastructure for autonomous financial agents. Money moves only
            when intent, behavior, risk and policy agree.
          </p>
        </div>
        {COLUMNS.map((col) => (
          <div key={col.title}>
            <h3 className="eyebrow">{col.title}</h3>
            <ul className="mt-4 space-y-2.5">
              {col.links.map((l) => (
                <li key={l.to}>
                  <a
                    href={l.to}
                    className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                  >
                    {l.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="border-t border-border">
        <div className="mx-auto flex max-w-7xl flex-col gap-2 px-6 py-6 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <p>© {new Date().getFullYear()} FINSHIELD. All rights reserved.</p>
          <p className="font-mono">status: all systems operational</p>
        </div>
      </div>
    </footer>
  );
}
