import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  getApiClients, createApiClient, 
  getApiCredentials, createApiCredential, revokeApiCredential,
  getWebhooks, createWebhook,
  getRequestLogs
} from '../api/developer';
import { useWorkspace } from './useWorkspace';

export const useDeveloper = () => {
  const queryClient = useQueryClient();
  const { currentWorkspace } = useWorkspace();
  const workspaceId = currentWorkspace?.id || '';

  const clientsQuery = useQuery({
    queryKey: ['apiClients', workspaceId],
    queryFn: () => getApiClients(workspaceId),
    enabled: !!workspaceId,
  });

  const createClientMutation = useMutation({
    mutationFn: (data: { name: string, description?: string }) => createApiClient(workspaceId, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['apiClients', workspaceId] }),
  });

  const credentialsQuery = useQuery({
    queryKey: ['apiCredentials', workspaceId],
    queryFn: () => getApiCredentials(workspaceId),
    enabled: !!workspaceId,
  });

  const createCredentialMutation = useMutation({
    mutationFn: (data: { api_client_id: string, name: string, scopes: string[] }) => createApiCredential(workspaceId, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['apiCredentials', workspaceId] }),
  });

  const revokeCredentialMutation = useMutation({
    mutationFn: (credentialId: string) => revokeApiCredential(workspaceId, credentialId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['apiCredentials', workspaceId] }),
  });

  const webhooksQuery = useQuery({
    queryKey: ['webhooks', workspaceId],
    queryFn: () => getWebhooks(workspaceId),
    enabled: !!workspaceId,
  });

  const createWebhookMutation = useMutation({
    mutationFn: (data: { url: string, description?: string, subscribed_events: string[] }) => createWebhook(workspaceId, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['webhooks', workspaceId] }),
  });

  const requestLogsQuery = useQuery({
    queryKey: ['apiRequestLogs', workspaceId],
    queryFn: () => getRequestLogs(workspaceId),
    enabled: !!workspaceId,
    refetchInterval: 5000 // Poll every 5s for dashboard feel
  });

  return {
    clients: clientsQuery.data,
    isLoadingClients: clientsQuery.isLoading,
    createClient: createClientMutation.mutateAsync,
    
    credentials: credentialsQuery.data,
    isLoadingCredentials: credentialsQuery.isLoading,
    createCredential: createCredentialMutation.mutateAsync,
    revokeCredential: revokeCredentialMutation.mutateAsync,

    webhooks: webhooksQuery.data,
    isLoadingWebhooks: webhooksQuery.isLoading,
    createWebhook: createWebhookMutation.mutateAsync,

    requestLogs: requestLogsQuery.data,
    isLoadingLogs: requestLogsQuery.isLoading,
  };
};
