import { useState } from "react";
import { UserPlus, Check, ChevronDown } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { TEAM_MEMBERS, TeamMember } from "@/data/mock-settings";
import { toast } from "sonner";

const ROLES = ["Owner", "Security Admin", "Developer", "Auditor", "Viewer"];
const PERMISSIONS_LABELS: Record<string, string> = {
  view_agents:           "View agents",
  view_transactions:     "View transactions",
  view_investigations:   "View investigations",
  manage_policies:       "Manage policies",
  view_audit:            "View audit log",
  manage_billing:        "Manage billing",
  manage_workspace:      "Manage workspace",
};

const statusStyle = (s: TeamMember["status"]) => {
  switch (s) {
    case "ACTIVE":    return "text-safe bg-safe/10 border-safe/20";
    case "INVITED":   return "text-warn bg-warn/10 border-warn/20";
    case "SUSPENDED": return "text-danger bg-danger/10 border-danger/20";
  }
};

export function TeamPanel() {
  const [members, setMembers] = useState(TEAM_MEMBERS);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showRoleDropdown, setShowRoleDropdown] = useState(false);
  const [isInviting, setIsInviting] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");

  const selected = members.find(m => m.id === selectedId) ?? null;

  const updateRole = (id: string, role: string) =>
    setMembers(ms => ms.map(m => m.id === id ? { ...m, role } : m));

  const togglePerm = (id: string, perm: string) =>
    setMembers(ms => ms.map(m => m.id === id
      ? { ...m, permissions: { ...m.permissions, [perm]: !m.permissions[perm] } }
      : m
    ));

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-foreground mb-0.5">Team & Access</h2>
        <p className="text-sm text-muted-foreground">Manage workspace members and their permissions.</p>
      </div>

      {/* Members table */}
      <Card className="border-border bg-surface overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Workspace Members</div>
          <Button size="sm" onClick={() => setIsInviting(true)} className="bg-primary hover:bg-primary/90 text-primary-foreground gap-1.5">
            <UserPlus className="size-3.5" /> Invite member
          </Button>
        </div>

        {isInviting && (
          <div className="px-6 py-4 border-b border-border bg-muted/20">
            <form onSubmit={(e) => {
              e.preventDefault();
              setMembers([...members, {
                id: `usr_${Date.now()}`,
                name: inviteEmail.split('@')[0],
                email: inviteEmail,
                role: "Viewer",
                joined: new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }),
                status: "INVITED",
                permissions: {}
              }]);
              setIsInviting(false);
              setInviteEmail("");
              toast.success("Invitation sent");
            }} className="flex gap-3 items-center">
              <input 
                type="email" 
                required 
                placeholder="Email address..." 
                value={inviteEmail}
                onChange={e => setInviteEmail(e.target.value)}
                className="flex-1 bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40" 
              />
              <Button type="submit" size="sm" className="bg-primary text-primary-foreground">Send Invite</Button>
              <Button type="button" variant="ghost" size="sm" onClick={() => setIsInviting(false)}>Cancel</Button>
            </form>
          </div>
        )}

        {/* Header row */}
        <div className="grid grid-cols-[1fr_auto_auto_auto] gap-4 px-6 py-2 border-b border-border text-xs font-semibold text-muted-foreground uppercase tracking-wider">
          <span>Name</span>
          <span className="hidden sm:block w-28">Role</span>
          <span className="hidden md:block w-20">Joined</span>
          <span className="w-16 text-right">Status</span>
        </div>

        <div className="divide-y divide-border">
          {members.map(m => (
            <div
              key={m.id}
              className={`grid grid-cols-[1fr_auto_auto_auto] gap-4 items-center px-6 py-4 cursor-pointer transition-colors ${selectedId === m.id ? "bg-primary/5" : "hover:bg-muted/40"}`}
              onClick={() => setSelectedId(selectedId === m.id ? null : m.id)}
            >
              <div>
                <div className="font-medium text-foreground text-sm">{m.name}</div>
                <div className="text-xs text-muted-foreground">{m.email}</div>
              </div>
              <div className="hidden sm:block w-28">
                <span className="text-xs font-medium text-foreground">{m.role}</span>
              </div>
              <div className="hidden md:block w-20 text-xs text-muted-foreground">{m.joined.split(" ")[0]} {m.joined.split(" ")[1]}</div>
              <div className="w-16 flex justify-end">
                <span className={`text-xs px-1.5 py-0.5 rounded-md border font-bold uppercase ${statusStyle(m.status)}`}>
                  {m.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Member editor */}
      {selected && (
        <Card className="border-border bg-surface p-6 space-y-5 animate-in slide-in-from-top-2 duration-200">
          <div className="flex items-center justify-between">
            <div>
              <div className="font-bold text-foreground">{selected.name}</div>
              <div className="text-xs text-muted-foreground">{selected.email}</div>
            </div>
            <button onClick={() => setSelectedId(null)} className="text-xs text-muted-foreground hover:text-foreground">✕ Close</button>
          </div>

          {/* Role selector */}
          <div>
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-2">Role</label>
            <div className="relative max-w-xs">
              <button
                onClick={() => setShowRoleDropdown(o => !o)}
                disabled={selected.role === "Owner"}
                className="flex items-center justify-between w-full bg-background border border-border rounded-lg px-3 py-2.5 text-sm text-foreground hover:border-border-strong transition-colors disabled:opacity-50"
              >
                {selected.role} <ChevronDown className="size-4 text-muted-foreground" />
              </button>
              {showRoleDropdown && (
                <div className="absolute z-10 top-full mt-1 w-full bg-popover border border-border rounded-lg shadow-xl overflow-hidden">
                  {ROLES.filter(r => r !== "Owner").map(r => (
                    <button key={r} onClick={() => { updateRole(selected.id, r); setShowRoleDropdown(false); }}
                      className={`w-full text-left px-4 py-2.5 text-sm hover:bg-muted flex items-center justify-between ${r === selected.role ? "text-primary font-medium" : "text-foreground"}`}>
                      {r} {r === selected.role && <Check className="size-4" />}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Permissions */}
          <div>
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Permissions</div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {Object.keys(PERMISSIONS_LABELS).map(perm => {
                const active = !!selected.permissions[perm];
                const isOwner = selected.role === "Owner";
                return (
                  <label key={perm} className={`flex items-center gap-3 p-3 rounded-lg border border-border bg-muted ${isOwner ? "opacity-60" : "cursor-pointer hover:border-border-strong"} transition-colors`}>
                    <div className={`size-4 rounded border-2 flex items-center justify-center shrink-0 ${active ? "bg-primary border-primary" : "border-muted-foreground/30"}`}>
                      {active && <Check className="size-3 text-primary-foreground" strokeWidth={3} />}
                    </div>
                    <input type="checkbox" className="sr-only" checked={active} onChange={() => !isOwner && togglePerm(selected.id, perm)} />
                    <span className="text-sm text-foreground">{PERMISSIONS_LABELS[perm]}</span>
                  </label>
                );
              })}
            </div>
          </div>

          <div className="flex gap-3">
            <Button onClick={() => { setSelectedId(null); toast.success("Member updated successfully"); }} className="bg-primary hover:bg-primary/90 text-primary-foreground">Save changes</Button>
            {selected.role !== "Owner" && (
              <Button onClick={() => {
                setMembers(ms => ms.filter(m => m.id !== selected.id));
                setSelectedId(null);
                toast.success("Member removed");
              }} variant="outline" className="border-danger/30 bg-danger/5 text-danger hover:bg-danger/10">Remove member</Button>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}
