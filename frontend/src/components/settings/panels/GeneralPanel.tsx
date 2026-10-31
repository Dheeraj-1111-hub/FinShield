import { useState } from "react";
import { Check, ChevronDown } from "lucide-react";
import { Card } from "@/components/ui/card";

const LANGUAGES = ["English (US)", "English (UK)", "Hindi", "French", "German"];
const TIMEZONES = ["Asia/Kolkata (UTC+05:30)", "UTC", "America/New_York (UTC-05:00)", "Europe/London (UTC+00:00)"];
const CURRENCIES = ["INR", "USD", "EUR", "GBP"];
const DATE_FORMATS = ["DD/MM/YYYY", "MM/DD/YYYY", "YYYY-MM-DD"];

function SelectField({ label, options, value, onChange }: { label: string; options: string[]; value: string; onChange: (v: string) => void }) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-2">{label}</label>
      <div className="relative">
        <button
          onClick={() => setOpen(o => !o)}
          className="w-full flex items-center justify-between bg-muted border border-border rounded-lg px-3 py-2.5 text-sm text-foreground hover:border-border-strong transition-colors"
        >
          {value || "Select..."} <ChevronDown className="size-4 text-muted-foreground shrink-0" />
        </button>
        {open && (
          <div className="absolute z-10 top-full mt-1 w-full bg-popover border border-border rounded-lg shadow-xl overflow-hidden max-h-60 overflow-y-auto">
            {options.map(o => (
              <button key={o} onClick={() => { onChange(o); setOpen(false); }}
                className={`w-full text-left px-4 py-2.5 text-sm hover:bg-muted transition-colors flex items-center justify-between ${o === value ? "text-primary font-medium" : "text-foreground"}`}>
                {o} {o === value && <Check className="size-4" />}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export function GeneralPanel({ data, onChange }: { data?: any, onChange?: (domain: string, field: string, value: any) => void }) {
  if (!data?.profile) return null;

  const initials = data.profile.full_name?.substring(0, 2).toUpperCase() || "US";

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-foreground mb-0.5">General</h2>
        <p className="text-sm text-muted-foreground">Account preferences and workspace identity.</p>
      </div>

      {/* Profile */}
      <Card className="border-border bg-surface p-6 space-y-5">
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Profile</div>

        <div className="flex items-center gap-4">
          <div className="size-14 rounded-2xl bg-primary/20 border border-primary/30 flex items-center justify-center text-xl font-bold text-primary shrink-0">
            {initials}
          </div>
          <div>
            <div className="font-semibold text-foreground">{data.profile.full_name}</div>
            <div className="text-sm text-muted-foreground">{data.profile.email}</div>
            <div className="text-xs text-muted-foreground mt-0.5">Pro Plan</div>
          </div>
          <button className="ml-auto text-xs text-primary hover:underline">Change avatar</button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-2">Full name</label>
            <input value={data.profile.full_name || ""} onChange={e => onChange?.("profile", "full_name", e.target.value)}
              className="w-full bg-background border border-border rounded-lg px-3 py-2.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40" />
          </div>
          <div>
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-2">Email</label>
            <div className="relative">
              <input value={data.profile.email || ""} disabled
                className="w-full bg-muted border border-border rounded-lg px-3 py-2.5 pr-24 text-sm text-muted-foreground focus:outline-none cursor-not-allowed" />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1 text-xs text-safe font-semibold">
                <Check className="size-3" /> Verified
              </span>
            </div>
          </div>
        </div>
      </Card>

      {/* Language & Region */}
      <Card className="border-border bg-surface p-6 space-y-5">
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Language & Region</div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <SelectField label="Language"    options={LANGUAGES}    value={data.prefs?.language || "English (US)"}     onChange={v => onChange?.("prefs", "language", v)} />
          <SelectField label="Timezone"    options={TIMEZONES}    value={data.prefs?.timezone || "UTC"}       onChange={v => onChange?.("prefs", "timezone", v)} />
          <SelectField label="Currency"    options={CURRENCIES}   value={data.workspace?.currency || "USD"} onChange={v => onChange?.("workspace", "currency", v)} />
          <SelectField label="Date format" options={DATE_FORMATS} value={data.prefs?.date_format || "YYYY-MM-DD"}  onChange={v => onChange?.("prefs", "date_format", v)} />
        </div>
      </Card>
    </div>
  );
}
