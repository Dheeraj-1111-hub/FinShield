import { useState, useEffect } from 'react';
import { createFileRoute } from '@tanstack/react-router';
import { 
  ShieldAlert, 
  Clock, 
  AlertTriangle,
  CheckCircle2,
  Lock,
  UserCircle,
  FileText,
  Activity,
  MessageSquare
} from 'lucide-react';
import { investigationsApi } from '@/api/investigations';
import type { 
  Investigation, 
  InvestigationEvidence, 
  InvestigationTimelineEvent,
  InvestigationNote
} from '@/types/investigation';
import { formatDistanceToNow, format } from 'date-fns';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export const Route = createFileRoute('/app/investigations/$id')({
  component: InvestigationDetail,
});

function InvestigationDetail() {
  const { id } = Route.useParams();
  
  const [investigation, setInvestigation] = useState<Investigation | null>(null);
  const [evidence, setEvidence] = useState<InvestigationEvidence[]>([]);
  const [timeline, setTimeline] = useState<InvestigationTimelineEvent[]>([]);
  const [notes, setNotes] = useState<InvestigationNote[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, [id]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [inv, ev, tl, nts] = await Promise.all([
        investigationsApi.getInvestigation(id),
        investigationsApi.getEvidence(id),
        investigationsApi.getTimeline(id),
        investigationsApi.getNotes(id)
      ]);
      setInvestigation(inv);
      setEvidence(ev);
      setTimeline(tl);
      setNotes(nts);
    } catch (error) {
      console.error('Failed to fetch investigation details:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-12 text-center text-gray-500">
        <div className="animate-spin h-8 w-8 border-4 border-indigo-500 border-t-transparent rounded-full mx-auto mb-4"></div>
        Loading investigation...
      </div>
    );
  }

  if (!investigation) {
    return (
      <div className="p-12 text-center">
        <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-white">Investigation not found</h3>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span className="text-sm font-mono text-gray-500">{investigation.id}</span>
            <span className="px-2 py-0.5 rounded text-xs font-medium border bg-gray-800 text-gray-300 border-gray-700">
              {investigation.status.replace('_', ' ')}
            </span>
            <span className="px-2 py-0.5 rounded text-xs font-medium border bg-gray-800 text-gray-300 border-gray-700">
              {investigation.priority}
            </span>
          </div>
          <h1 className="text-2xl font-semibold text-white">
            {investigation.title}
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            {investigation.description}
          </p>
        </div>
        
        <div className="flex gap-2">
          {investigation.status !== 'CLOSED' && (
            <button className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors">
              Update Status
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card className="bg-gray-900 border-gray-800">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2 text-white">
                <Activity className="h-5 w-5 text-indigo-400" />
                Timeline
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {timeline.map((evt, idx) => (
                  <div key={evt.id} className="relative flex gap-4">
                    {idx !== timeline.length - 1 && (
                      <div className="absolute left-2.5 top-6 bottom-[-24px] w-px bg-gray-800" />
                    )}
                    <div className="relative z-10 flex h-6 w-6 items-center justify-center rounded-full bg-gray-800 border border-gray-700 shrink-0">
                      <div className="h-2 w-2 rounded-full bg-indigo-400" />
                    </div>
                    <div className="flex-1 pb-4">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium text-gray-200">
                          {evt.title}
                        </span>
                        <span className="text-xs text-gray-500">
                          {format(new Date(evt.timestamp), 'MMM d, HH:mm:ss')}
                        </span>
                      </div>
                      {evt.description && (
                        <p className="text-sm text-gray-400">
                          {evt.description}
                        </p>
                      )}
                      {evt.metadata && Object.keys(evt.metadata).length > 0 && (
                        <div className="mt-2 p-2 bg-gray-950 rounded border border-gray-800 text-xs font-mono text-gray-400">
                          {JSON.stringify(evt.metadata, null, 2)}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
          
          <Card className="bg-gray-900 border-gray-800">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2 text-white">
                <FileText className="h-5 w-5 text-emerald-400" />
                Evidence & Logs
              </CardTitle>
            </CardHeader>
            <CardContent>
              {evidence.length === 0 ? (
                <p className="text-sm text-gray-500 text-center py-4">No evidence collected yet.</p>
              ) : (
                <div className="space-y-4">
                  {evidence.map(ev => (
                    <div key={ev.id} className="p-3 bg-gray-950 rounded-lg border border-gray-800">
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <span className="text-sm font-medium text-gray-300">{ev.title || ev.entity_type}</span>
                          <span className="ml-2 text-xs text-gray-500">{ev.entity_id}</span>
                        </div>
                        <span className="text-xs px-2 py-0.5 rounded bg-gray-800 text-gray-400">
                          {ev.evidence_type}
                        </span>
                      </div>
                      <div className="text-xs font-mono text-gray-400 overflow-x-auto bg-gray-900 p-2 rounded">
                        <pre>{JSON.stringify(ev.snapshot, null, 2)}</pre>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card className="bg-gray-900 border-gray-800">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2 text-white">
                <UserCircle className="h-5 w-5 text-blue-400" />
                Details
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4 text-sm">
                <div>
                  <span className="text-gray-500 block mb-1">Agent ID</span>
                  <span className="text-gray-200 font-mono">{investigation.agent_id}</span>
                </div>
                {investigation.original_intent && (
                  <div>
                    <span className="text-gray-500 block mb-1">Original Intent</span>
                    <span className="text-gray-200">{investigation.original_intent}</span>
                  </div>
                )}
                {(investigation.executed_intent || investigation.proposed_action) && (
                  <div>
                    <span className="text-gray-500 block mb-1">Proposed Action</span>
                    <span className="text-gray-200 font-mono">{investigation.executed_intent || investigation.proposed_action}</span>
                  </div>
                )}
                {investigation.decision_reason && (
                  <div>
                    <span className="text-gray-500 block mb-1">Decision Reason / Outcome</span>
                    <span className="text-gray-200">{investigation.decision_reason}</span>
                  </div>
                )}
                {typeof investigation.intent_alignment === 'number' && (
                  <div>
                    <span className="text-gray-500 block mb-1">Intent Alignment</span>
                    <span className={`font-mono font-bold ${investigation.intent_alignment >= 80 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {investigation.intent_alignment}% MATCH
                    </span>
                  </div>
                )}
                <div>
                  <span className="text-gray-500 block mb-1">Created At</span>
                  <span className="text-gray-200">{format(new Date(investigation.created_at), 'PPP p')}</span>
                </div>
                <div>
                  <span className="text-gray-500 block mb-1">Assigned To</span>
                  <span className="text-gray-200">{investigation.assigned_to || 'Unassigned'}</span>
                </div>
                {investigation.resolution && (
                  <div>
                    <span className="text-gray-500 block mb-1">Resolution</span>
                    <span className="text-emerald-400 font-medium">{investigation.resolution.replace(/_/g, ' ')}</span>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
          
          <Card className="bg-gray-900 border-gray-800">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2 text-white">
                <MessageSquare className="h-5 w-5 text-purple-400" />
                Analyst Notes
              </CardTitle>
            </CardHeader>
            <CardContent>
              {notes.length === 0 ? (
                <p className="text-sm text-gray-500 text-center py-4">No notes added.</p>
              ) : (
                <div className="space-y-4">
                  {notes.map(note => (
                    <div key={note.id} className="p-3 bg-gray-800/50 rounded-lg border border-gray-800">
                      <p className="text-sm text-gray-300">{note.content}</p>
                      <div className="mt-2 text-xs text-gray-500 flex justify-between">
                        <span>{note.author_id}</span>
                        <span>{formatDistanceToNow(new Date(note.created_at), { addSuffix: true })}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
