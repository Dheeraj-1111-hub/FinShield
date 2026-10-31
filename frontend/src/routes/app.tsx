import { createFileRoute, Outlet, Link, useRouterState, useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { getOverview } from "@/api/overview";
import {
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import {
  LayoutDashboard, Bot, Terminal, CreditCard, ShoppingCart,
  ShieldAlert, ShieldCheck, FileSearch, FlaskConical, LineChart,
  ScrollText, Code, Settings, ChevronRight, Bell, Target, LogOut
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
} from "@/components/ui/command";
import { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth-context";
import { formatCurrency } from "@/lib/utils";

export const Route = createFileRoute("/app")({
  component: AppLayout,
});

const NAV_GROUPS = [
  {
    label: "HOME",
    items: [{ name: "Overview", icon: LayoutDashboard, path: "/app" }],
  },
  {
    label: "AUTONOMY",
    items: [
      { name: "Agents",        icon: Bot,      path: "/app/agents"  },
      { name: "Agent Console", icon: Terminal,  path: "/app/console" },
    ],
  },
  {
    label: "FINANCIAL ACTIVITY",
    items: [
      { name: "Commerce Sandbox", icon: ShoppingCart, path: "/app/commerce" },
      { name: "Orders",   icon: ShoppingCart, path: "/app/orders"   },
      { name: "Payments", icon: CreditCard,   path: "/app/payments" },
    ],
  },
  {
    label: "CONTROL",
    items: [
      { name: "Action Gate",     icon: ShieldCheck, path: "/app/approvals"       },
      { name: "Policies",        icon: ShieldCheck, path: "/app/policies"        },
      { name: "Risk Center",     icon: ShieldAlert, path: "/app/risk"            },
    ],
  },
  {
    label: "GOVERNANCE",
    items: [
      { name: "Intents",         icon: Target,      path: "/app/intents"         },
      { name: "Authorities",     icon: ShieldCheck, path: "/app/authorities"     },
      { name: "Investigations",  icon: FileSearch,  path: "/app/investigations"  },
    ],
  },
  {
    label: "INTEGRATIONS",
    items: [
      { name: "Developers",  icon: Code,       path: "/app/developers"  },
    ],
  },
  {
    label: "SYSTEM",
    items: [
      { name: "Audit Log",   icon: ScrollText, path: "/app/audit"       },
      { name: "Settings",    icon: Settings,   path: "/app/settings"    },
      { name: "Security Lab",   icon: FlaskConical, path: "/app/lab"        },
      { name: "Benchmark Lab",  icon: LineChart,    path: "/app/benchmarks" },
    ],
  },
];

// Colour accent per group for the active indicator dot
const GROUP_ACCENTS: Record<string, string> = {
  "HOME":      "bg-primary",
  "AUTONOMY":  "bg-info",
  "FINANCIAL ACTIVITY": "bg-safe",
  "CONTROL":     "bg-warn",
  "GOVERNANCE":  "bg-primary",
  "INTEGRATIONS": "bg-muted-foreground",
  "SYSTEM":    "bg-muted-foreground",
};

function AppSidebar() {
  const { location } = useRouterState();
  const currentPath = location.pathname;
  const { user, workspace, logout } = useAuth();
  const navigate = useNavigate({ from: "/app" });
  
  const { data: overview } = useQuery({
    queryKey: ["overview", workspace?.id],
    queryFn: () => getOverview(workspace?.id || ""),
    enabled: !!workspace?.id,
  });

  const handleLogout = async () => {
    await logout();
    navigate({ to: "/login" });
  };

  const isActive = (path: string) =>
    path === "/app" ? currentPath === "/app" : currentPath.startsWith(path);

  return (
    <aside className="fixed inset-y-0 left-0 z-20 flex w-[220px] flex-col border-r border-border bg-background">

      {/* ── Logo ─────────────────────────────────────────────────────────────── */}
      <div className="flex h-16 shrink-0 items-center gap-3 border-b border-border px-5">
        <Link to="/app" className="flex items-center gap-2.5 group">
          <div className="relative flex size-8 shrink-0 items-center justify-center rounded-xl bg-primary shadow-lg shadow-primary/25 group-hover:shadow-primary/40 transition-shadow">
            <ShieldCheck className="size-4 text-primary-foreground" />
            <div className="absolute inset-0 rounded-xl ring-2 ring-primary/20 group-hover:ring-primary/40 transition-all" />
          </div>
          <span className="text-[15px] font-bold tracking-tight text-foreground">FINSHIELD</span>
        </Link>
      </div>

      {/* ── Nav ──────────────────────────────────────────────────────────────── */}
      <nav className="flex-1 overflow-y-auto overflow-x-hidden py-3 px-3 space-y-0.5 scrollbar-none">
        {NAV_GROUPS.map((group, gi) => (
          <div key={group.label} className={gi > 0 ? "mt-4" : ""}>

            {/* Group label */}
            <div className="mb-1 px-2 flex items-center gap-1.5">
              <span className={`size-1.5 rounded-full ${GROUP_ACCENTS[group.label] ?? "bg-muted-foreground"}`} />
              <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-muted-foreground/60">
                {group.label}
              </span>
            </div>

            {/* Items */}
            {group.items.map(item => {
              const active = isActive(item.path);
              return (
                <Link
                  key={item.name}
                  to={item.path}
                  className={`
                    flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition-all duration-150 group relative
                    ${active
                      ? "bg-primary/12 text-primary"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"}
                  `}
                >
                  {/* Active left bar */}
                  {active && (
                    <span className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-0.5 rounded-full bg-primary" />
                  )}

                  {/* Icon */}
                  <div className={`flex size-7 shrink-0 items-center justify-center rounded-lg transition-colors ${
                    active
                      ? "bg-primary/20 text-primary"
                      : "text-muted-foreground group-hover:text-foreground"
                  }`}>
                    <item.icon className="size-[15px]" />
                  </div>

                  <span className="flex-1 truncate">{item.name}</span>

                  {/* Active chevron */}
                  {active && (
                    <ChevronRight className="size-3.5 text-primary/60 shrink-0" />
                  )}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* ── Env badge ────────────────────────────────────────────────────────── */}
      <div className="mx-3 mb-3 flex items-center gap-2 rounded-xl border border-border bg-muted/50 px-3 py-2">
        <span className="size-1.5 rounded-full bg-safe animate-pulse" />
        <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Sandbox</span>
        <span className="ml-auto font-mono text-[11px] font-semibold text-foreground">
          {formatCurrency(overview?.financial.payment_volume || 0, overview?.financial.currency || workspace?.currency || "INR")}
        </span>
      </div>

      {/* ── Footer / user ────────────────────────────────────────────────────── */}
      <div className="border-t border-border p-3">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <div className="flex items-center gap-3 rounded-xl px-3 py-2.5 hover:bg-muted transition-colors group cursor-pointer">
              <div className="flex size-8 shrink-0 items-center justify-center rounded-xl bg-primary/20 text-primary text-xs font-bold">
                {user?.full_name ? user.full_name.substring(0, 2).toUpperCase() : 'US'}
              </div>
              <div className="flex min-w-0 flex-col">
                <span className="text-sm font-semibold text-foreground truncate">{user?.full_name || 'User Account'}</span>
                <span className="text-[11px] text-muted-foreground truncate">{user?.email || 'user@finshield.dev'}</span>
              </div>
              <Settings className="size-3.5 text-muted-foreground shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-56 mb-2">
            <Link to="/app/settings">
              <DropdownMenuItem className="cursor-pointer">
                <Settings className="mr-2 size-4" />
                <span>Settings</span>
              </DropdownMenuItem>
            </Link>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={(e) => { e.preventDefault(); handleLogout(); }} className="text-danger focus:text-danger cursor-pointer">
              <LogOut className="mr-2 size-4" />
              <span>Sign out</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </aside>
  );
}

function AppLayout() {
  const { isAuthenticated, isLoading, logout, user, workspace } = useAuth();
  const navigate = useNavigate({ from: "/app" });
  
  const [searchOpen, setSearchOpen] = useState(false);

  const { data: overview } = useQuery({
    queryKey: ["overview", workspace?.id],
    queryFn: () => getOverview(workspace?.id || ""),
    enabled: !!workspace?.id,
  });

  const handleLogout = async () => {
    await logout();
    navigate({ to: "/login" });
  };
  
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      navigate({ to: "/login" });
    }
  }, [isLoading, isAuthenticated, navigate]);
  
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setSearchOpen((open) => !open);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);
  
  if (isLoading || !isAuthenticated) {
    return <div className="flex min-h-screen items-center justify-center bg-background"><div className="size-8 animate-spin rounded-full border-4 border-primary border-t-transparent" /></div>;
  }

  // Calculate notifications
  const needsAttention = (overview?.recent_approvals?.length || 0) + (overview?.recent_critical_risks?.length || 0);

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full bg-background text-foreground">
        <AppSidebar />

        {/* ── Main content ──────────────────────────────────────────────────── */}
        <div className="flex flex-1 flex-col min-w-0 pl-[220px]">

          {/* Top bar */}
          <header className="sticky top-0 z-10 flex h-16 shrink-0 items-center gap-4 border-b border-border bg-background/80 px-6 backdrop-blur-md">
            {/* Mobile sidebar trigger (hidden on desktop) */}
            <SidebarTrigger className="lg:hidden -ml-1" />

            {/* Breadcrumb-style title */}
            <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
              <span className="text-primary font-mono">⌗</span>
              <span>Command Center</span>
            </div>

            <div className="ml-auto flex items-center gap-3">
              {/* Search */}
              <button 
                onClick={() => setSearchOpen(true)}
                className="flex items-center gap-2 rounded-xl border border-border bg-surface px-3 py-1.5 text-xs text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
              >
                <svg className="size-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
                </svg>
                <span>Search...</span>
                <kbd className="ml-1 rounded bg-background px-1.5 font-mono text-[10px] font-medium text-muted-foreground border border-border">⌘K</kbd>
              </button>

              {/* Notifications */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button className="relative flex size-9 items-center justify-center rounded-xl border border-border bg-surface text-muted-foreground hover:bg-muted hover:text-foreground transition-colors outline-none cursor-pointer">
                    <Bell className="size-4" />
                    {needsAttention > 0 && (
                      <span className="absolute top-1.5 right-1.5 size-1.5 rounded-full bg-danger animate-pulse" />
                    )}
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-80 p-0">
                  <div className="p-3 border-b border-border/50 bg-muted/30">
                    <h3 className="font-semibold text-sm">Notifications</h3>
                  </div>
                  <div className="max-h-[300px] overflow-y-auto">
                    {needsAttention === 0 ? (
                      <div className="p-6 text-center text-sm text-muted-foreground">
                        No new notifications.
                      </div>
                    ) : (
                      <div className="flex flex-col">
                        {overview?.recent_critical_risks?.map(risk => (
                          <DropdownMenuItem key={risk.id} asChild className="cursor-pointer p-3 focus:bg-muted items-start gap-3 rounded-none">
                            <Link to="/app/risk">
                              <div className="size-8 rounded-full bg-danger/10 text-danger flex items-center justify-center shrink-0 mt-0.5">
                                <ShieldAlert className="size-4" />
                              </div>
                              <div className="flex flex-col gap-1">
                                <span className="text-sm font-medium leading-none text-foreground">Critical Risk Blocked</span>
                                <span className="text-xs text-muted-foreground line-clamp-2">{risk.agent_name} attempted {risk.action_type === 'Unknown' ? 'an action' : risk.action_type} which was blocked due to high risk score ({risk.score}).</span>
                              </div>
                            </Link>
                          </DropdownMenuItem>
                        ))}
                        {overview?.recent_approvals?.map(appr => (
                          <DropdownMenuItem key={appr.id} asChild className="cursor-pointer p-3 focus:bg-muted items-start gap-3 rounded-none border-t border-border/50">
                            <Link to="/app/approvals">
                              <div className="size-8 rounded-full bg-warn/10 text-warn flex items-center justify-center shrink-0 mt-0.5">
                                <ShieldCheck className="size-4" />
                              </div>
                              <div className="flex flex-col gap-1">
                                <span className="text-sm font-medium leading-none text-foreground">Approval Required</span>
                                <span className="text-xs text-muted-foreground line-clamp-2">{appr.agent_name} wants to perform {appr.action_type === 'Unknown' ? 'an action' : appr.action_type}.</span>
                              </div>
                            </Link>
                          </DropdownMenuItem>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="p-2 border-t border-border/50 bg-muted/30">
                    <DropdownMenuItem asChild className="cursor-pointer justify-center text-center font-medium text-primary w-full">
                      <Link to="/app/approvals">
                        View all in Action Gate
                      </Link>
                    </DropdownMenuItem>
                  </div>
                </DropdownMenuContent>
              </DropdownMenu>

              {/* Wallet */}
              <div className="group relative flex items-center gap-2 rounded-xl border border-border bg-surface px-3 py-1.5 cursor-pointer hover:bg-muted transition-colors">
                <span className="size-1.5 rounded-full bg-safe" />
                <span className="text-xs text-muted-foreground font-semibold">SANDBOX</span>
                <span className="font-mono text-xs font-semibold text-foreground">
                  {formatCurrency(overview?.financial.payment_volume || 0, overview?.financial.currency || workspace?.currency || "INR")}
                </span>

                {/* Dropdown */}
                <div className="absolute top-full right-0 mt-2 w-56 bg-popover border border-border rounded-xl shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all p-4 z-50 space-y-2">
                  <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-3">Sandbox Volume</div>
                  <div className="flex justify-between text-xs text-muted-foreground"><span>Total Payments</span><span className="font-mono">{overview?.financial.payment_count || 0}</span></div>
                  {overview?.financial.balances_by_currency && Object.keys(overview.financial.balances_by_currency).length > 1 ? (
                    <div className="space-y-1.5 border-t border-border pt-2 mt-2">
                      <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Balances by Currency</div>
                      {Object.entries(overview.financial.balances_by_currency).map(([curr, amt]) => (
                        <div key={curr} className="flex justify-between text-xs">
                          <span className="text-muted-foreground">{curr}</span>
                          <span className="font-mono font-semibold">{formatCurrency(amt, curr)}</span>
                        </div>
                      ))}
                    </div>
                  ) : null}
                  <div className="flex justify-between text-xs border-t border-border pt-2 mt-2">
                    <span className="font-semibold text-foreground">Volume ({overview?.financial.currency || workspace?.currency || "INR"})</span>
                    <span className="font-mono font-semibold">
                      {formatCurrency(overview?.financial.payment_volume || 0, overview?.financial.currency || workspace?.currency || "INR")}
                    </span>
                  </div>
                </div>
              </div>

              {/* Avatar Dropdown */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <div className="flex size-9 items-center justify-center rounded-xl bg-primary/20 text-primary font-bold text-xs border border-primary/20 hover:bg-primary/30 transition-colors cursor-pointer">
                    {user?.full_name ? user.full_name.substring(0, 2).toUpperCase() : 'US'}
                  </div>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <DropdownMenuLabel className="font-normal">
                    <div className="flex flex-col space-y-1">
                      <p className="text-sm font-medium leading-none">{user?.full_name}</p>
                      <p className="text-xs leading-none text-muted-foreground">
                        {user?.email}
                      </p>
                    </div>
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <Link to="/app/settings">
                    <DropdownMenuItem className="cursor-pointer">
                      <Settings className="mr-2 size-4" />
                      <span>Settings</span>
                    </DropdownMenuItem>
                  </Link>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onSelect={(e) => { e.preventDefault(); handleLogout(); }} className="text-danger focus:text-danger cursor-pointer">
                    <LogOut className="mr-2 size-4" />
                    <span>Sign out</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </header>

          <main className="flex-1 p-6 sm:p-8 overflow-y-auto">
            <Outlet />
          </main>
        </div>
      </div>

      <CommandDialog open={searchOpen} onOpenChange={setSearchOpen}>
        <CommandInput placeholder="Search FINSHIELD..." />
        <CommandList>
          <CommandEmpty>No results found.</CommandEmpty>
          {NAV_GROUPS.map((group) => (
            <CommandGroup key={group.label} heading={group.label}>
              {group.items.map((item) => (
                <CommandItem
                  key={item.path}
                  onSelect={() => {
                    navigate({ to: item.path as any });
                    setSearchOpen(false);
                  }}
                >
                  <item.icon className="mr-2 size-4" />
                  <span>{item.name}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          ))}
        </CommandList>
      </CommandDialog>
    </SidebarProvider>
  );
}
