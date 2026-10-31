import { useState } from "react";
import { Monitor, Smartphone, ChevronDown } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { SESSIONS, SECURITY_EVENTS } from "@/data/mock-settings";
import { useNavigate } from "@tanstack/react-router";

function Toggle({ checked, onChange }: { checked: boolean; onChange: () => void }) {
  return (
    <button
      onClick={onChange}
      className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ${checked ? "bg-primary" : "bg-muted-foreground/30"}`}
    >
      <span className={`pointer-events-none inline-block size-4 rounded-full bg-white shadow transition-transform duration-200 ${checked ? "translate-x-4" : "translate-x-0"}`} />
    </button>
  );
}

const SESSION_TIMEOUTS = ["1 hour", "4 hours", "12 hours", "24 hours", "7 days"];

export function SecurityPanel() {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState(SESSIONS);
  const [twoFaRequired, setTwoFaRequired] = useState<"account" | "all">("all");
  const [sessionTimeout, setSessionTimeout] = useState("12 hours");
  const [showTimeout, setShowTimeout] = useState(false);
  const [loginNotifs, setLoginNotifs] = useState(true);
  const [ipRestrict, setIpRestrict] = useState(false);

  const revokeSession = (id: string) => setSessions(s => s.filter(sess => sess.id !== id));

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-foreground mb-0.5">Security</h2>
        <p className="text-sm text-muted-foreground">Protect your FINSHIELD account and workspace.</p>
      </div>

      {/* Account Security */}
      <Card className="border-border bg-surface overflow-hidden">
        <div className="px-6 py-4 border-b border-border text-xs font-semibold text-muted-foreground uppercase tracking-wider">Account Security</div>
        <div className="divide-y divide-border">
          {/* Password */}
          <div className="px-6 py-4 flex items-center justify-between gap-4">
            <div>
              <div className="font-medium text-foreground">Password</div>
              <div className="text-xs text-muted-foreground mt-0.5">Last changed 14 days ago</div>
            </div>
            <Button size="sm" variant="outline" className="border-border bg-background shrink-0">Change password</Button>
          </div>
          {/* 2FA */}
          <div className="px-6 py-4 flex items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-medium text-foreground">Two-factor authentication</span>
                <span className="text-xs px-2 py-0.5 rounded-md bg-safe/10 border border-safe/20 text-safe font-bold">ENABLED</span>
              </div>
              <div className="text-xs text-muted-foreground mt-0.5">Authenticator app configured</div>
            </div>
            <Button size="sm" variant="outline" className="border-border bg-background shrink-0">Manage</Button>
          </div>
          {/* Sessions */}
          <div className="px-6 py-4 flex items-center justify-between gap-4">
            <div>
              <div className="font-medium text-foreground">Active sessions</div>
              <div className="text-xs text-muted-foreground mt-0.5">{sessions.length} active sessions</div>
            </div>
          </div>
        </div>
      </Card>

      {/* Sessions list */}
      <Card className="border-border bg-surface overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Active Sessions</div>
          <button className="text-xs text-danger hover:underline font-medium">Sign out all other sessions</button>
        </div>
        <div className="divide-y divide-border">
          {sessions.map(sess => (
            <div key={sess.id} className="px-6 py-4 flex items-center gap-4">
              <div className="size-9 rounded-xl bg-muted border border-border flex items-center justify-center shrink-0">
                <Monitor className="size-4 text-muted-foreground" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-foreground text-sm">{sess.browser} · {sess.os}</span>
                  {sess.isCurrent && (
                    <span className="text-xs px-1.5 py-0.5 rounded bg-safe/10 border border-safe/20 text-safe font-bold">Current</span>
                  )}
                </div>
                <div className="text-xs text-muted-foreground mt-0.5">{sess.location} · {sess.lastActive}</div>
              </div>
              {!sess.isCurrent && (
                <Button size="sm" variant="outline" className="border-danger/30 bg-danger/5 text-danger hover:bg-danger/10 shrink-0 text-xs"
                  onClick={() => revokeSession(sess.id)}>Revoke</Button>
              )}
            </div>
          ))}
        </div>
      </Card>

      {/* Login Protection */}
      <Card className="border-border bg-surface p-6 space-y-5">
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Login Protection</div>

        <div>
          <div className="text-sm font-medium text-foreground mb-2">Require 2FA for</div>
          <div className="space-y-2">
            {(["account", "all"] as const).map(opt => (
              <label key={opt} className="flex items-center gap-3 cursor-pointer">
                <div className={`size-4 rounded-full border-2 flex items-center justify-center shrink-0 ${twoFaRequired === opt ? "border-primary" : "border-muted-foreground/40"}`}>
                  {twoFaRequired === opt && <div className="size-2 rounded-full bg-primary" />}
                </div>
                <input type="radio" className="sr-only" checked={twoFaRequired === opt} onChange={() => setTwoFaRequired(opt)} />
                <span className="text-sm text-foreground">{opt === "account" ? "Account only" : "All workspace members"}</span>
              </label>
            ))}
          </div>
        </div>

        <div>
          <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-2">Session timeout</label>
          <div className="relative">
            <button onClick={() => setShowTimeout(o => !o)}
              className="flex items-center justify-between w-full max-w-xs bg-background border border-border rounded-lg px-3 py-2.5 text-sm text-foreground hover:border-border-strong transition-colors">
              {sessionTimeout} <ChevronDown className="size-4 text-muted-foreground" />
            </button>
            {showTimeout && (
              <div className="absolute z-10 top-full mt-1 w-full max-w-xs bg-popover border border-border rounded-lg shadow-xl overflow-hidden">
                {SESSION_TIMEOUTS.map(t => (
                  <button key={t} onClick={() => { setSessionTimeout(t); setShowTimeout(false); }}
                    className={`w-full text-left px-4 py-2.5 text-sm hover:bg-muted ${t === sessionTimeout ? "text-primary font-medium" : "text-foreground"}`}>
                    {t}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium text-foreground">Login notifications</div>
            <div className="text-xs text-muted-foreground mt-0.5">Notify when a new device signs in.</div>
          </div>
          <Toggle checked={loginNotifs} onChange={() => setLoginNotifs(v => !v)} />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium text-foreground">IP restrictions</div>
            <div className="text-xs text-muted-foreground mt-0.5">Restrict access to allowed IP ranges.</div>
          </div>
          <Toggle checked={ipRestrict} onChange={() => setIpRestrict(v => !v)} />
        </div>
      </Card>

      {/* Recent Security Activity */}
      <Card className="border-border bg-surface overflow-hidden">
        <div className="px-6 py-4 border-b border-border text-xs font-semibold text-muted-foreground uppercase tracking-wider">
          Recent Security Activity
        </div>
        <div className="divide-y divide-border">
          {SECURITY_EVENTS.map((ev, i) => (
            <div key={i} className="px-6 py-3.5 flex items-center gap-4">
              <span className="text-xs font-mono text-muted-foreground w-10 shrink-0">{ev.time}</span>
              <div className="flex-1">
                <span className="text-sm font-medium text-foreground">{ev.event}</span>
                <span className="text-xs text-muted-foreground ml-2">{ev.detail}</span>
              </div>
            </div>
          ))}
        </div>
        <div className="px-6 py-3 border-t border-border">
          <button
            onClick={() => navigate({ to: "/app/audit" })}
            className="text-xs text-primary hover:underline font-medium"
          >
            View security activity →
          </button>
        </div>
      </Card>
    </div>
  );
}
