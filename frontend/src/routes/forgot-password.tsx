import { createFileRoute, Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ShieldCheck, ArrowRight, ArrowLeft } from "lucide-react";
import { useState } from "react";
import { api } from "@/lib/api-client";

export const Route = createFileRoute("/forgot-password")({
  component: ForgotPasswordComponent,
});

function ForgotPasswordComponent() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("loading");
    try {
      await api.post("/auth/forgot-password", { email });
      setStatus("success");
    } catch (err: any) {
      setStatus("error");
      setErrorMsg(err.response?.data?.error?.message || err.response?.data?.detail || "Something went wrong.");
    }
  };

  return (
    <div className="flex min-h-screen bg-background items-center justify-center p-4">
      <div className="w-full max-w-sm animate-rise">
        <Link to="/" className="flex items-center gap-2 mb-8 hover:opacity-80 transition-opacity">
          <div className="flex size-8 items-center justify-center rounded-lg bg-primary">
            <ShieldCheck className="size-5 text-primary-foreground" />
          </div>
          <span className="text-xl font-bold tracking-tight text-foreground">FINSHIELD</span>
        </Link>

        {status === "success" ? (
          <div className="space-y-4">
            <h2 className="text-2xl font-semibold tracking-tight">Check your email</h2>
            <p className="text-sm text-muted-foreground">
              We sent a password reset link to <span className="font-medium text-foreground">{email}</span>.
            </p>
            <Link to="/login" className="inline-flex items-center text-sm font-medium text-primary hover:underline mt-4">
              <ArrowLeft className="mr-2 size-4" /> Return to login
            </Link>
          </div>
        ) : (
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-semibold tracking-tight">Reset password</h2>
              <p className="mt-2 text-sm text-muted-foreground">
                Enter your email address and we will send you a link to reset your password.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              {status === "error" && (
                <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive font-medium">
                  {errorMsg}
                </div>
              )}
              <div className="space-y-2">
                <Label htmlFor="email">Email address</Label>
                <Input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="bg-surface/50 h-11"
                  disabled={status === "loading"}
                />
              </div>

              <Button type="submit" className="w-full h-11" disabled={status === "loading"}>
                {status === "loading" ? "Sending link..." : "Send reset link"}
                {status !== "loading" && <ArrowRight className="ml-2 size-4" />}
              </Button>
            </form>

            <div className="text-center">
              <Link to="/login" className="text-sm font-medium text-muted-foreground hover:text-foreground">
                Back to login
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}


