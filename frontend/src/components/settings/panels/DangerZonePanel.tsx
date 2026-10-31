import { useState } from "react";
import { AlertTriangle, RotateCcw, Key, Trash2 } from "lucide-react";
import { ConfirmationModal } from "@/components/settings/ConfirmationModal";

interface DangerAction {
  id: string;
  icon: React.ElementType;
  title: string;
  description: string;
  buttonLabel: string;
  confirmPhrase: string;
  confirmLabel: string;
  impacts: string[];
}

const ACTIONS: DangerAction[] = [
  {
    id: "reset",
    icon: RotateCcw,
    title: "Reset sandbox data",
    description: "Delete sandbox agents, transactions, test events, and investigation history. Your policies and API keys will not be affected.",
    buttonLabel: "Reset sandbox",
    confirmPhrase: "RESET",
    confirmLabel: "Reset sandbox",
    impacts: [
      "All sandbox agents will be deregistered",
      "All test transactions will be deleted",
      "All investigation history will be removed",
      "All security lab tests will be cleared",
    ],
  },
  {
    id: "revoke",
    icon: Key,
    title: "Revoke all API keys",
    description: "Immediately invalidate every workspace API key. Connected agents will stop authenticating until new keys are issued.",
    buttonLabel: "Revoke all keys",
    confirmPhrase: "REVOKE",
    confirmLabel: "Revoke all keys",
    impacts: [
      "3 API keys will be immediately invalidated",
      "2 connected agents will lose authentication",
      "18,492 recent API requests may stop authenticating",
      "Webhook deliveries may fail until keys are reissued",
    ],
  },
  {
    id: "delete",
    icon: Trash2,
    title: "Delete workspace",
    description: "Permanently delete this FINSHIELD workspace and all associated data. This cannot be undone.",
    buttonLabel: "Delete workspace",
    confirmPhrase: "DELETE WORKSPACE",
    confirmLabel: "Delete workspace",
    impacts: [
      "All workspace data will be permanently deleted",
      "All agents, policies, and investigations will be removed",
      "All audit logs will be destroyed",
      "All API keys and webhooks will be invalidated",
      "Your account will be downgraded to no workspace",
    ],
  },
];

export function DangerZonePanel() {
  const [activeModal, setActiveModal] = useState<string | null>(null);
  const action = ACTIONS.find(a => a.id === activeModal) ?? null;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-danger mb-0.5">Danger Zone</h2>
        <p className="text-sm text-muted-foreground">Destructive and irreversible workspace actions.</p>
      </div>

      <div className="border border-danger/25 rounded-2xl overflow-hidden divide-y divide-danger/15">
        {ACTIONS.map(action => {
          const Icon = action.icon;
          return (
            <div key={action.id} className="px-6 py-5 flex items-start justify-between gap-6 bg-surface hover:bg-danger/3 transition-colors">
              <div className="flex items-start gap-4 min-w-0">
                <div className="size-9 rounded-xl bg-danger/10 border border-danger/20 flex items-center justify-center shrink-0">
                  <Icon className="size-4 text-danger" />
                </div>
                <div>
                  <div className="font-semibold text-foreground">{action.title}</div>
                  <div className="text-sm text-muted-foreground mt-1">{action.description}</div>
                </div>
              </div>
              <button
                onClick={() => setActiveModal(action.id)}
                className="shrink-0 px-4 py-2 rounded-lg border border-danger/30 bg-danger/8 text-danger hover:bg-danger/15 transition-colors text-sm font-medium whitespace-nowrap"
              >
                {action.buttonLabel}
              </button>
            </div>
          );
        })}
      </div>

      <div className="flex items-start gap-2.5 p-4 bg-danger/5 border border-danger/15 rounded-xl">
        <AlertTriangle className="size-4 text-danger shrink-0 mt-0.5" />
        <p className="text-xs text-muted-foreground">
          Actions in the Danger Zone are permanent and cannot be recovered. All destructive operations require typed confirmation before executing.
        </p>
      </div>

      {action && (
        <ConfirmationModal
          open={activeModal !== null}
          title={`${action.title}?`}
          description={action.description}
          impacts={action.impacts}
          confirmPhrase={action.confirmPhrase}
          confirmLabel={action.confirmLabel}
          onClose={() => setActiveModal(null)}
          onConfirm={() => { /* Real implementation would call API */ }}
        />
      )}
    </div>
  );
}
