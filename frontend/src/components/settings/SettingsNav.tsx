import {
  User, Building2, Shield, Users, Bell, Bot, Database, CreditCard, Key, AlertTriangle,
} from "lucide-react";

export type SettingsSection =
  | "general" | "workspace" | "security" | "team"
  | "notifications" | "ai" | "data" | "billing" | "api" | "danger";

interface NavItem {
  id: SettingsSection;
  label: string;
  icon: React.ElementType;
  danger?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { id: "general",       label: "General",         icon: User },
  { id: "workspace",     label: "Workspace",        icon: Building2 },
  { id: "security",      label: "Security",         icon: Shield },
  { id: "team",          label: "Team & Access",    icon: Users },
  { id: "notifications", label: "Notifications",    icon: Bell },
  { id: "ai",            label: "AI & Intelligence",icon: Bot },
  { id: "data",          label: "Data & Privacy",   icon: Database },
  { id: "billing",       label: "Billing",          icon: CreditCard },
  { id: "api",           label: "API & Access",     icon: Key },
  { id: "danger",        label: "Danger Zone",      icon: AlertTriangle, danger: true },
];

interface Props {
  active: SettingsSection;
  onChange: (s: SettingsSection) => void;
}

export function SettingsNav({ active, onChange }: Props) {
  return (
    <nav className="flex flex-col gap-0.5">
      <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider px-3 py-2 mb-1">
        Settings
      </div>
      {NAV_ITEMS.map(item => {
        const Icon = item.icon;
        const isActive = active === item.id;
        return (
          <button
            key={item.id}
            onClick={() => onChange(item.id)}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium w-full text-left transition-colors ${
              item.danger
                ? isActive
                  ? "bg-danger/15 text-danger"
                  : "text-danger/70 hover:bg-danger/8 hover:text-danger"
                : isActive
                  ? "bg-primary/15 text-primary"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
            }`}
          >
            <Icon className="size-4 shrink-0" />
            {item.label}
          </button>
        );
      })}
    </nav>
  );
}
