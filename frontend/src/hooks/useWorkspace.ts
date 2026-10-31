import { useAuth } from "@/lib/auth-context";

export function useWorkspace() {
  try {
    const { workspace } = useAuth();
    return {
      workspace,
      currentWorkspace: workspace
    };
  } catch {
    return {
      workspace: null,
      currentWorkspace: null
    };
  }
}
