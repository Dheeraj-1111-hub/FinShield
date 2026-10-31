import { useState, useEffect } from 'react';
import { useNavigate, createFileRoute } from '@tanstack/react-router';
import { 
  ShieldAlert, 
  Search, 
  Filter, 
  Clock, 
  AlertTriangle,
  CheckCircle2,
  Lock,
  ChevronRight,
  UserCircle
} from 'lucide-react';
import { investigationsApi } from '@/api/investigations';
import type { Investigation, InvestigationStatus, InvestigationPriority } from '@/types/investigation';
import { formatDistanceToNow } from 'date-fns';

export const Route = createFileRoute('/app/investigations/')({
  component: InvestigationsPage,
});

function InvestigationsPage() {
  const navigate = useNavigate();
  const [investigations, setInvestigations] = useState<Investigation[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<InvestigationStatus | 'ALL'>('ALL');

  useEffect(() => {
    fetchInvestigations();
  }, [statusFilter]);

  const fetchInvestigations = async () => {
    try {
      setLoading(true);
      const params = statusFilter !== 'ALL' ? { status: statusFilter } : undefined;
      const data = await investigationsApi.getInvestigations(params);
      setInvestigations(data);
    } catch (error) {
      console.error('Failed to fetch investigations:', error);
    } finally {
      setLoading(false);
    }
  };

  const getPriorityColor = (priority: InvestigationPriority) => {
    switch (priority) {
      case 'CRITICAL': return 'bg-red-500/10 text-red-500 border-red-500/20';
      case 'HIGH': return 'bg-orange-500/10 text-orange-500 border-orange-500/20';
      case 'MEDIUM': return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20';
      case 'LOW': return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
      default: return 'bg-gray-500/10 text-gray-500 border-gray-500/20';
    }
  };

  const getStatusIcon = (status: InvestigationStatus) => {
    switch (status) {
      case 'OPEN': return <AlertTriangle className="h-4 w-4 text-orange-500" />;
      case 'IN_REVIEW': return <Search className="h-4 w-4 text-blue-500" />;
      case 'ESCALATED': return <ShieldAlert className="h-4 w-4 text-red-500" />;
      case 'RESOLVED': return <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
      case 'CLOSED': return <Lock className="h-4 w-4 text-gray-500" />;
      default: return null;
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-semibold text-white flex items-center gap-2">
            <ShieldAlert className="h-6 w-6 text-indigo-400" />
            Security Investigations
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Manage and respond to security events and anomalous agent behavior
          </p>
        </div>
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden shadow-sm">
        <div className="p-4 border-b border-gray-800 flex items-center gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input 
              type="text" 
              placeholder="Search investigations by ID, agent, or keyword..."
              className="w-full bg-gray-950 border border-gray-800 rounded-lg pl-10 pr-4 py-2 text-sm text-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition-all"
            />
          </div>
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-gray-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as any)}
              className="bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-sm text-gray-300 outline-none"
            >
              <option value="ALL">All Statuses</option>
              <option value="OPEN">Open</option>
              <option value="IN_REVIEW">In Review</option>
              <option value="ESCALATED">Escalated</option>
              <option value="RESOLVED">Resolved</option>
              <option value="CLOSED">Closed</option>
            </select>
          </div>
        </div>

        {loading ? (
          <div className="p-12 text-center text-gray-500">
            <div className="animate-spin h-8 w-8 border-4 border-indigo-500 border-t-transparent rounded-full mx-auto mb-4"></div>
            Loading investigations...
          </div>
        ) : investigations.length === 0 ? (
          <div className="p-12 text-center">
            <ShieldAlert className="h-12 w-12 text-gray-700 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-white mb-1">No investigations found</h3>
            <p className="text-gray-400">Everything is secure. There are no active security investigations matching your filters.</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-800">
            {investigations.map((inv) => (
              <div 
                key={inv.id}
                onClick={() => navigate({ to: '/app/investigations/$id', params: { id: inv.id } })}
                className="p-4 hover:bg-gray-800/50 transition-colors cursor-pointer group flex items-center gap-4"
              >
                <div className="flex flex-col gap-2 flex-1">
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-mono text-gray-500">{inv.id}</span>
                    <span className={`px-2 py-0.5 rounded text-xs font-medium border flex items-center gap-1 ${getPriorityColor(inv.priority)}`}>
                      {inv.priority}
                    </span>
                    <span className="flex items-center gap-1.5 text-xs font-medium bg-gray-800 text-gray-300 px-2 py-0.5 rounded border border-gray-700">
                      {getStatusIcon(inv.status)}
                      {inv.status.replace('_', ' ')}
                    </span>
                  </div>
                  
                  <h3 className="text-sm font-medium text-white group-hover:text-indigo-400 transition-colors">
                    {inv.title}
                  </h3>
                  
                  <div className="flex items-center gap-4 text-xs text-gray-400">
                    <span className="flex items-center gap-1">
                      <UserCircle className="h-3.5 w-3.5" />
                      Agent: {inv.agent_id}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-3.5 w-3.5" />
                      {formatDistanceToNow(new Date(inv.created_at), { addSuffix: true })}
                    </span>
                    <span className="flex items-center gap-1 px-1.5 py-0.5 bg-gray-900 rounded border border-gray-800 font-medium">
                      {inv.type.replace(/_/g, ' ')}
                    </span>
                  </div>
                </div>
                
                <div className="text-gray-500 group-hover:text-white transition-colors p-2">
                  <ChevronRight className="h-5 w-5" />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
