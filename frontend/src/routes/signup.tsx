import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ShieldCheck, ArrowRight, Shield, Globe, Cpu } from "lucide-react";

export const Route = createFileRoute("/signup")({
  component: SignupComponent,
});

function SignupComponent() {
  const navigate = useNavigate();
  const { checkAuth } = useAuth();
  
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");
    
    try {
      await api.post("/auth/signup", { 
        full_name: `${firstName} ${lastName}`,
        email, 
        password 
      });
      await checkAuth(); // Refetch user info
      navigate({ to: "/app" });
    } catch (err: any) {
      setError(err.response?.data?.error?.message || err.response?.data?.detail || "An error occurred during signup.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-background">
      {/* Left Panel - Form */}
      <div className="flex w-full flex-col justify-center px-4 sm:px-6 lg:w-1/2 lg:flex-none lg:px-20 xl:px-24">
        <div className="mx-auto w-full max-w-sm lg:w-[360px] animate-rise">
          <Link to="/" className="flex items-center gap-2 mb-10 hover:opacity-80 transition-opacity">
            <div className="flex size-8 items-center justify-center rounded-lg bg-primary">
              <ShieldCheck className="size-5 text-primary-foreground" />
            </div>
            <span className="text-xl font-bold tracking-tight text-foreground">FINSHIELD</span>
          </Link>

          <h2 className="text-3xl font-semibold tracking-tight text-foreground">
            Create an account
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Get started with secure autonomous finance infrastructure.
          </p>

          <div className="mt-8">
            <form className="space-y-5" onSubmit={handleSignUp}>
              {error && (
                <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive font-medium">
                  {error}
                </div>
              )}
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="first-name">First name</Label>
                  <Input
                    id="first-name"
                    name="first-name"
                    type="text"
                    autoComplete="given-name"
                    required
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    className="bg-surface/50 h-11"
                    disabled={isLoading}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="last-name">Last name</Label>
                  <Input
                    id="last-name"
                    name="last-name"
                    type="text"
                    autoComplete="family-name"
                    required
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    className="bg-surface/50 h-11"
                    disabled={isLoading}
                  />
                </div>
              </div>

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
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="new-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="bg-surface/50 h-11"
                  disabled={isLoading}
                />
                <p className="text-[13px] text-muted-foreground mt-1.5">
                  Must be at least 8 characters long.
                </p>
              </div>

              <Button type="submit" className="w-full h-11 text-base font-medium mt-2" disabled={isLoading}>
                {isLoading ? "Creating account..." : "Create account"}
                {!isLoading && <ArrowRight className="ml-2 size-4" />}
              </Button>
            </form>

            <div className="mt-8 text-center text-sm text-muted-foreground">
              Already have an account?{" "}
              <Link to="/login" className="font-semibold text-primary hover:underline transition-colors">
                Sign in
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Right Panel - Graphic */}
      <div className="relative hidden w-0 flex-1 lg:block bg-surface overflow-hidden border-l border-border">
        {/* Abstract background effects */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,var(--color-primary)_0%,transparent_50%)] opacity-[0.03]" />
        
        <div className="flex h-full flex-col justify-center p-12 relative z-10">
          <div className="relative mx-auto w-full max-w-lg">
            <div className="grid gap-6">
              <div className="flex gap-4 rounded-xl border border-border/60 bg-background/40 p-6 backdrop-blur-md shadow-sm">
                <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Shield className="size-5" />
                </div>
                <div>
                  <h3 className="text-base font-medium text-foreground">Deterministic Security</h3>
                  <p className="mt-1 text-sm text-muted-foreground">Enforce hard financial boundaries on AI agents before any transactions occur.</p>
                </div>
              </div>
              
              <div className="flex gap-4 rounded-xl border border-border/60 bg-background/40 p-6 backdrop-blur-md shadow-sm ml-8">
                <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Cpu className="size-5" />
                </div>
                <div>
                  <h3 className="text-base font-medium text-foreground">Intent Alignment ML</h3>
                  <p className="mt-1 text-sm text-muted-foreground">Continuously evaluate agent trajectory against the original human objective.</p>
                </div>
              </div>

              <div className="flex gap-4 rounded-xl border border-border/60 bg-background/40 p-6 backdrop-blur-md shadow-sm">
                <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Globe className="size-5" />
                </div>
                <div>
                  <h3 className="text-base font-medium text-foreground">Complete Ecosystem</h3>
                  <p className="mt-1 text-sm text-muted-foreground">A unified platform integrating agents, commerce, and payment infrastructure.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

