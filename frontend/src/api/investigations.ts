import { api as apiClient } from "@/lib/api-client";
import type { 
  Investigation, 
  InvestigationCreate, 
  InvestigationEvidence, 
  InvestigationNote, 
  InvestigationNoteCreate, 
  InvestigationResolutionReq, 
  InvestigationStatus, 
  InvestigationTimelineEvent 
} from '../types/investigation';

export const investigationsApi = {
  getInvestigations: async (params?: { 
    status?: InvestigationStatus, 
    priority?: string, 
    type?: string,
    assigned_to?: string,
    agent_id?: string,
    run_id?: string,
    skip?: number, 
    limit?: number 
  }) => {
    const response = await apiClient.get<Investigation[]>('/investigations', { params });
    return response.data;
  },

  getInvestigationByRun: async (runId: string) => {
    const response = await apiClient.get<Investigation | null>(`/investigations/by-run/${runId}`);
    return response.data;
  },

  getInvestigation: async (id: string) => {
    const response = await apiClient.get<Investigation>(`/investigations/${id}`);
    return response.data;
  },

  createInvestigation: async (data: InvestigationCreate) => {
    const response = await apiClient.post<Investigation>('/investigations', data);
    return response.data;
  },

  startInvestigation: async (id: string) => {
    const response = await apiClient.post<Investigation>(`/investigations/${id}/start`);
    return response.data;
  },

  escalateInvestigation: async (id: string) => {
    const response = await apiClient.post<Investigation>(`/investigations/${id}/escalate`);
    return response.data;
  },

  resolveInvestigation: async (id: string, data: InvestigationResolutionReq) => {
    const response = await apiClient.post<Investigation>(`/investigations/${id}/resolve`, data);
    return response.data;
  },

  closeInvestigation: async (id: string) => {
    const response = await apiClient.post<Investigation>(`/investigations/${id}/close`);
    return response.data;
  },

  reopenInvestigation: async (id: string) => {
    const response = await apiClient.post<Investigation>(`/investigations/${id}/reopen`);
    return response.data;
  },

  assignInvestigation: async (id: string, assigned_to: string) => {
    const response = await apiClient.post<Investigation>(`/investigations/${id}/assign`, { assigned_to });
    return response.data;
  },

  getEvidence: async (id: string) => {
    const response = await apiClient.get<InvestigationEvidence[]>(`/investigations/${id}/evidence`);
    return response.data;
  },

  getTimeline: async (id: string) => {
    const response = await apiClient.get<InvestigationTimelineEvent[]>(`/investigations/${id}/timeline`);
    return response.data;
  },

  getNotes: async (id: string) => {
    const response = await apiClient.get<InvestigationNote[]>(`/investigations/${id}/notes`);
    return response.data;
  },

  addNote: async (id: string, data: InvestigationNoteCreate) => {
    const response = await apiClient.post<InvestigationNote>(`/investigations/${id}/notes`, data);
    return response.data;
  }
};
