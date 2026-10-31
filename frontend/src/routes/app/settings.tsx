import { useState, useEffect } from "react";
import { createFileRoute, useRouter } from "@tanstack/react-router";
import { Settings } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { usersApi, workspacesApi } from "@/api/settings";

import { SettingsNav, SettingsSection } from "@/components/settings/SettingsNav";
import { GeneralPanel }        from "@/components/settings/panels/GeneralPanel";
import { WorkspacePanel }      from "@/components/settings/panels/WorkspacePanel";
import { SecurityPanel }       from "@/components/settings/panels/SecurityPanel";
import { TeamPanel }           from "@/components/settings/panels/TeamPanel";
import { NotificationsPanel }  from "@/components/settings/panels/NotificationsPanel";
import { AiPanel }             from "@/components/settings/panels/AiPanel";
import { DataPrivacyPanel }    from "@/components/settings/panels/DataPrivacyPanel";
import { BillingPanel }        from "@/components/settings/panels/BillingPanel";
import { ApiAccessPanel }      from "@/components/settings/panels/ApiAccessPanel";
import { DangerZonePanel }     from "@/components/settings/panels/DangerZonePanel";

export const Route = createFileRoute("/app/settings")({
  component: SettingsPage,
});

function SettingsPage() {
  const [section, setSection] = useState<SettingsSection>("general");
  const queryClient = useQueryClient();
  
  // Queries
  const { data: profile, isLoading: profileLoading, isError: profileError } = useQuery({ queryKey: ["profile"], queryFn: usersApi.getProfile });
  const { data: prefs, isLoading: prefsLoading, isError: prefsError } = useQuery({ queryKey: ["preferences"], queryFn: usersApi.getPreferences });
  const { data: workspace, isLoading: wsLoading, isError: wsError } = useQuery({ queryKey: ["workspace"], queryFn: workspacesApi.getCurrent });
  const { data: settings, isLoading: settingsLoading, isError: settingsError } = useQuery({ queryKey: ["workspaceSettings"], queryFn: workspacesApi.getSettings });

  // Local state for forms
  const [formData, setFormData] = useState<any>({});
  const [isDirty, setIsDirty] = useState(false);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");

  // Initialize local state when data loads
  useEffect(() => {
    if (profile && prefs && workspace && settings && !isDirty) {
      setFormData({
        profile: { ...profile },
        prefs: { ...prefs },
        workspace: { ...workspace },
        settings: { ...settings }
      });
    }
  }, [profile, prefs, workspace, settings]);

  // Handle unsaved changes warning natively
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (isDirty) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [isDirty]);

  // Mutations
  const updateProfileMutation = useMutation({
    mutationFn: usersApi.updateProfile,
    onSuccess: (data) => queryClient.setQueryData(["profile"], data)
  });
  const updatePrefsMutation = useMutation({
    mutationFn: usersApi.updatePreferences,
    onSuccess: (data) => queryClient.setQueryData(["preferences"], data)
  });
  const updateWorkspaceMutation = useMutation({
    mutationFn: workspacesApi.updateCurrent,
    onSuccess: (data) => queryClient.setQueryData(["workspace"], data)
  });
  const updateSettingsMutation = useMutation({
    mutationFn: workspacesApi.updateSettings,
    onSuccess: (data) => queryClient.setQueryData(["workspaceSettings"], data)
  });

  const handleFieldChange = (domain: string, field: string, value: any) => {
    setFormData((prev: any) => ({
      ...prev,
      [domain]: {
        ...prev[domain],
        [field]: value
      }
    }));
    setIsDirty(true);
    setSaveStatus("idle");
  };

  const handleSave = async () => {
    setSaveStatus("saving");
    setErrorMessage("");
    try {
      if (JSON.stringify(formData.profile) !== JSON.stringify(profile)) {
        await updateProfileMutation.mutateAsync(formData.profile);
      }
      if (JSON.stringify(formData.prefs) !== JSON.stringify(prefs)) {
        await updatePrefsMutation.mutateAsync(formData.prefs);
      }
      if (JSON.stringify(formData.workspace) !== JSON.stringify(workspace)) {
        await updateWorkspaceMutation.mutateAsync(formData.workspace);
      }
      if (JSON.stringify(formData.settings) !== JSON.stringify(settings)) {
        await updateSettingsMutation.mutateAsync(formData.settings);
      }
      
      setIsDirty(false);
      setSaveStatus("saved");
      setTimeout(() => setSaveStatus("idle"), 3000);
    } catch (err: any) {
      setSaveStatus("error");
      setErrorMessage(err.response?.data?.error?.message || "Failed to save changes. Please try again.");
    }
  };

  const isLoading = profileLoading || prefsLoading || wsLoading || settingsLoading;
  const isError = profileError || prefsError || wsError || settingsError;

  if (isLoading) {
    return <div className="max-w-7xl mx-auto p-8 flex items-center justify-center text-muted-foreground">Loading settings...</div>;
  }
  
  if (isError) {
    return (
      <div className="max-w-7xl mx-auto p-8 text-center space-y-4">
        <p className="text-destructive font-medium">Unable to load settings.</p>
        <Button onClick={() => queryClient.invalidateQueries()}>Retry</Button>
      </div>
    );
  }

  const renderPanel = (section: SettingsSection) => {
    switch (section) {
      case "general": return <GeneralPanel data={formData} onChange={handleFieldChange} />;
      case "workspace": return <WorkspacePanel data={formData} onChange={handleFieldChange} />;
      case "security": return <SecurityPanel />;
      case "team": return <TeamPanel />;
      case "notifications": return <NotificationsPanel data={formData} onChange={handleFieldChange} />;
      case "ai": return <AiPanel />;
      case "data": return <DataPrivacyPanel />;
      case "billing": return <BillingPanel />;
      case "api": return <ApiAccessPanel />;
      case "danger": return <DangerZonePanel />;
    }
  };

  return (
    <div className="max-w-7xl mx-auto animate-in fade-in duration-500 pb-16">
      {/* ── Page Header ────────────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <Settings className="size-6 text-primary" />
            <h1 className="text-3xl font-bold tracking-tight text-foreground">Settings</h1>
          </div>
          <p className="text-muted-foreground font-medium">
            Manage your FINSHIELD workspace, security, notifications, billing, and platform preferences.
          </p>
        </div>
        
        <div className="flex items-center gap-4">
          {saveStatus === "error" && (
            <span className="text-destructive text-sm font-medium">{errorMessage}</span>
          )}
          {section !== "danger" && (
            <Button
              className={`shrink-0 gap-2 transition-colors ${saveStatus === "saved" ? "bg-safe/15 text-safe border-safe/20" : "bg-primary hover:bg-primary/90 text-primary-foreground"}`}
              variant={saveStatus === "saved" ? "outline" : "default"}
              onClick={handleSave}
              disabled={!isDirty || saveStatus === "saving"}
            >
              {saveStatus === "saving" ? "Saving..." : saveStatus === "saved" ? "✓ Saved" : "Save changes"}
            </Button>
          )}
        </div>
      </div>

      {/* ── Two-column layout ───────────────────────────────────────────────────── */}
      <div className="flex gap-8 items-start">
        {/* Left nav — sticky */}
        <aside className="w-52 shrink-0 sticky top-6">
          <SettingsNav active={section} onChange={s => {
            if (isDirty) {
              if (!window.confirm("You have unsaved changes. Leave without saving?")) return;
            }
            setSection(s);
          }} />
        </aside>

        {/* Right content */}
        <main className="flex-1 min-w-0 animate-in fade-in slide-in-from-right-2 duration-200" key={section}>
          {renderPanel(section)}
        </main>
      </div>
    </div>
  );
}
