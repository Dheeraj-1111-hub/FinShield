import type { ReactNode } from "react";
import { SiteHeader } from "./SiteHeader";
import { SiteFooter } from "./SiteFooter";

export function SiteShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[100] focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-sm focus:text-primary-foreground"
      >
        Skip to content
      </a>
      <SiteHeader />
      <main id="main" className="flex-1">
        {children}
      </main>
      <SiteFooter />
    </div>
  );
}

export function PageHero({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <section className="relative border-b border-border">
      <div className="pointer-events-none absolute inset-0 grid-backdrop opacity-60" aria-hidden />
      <div className="relative mx-auto max-w-7xl px-6 py-20 md:py-28">
        <p className="eyebrow">{eyebrow}</p>
        <h1 className="mt-4 max-w-3xl text-4xl font-semibold tracking-tight text-balance md:text-5xl">
          {title}
        </h1>
        <p className="mt-5 max-w-2xl text-lg leading-relaxed text-muted-foreground">
          {description}
        </p>
      </div>
    </section>
  );
}

export function Section({
  eyebrow,
  title,
  description,
  children,
  bordered = true,
}: {
  eyebrow?: string;
  title?: string;
  description?: string;
  children: ReactNode;
  bordered?: boolean;
}) {
  return (
    <section className={bordered ? "border-b border-border" : undefined}>
      <div className="mx-auto max-w-7xl px-6 py-20 md:py-24">
        {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
        {title ? (
          <h2 className="mt-3 max-w-3xl text-3xl font-semibold tracking-tight text-balance md:text-4xl">
            {title}
          </h2>
        ) : null}
        {description ? (
          <p className="mt-4 max-w-2xl text-base leading-relaxed text-muted-foreground">
            {description}
          </p>
        ) : null}
        <div className={title || eyebrow ? "mt-12" : undefined}>{children}</div>
      </div>
    </section>
  );
}
