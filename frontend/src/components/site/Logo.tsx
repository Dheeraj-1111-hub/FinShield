import { ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";

export function Logo({ className }: { className?: string }) {
  return (
    <span className={cn("flex items-center gap-2", className)}>
      <ShieldCheck className="size-5 text-primary" aria-hidden />
      <span className="text-sm font-semibold tracking-[0.18em] text-foreground">FINSHIELD</span>
    </span>
  );
}
