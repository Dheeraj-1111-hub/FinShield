import { useState } from "react";
import { X, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Props {
  open: boolean;
  title: string;
  description: string;
  impacts: string[];
  confirmPhrase: string;
  confirmLabel: string;
  onClose: () => void;
  onConfirm: () => void;
}

export function ConfirmationModal({
  open, title, description, impacts, confirmPhrase, confirmLabel, onClose, onConfirm,
}: Props) {
  const [typed, setTyped] = useState("");

  if (!open) return null;

  const canConfirm = typed === confirmPhrase;

  const handleConfirm = () => {
    if (!canConfirm) return;
    onConfirm();
    setTyped("");
    onClose();
  };

  const handleClose = () => { setTyped(""); onClose(); };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={handleClose}>
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      <div
        className="relative w-full max-w-md bg-surface border border-danger/30 rounded-2xl shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-start gap-4 p-6 border-b border-border">
          <div className="size-10 rounded-xl bg-danger/10 border border-danger/20 flex items-center justify-center shrink-0">
            <AlertTriangle className="size-5 text-danger" />
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="font-bold text-foreground">{title}</h2>
            <p className="text-sm text-muted-foreground mt-1">{description}</p>
          </div>
          <button onClick={handleClose} className="text-muted-foreground hover:text-foreground transition-colors shrink-0">
            <X className="size-5" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          <div className="bg-danger/8 border border-danger/20 rounded-xl p-4 space-y-1.5">
            {impacts.map((impact, i) => (
              <div key={i} className="flex items-center gap-2 text-sm text-danger">
                <span className="size-1 rounded-full bg-danger shrink-0" />
                {impact}
              </div>
            ))}
            <div className="text-xs text-muted-foreground mt-2 pt-2 border-t border-danger/15">
              This action cannot be undone.
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-2">
              Type <code className="text-danger font-mono">{confirmPhrase}</code> to continue
            </label>
            <input
              value={typed}
              onChange={e => setTyped(e.target.value)}
              placeholder={confirmPhrase}
              className="w-full bg-background border border-border rounded-lg px-3 py-2.5 text-sm font-mono text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:ring-2 focus:ring-danger/40"
              autoComplete="off"
            />
          </div>

          <div className="flex gap-3">
            <Button variant="outline" className="flex-1 border-border bg-background" onClick={handleClose}>
              Cancel
            </Button>
            <Button
              className="flex-1 bg-danger hover:bg-danger/90 text-danger-foreground disabled:opacity-40"
              disabled={!canConfirm}
              onClick={handleConfirm}
            >
              {confirmLabel}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
