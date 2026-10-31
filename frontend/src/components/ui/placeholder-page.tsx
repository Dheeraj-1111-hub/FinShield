import { LucideIcon } from "lucide-react";

interface PlaceholderPageProps {
  title: string;
  description: string;
  icon: LucideIcon;
}

export function PlaceholderPage({ title, description, icon: Icon }: PlaceholderPageProps) {
  return (
    <div className="relative flex min-h-[calc(100vh-8rem)] w-full flex-col items-center justify-center overflow-hidden rounded-2xl border border-border bg-background shadow-sm">
      {/* Abstract Grid Background */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]" />
      
      {/* Glowing radial gradient */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 size-[400px] bg-primary/20 opacity-40 blur-[100px] rounded-full pointer-events-none" />

      <div className="relative z-10 flex flex-col items-center text-center animate-rise p-6">
        <div className="mb-6 flex size-20 items-center justify-center rounded-2xl border border-border/50 bg-background/50 shadow-glow backdrop-blur-xl">
          <Icon className="size-10 text-primary" />
        </div>
        <h2 className="text-3xl font-bold tracking-tight text-foreground">
          {title}
        </h2>
        <p className="mt-4 max-w-md text-base text-muted-foreground">
          {description}
        </p>
        
        <div className="mt-10 flex items-center gap-2 rounded-full border border-primary/30 bg-primary/5 px-4 py-1.5 text-sm font-medium text-primary shadow-sm backdrop-blur-md">
          <span className="relative flex size-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75"></span>
            <span className="relative inline-flex size-2 rounded-full bg-primary"></span>
          </span>
          Engineering in progress
        </div>
      </div>
    </div>
  );
}
