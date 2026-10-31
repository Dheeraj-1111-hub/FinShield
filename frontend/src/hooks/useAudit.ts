import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getAuditEvents, getAuditEvent, verifyAuditIntegrity, getAuditCorrelation } from '../api/audit';
import { useWorkspace } from './useWorkspace';

export const useAuditEvents = (params?: any) => {
  const { workspace } = useWorkspace();
  
  return useQuery({
    queryKey: ['audit', workspace?.id, params],
    queryFn: () => getAuditEvents(workspace!.id, params),
    enabled: !!workspace?.id,
  });
};

export const useAuditEvent = (eventId: string) => {
  const { workspace } = useWorkspace();
  
  return useQuery({
    queryKey: ['audit', workspace?.id, eventId],
    queryFn: () => getAuditEvent(workspace!.id, eventId),
    enabled: !!workspace?.id && !!eventId,
  });
};

export const useAuditCorrelation = (correlationId: string) => {
  const { workspace } = useWorkspace();
  
  return useQuery({
    queryKey: ['audit', workspace?.id, 'correlation', correlationId],
    queryFn: () => getAuditCorrelation(workspace!.id, correlationId),
    enabled: !!workspace?.id && !!correlationId,
  });
};

export const useVerifyAuditIntegrity = () => {
  const { workspace } = useWorkspace();
  
  return useMutation({
    mutationFn: () => verifyAuditIntegrity(workspace!.id),
  });
};
