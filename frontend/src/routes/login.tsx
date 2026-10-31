import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ShieldCheck, ArrowRight, Zap, Activity, Lock } from "lucide-react";

export const Route = createFileRoute("/login")({
  component: LoginComponent,
});

function LoginComponent() {
  const navigate = useNavigate();
  const { checkAuth } = useAuth();
  
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isLoading) return;
    setIsLoading(true);
    setError("");
    
    try {
      await api.post("/auth/login", { email, password });
      await checkAuth(); // Refetch user info
      navigate({ to: "/app" });
    } catch (err: any) {
      setError(err.response?.data?.error?.message || err.response?.data?.detail || "An error occurred during login.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-background">
      {/* Left Panel - Form */}
      <div className="flex w-full flex-col justify-center px-4 sm:px-6 lg:w-1/2 lg:flex-none lg:px-20 xl:px-24">
        <div className="mx-auto w-full max-w-sm lg:w-[360px] animate-rise">
          <Link to="/" className="flex items-center gap-2 mb-12 hover:opacity-80 transition-opacity">
            <div className="flex size-8 items-center justify-center rounded-lg bg-primary">
              <ShieldCheck className="size-5 text-primary-foreground" />
            </div>
            <span className="text-xl font-bold tracking-tight text-foreground">FINSHIELD</span>
          </Link>

          <h2 className="text-3xl font-semibold tracking-tight text-foreground">
            Welcome back
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Sign in to manage your autonomous financial agents.
          </p>

          <div className="mt-8">
            <form className="space-y-5" onSubmit={handleSignIn}>
              {error && (
                <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive font-medium">
                  {error}
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="email">Email address</Label>
                <Input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  placeholder="name@company.com"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="bg-surface/50 h-11"
                  disabled={isLoading}
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password">Password</Label>
                  <Link
                    to="/forgot-password"
                    className="text-sm font-medium text-primary hover:text-primary/80 hover:underline transition-colors"
                  >
                    Forgot password?
                  </Link>
                </div>
                <Input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="bg-surface/50 h-11"
                  disabled={isLoading}
                />
              </div>

              <Button type="submit" className="w-full h-11 text-base font-medium mt-2" disabled={isLoading}>
                {isLoading ? "Signing in..." : "Sign in"}
                {!isLoading && <ArrowRight className="ml-2 size-4" />}
              </Button>
            </form>

            <div className="mt-8 text-center text-sm text-muted-foreground">
              Don't have an account?{" "}
              <Link to="/signup" className="font-semibold text-primary hover:underline transition-colors">
                Create an account
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Right Panel - Graphic */}
      <div className="relative hidden w-0 flex-1 lg:block bg-surface overflow-hidden border-l border-border">
        {/* Abstract background effects */}
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,var(--color-primary)_0%,transparent_60%)] opacity-5" />
        
        <div className="flex h-full flex-col justify-center p-12 relative z-10">
          {/* Central graphic */}
          <div className="relative mx-auto w-full max-w-lg">
            <div className="relative rounded-2xl border border-border/60 bg-background/40 p-8 backdrop-blur-xl shadow-glow">
              <div className="flex items-center gap-4 mb-8">
                <div className="flex size-10 items-center justify-center rounded-full bg-primary/20 text-primary">
                  <Activity className="size-5" />
                </div>
                <div>
                  <h3 className="text-sm font-medium text-foreground">Runtime Evaluation</h3>
                  <p className="text-xs text-muted-foreground">Monitoring agent trajectory...</p>
                </div>
              </div>
              
              <div className="space-y-4">
                <div className="flex items-center justify-between rounded-lg bg-surface p-4 border border-border/80 shadow-sm">
                  <div className="flex items-center gap-3">
                    <Zap className="size-4 text-warn" />
                    <span className="text-sm text-muted-foreground">Intent Alignment</span>
                  </div>
                  <span className="text-sm font-mono font-medium text-foreground">98.4%</span>
                </div>
                <div className="flex items-center justify-between rounded-lg bg-surface p-4 border border-border/80 shadow-sm">
                  <div className="flex items-center gap-3">
                    <Lock className="size-4 text-safe" />
                    <span className="text-sm text-muted-foreground">Policy Enforcement</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <div className="size-1.5 rounded-full bg-safe animate-pulse-dot" />
                    <span className="text-sm font-mono font-medium text-safe">PASS</span>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="mt-12 text-center text-balance">
              <blockquote className="space-y-2">
                <p className="text-lg font-medium text-foreground/90">
                  "FINSHIELD connects the user's original intent with the agent's trajectory to secure financial transactions before they happen."
                </p>
              </blockquote>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

