import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ShieldCheck, ArrowRight } from "lucide-react";
import { useState, useEffect } from "react";
import { api } from "@/lib/api-client";

export const Route = createFileRoute("/reset-password")({
  component: ResetPasswordComponent,
});

function ResetPasswordComponent() {
  const navigate = useNavigate();
  const [token, setToken] = useState<string>("");
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
    setToken(new URLSearchParams(window.location.search).get("token") || "");
  }, []);

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      setStatus("error");
      setErrorMsg("Passwords do not match.");
      return;
    }
    setStatus("loading");
    try {
      await api.post("/auth/reset-password", { token, password });
      setStatus("success");
    } catch (err: any) {
      setStatus("error");
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        setErrorMsg(detail[0].msg);
      } else {
        setErrorMsg(err.response?.data?.error?.message || detail || "Invalid or expired token.");
      }
    }
  };

  if (!isClient) {
    return null; // Avoid SSR hydration mismatch
  }

  if (!token && status === "idle") {
    return (
      <div className="flex min-h-screen bg-background items-center justify-center p-4">
        <div className="text-center space-y-4">
          <h2 className="text-2xl font-semibold text-destructive">Invalid reset link</h2>
          <p className="text-muted-foreground">The password reset link is invalid or missing.</p>
          <Link to="/forgot-password" className="text-primary hover:underline">Request a new one</Link>
        </div>
      </div>
    );
  }

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
          <div className="space-y-4 text-center">
            <h2 className="text-2xl font-semibold tracking-tight">Password reset!</h2>
            <p className="text-sm text-muted-foreground">
              Your password has been successfully reset.
            </p>
            <Button onClick={() => navigate({ to: "/login" })} className="w-full mt-4">
              Sign in
            </Button>
          </div>
        ) : (
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-semibold tracking-tight">Set new password</h2>
              <p className="mt-2 text-sm text-muted-foreground">
                Please choose a strong password.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              {status === "error" && (
                <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive font-medium">
                  {errorMsg}
                </div>
              )}
              <div className="space-y-2">
                <Label htmlFor="password">New Password</Label>
                <Input
                  id="password"
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="bg-surface/50 h-11"
                  disabled={status === "loading"}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirmPassword">Confirm Password</Label>
                <Input
                  id="confirmPassword"
                  type="password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="bg-surface/50 h-11"
                  disabled={status === "loading"}
                />
              </div>

              <Button type="submit" className="w-full h-11" disabled={status === "loading"}>
                {status === "loading" ? "Resetting..." : "Reset password"}
                {status !== "loading" && <ArrowRight className="ml-2 size-4" />}
              </Button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}


