import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { policiesApi, PolicyEvaluationRequest, PolicyEvaluationResponse } from '@/api/policies';
import { Loader2, Play, AlertTriangle, Shield, CheckCircle2, Ban } from 'lucide-react';

export function PolicySimulator() {
  const [formData, setFormData] = useState<PolicyEvaluationRequest>({
    agent_id: 'agent_test_123',
    amount: 10000,
    currency: 'INR',
    merchant_id: 'merchant_456',
    capabilities: ['REQUEST_PAYMENT']
  });

  const [capabilitiesStr, setCapabilitiesStr] = useState('REQUEST_PAYMENT');

  const evalMutation = useMutation({
    mutationFn: policiesApi.evaluate
  });

  const handleSimulate = () => {
    evalMutation.mutate({
      ...formData,
      capabilities: capabilitiesStr.split(',').map(s => s.trim()).filter(Boolean)
    });
  };

  const getDecisionIcon = (decision: string) => {
    switch (decision) {
      case 'ALLOW': return <CheckCircle2 className="h-8 w-8 text-emerald-400" />;
      case 'BLOCK': return <Ban className="h-8 w-8 text-red-400" />;
      case 'REVIEW': return <Shield className="h-8 w-8 text-amber-400" />;
      default: return null;
    }
  };

  const getDecisionColor = (decision: string) => {
    switch (decision) {
      case 'ALLOW': return 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10';
      case 'BLOCK': return 'text-red-400 border-red-500/30 bg-red-500/10';
      case 'REVIEW': return 'text-amber-400 border-amber-500/30 bg-amber-500/10';
      default: return '';
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="space-y-4">
        <h3 className="font-semibold text-sm uppercase tracking-wider text-muted-foreground mb-4">Request Context</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-medium text-muted-foreground">Amount</label>
            <input 
              type="number" 
              className="input w-full bg-black/40 mt-1" 
              value={formData.amount}
              onChange={e => setFormData({...formData, amount: Number(e.target.value)})}
            />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Currency</label>
            <input 
              type="text" 
              className="input w-full bg-black/40 mt-1" 
              value={formData.currency}
              onChange={e => setFormData({...formData, currency: e.target.value})}
            />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Merchant ID (Optional)</label>
            <input 
              type="text" 
              className="input w-full bg-black/40 mt-1" 
              value={formData.merchant_id || ''}
              onChange={e => setFormData({...formData, merchant_id: e.target.value})}
            />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Agent ID</label>
            <input 
              type="text" 
              className="input w-full bg-black/40 mt-1" 
              value={formData.agent_id}
              onChange={e => setFormData({...formData, agent_id: e.target.value})}
            />
          </div>
          <div className="col-span-2">
            <label className="text-xs font-medium text-muted-foreground">Capabilities (comma separated)</label>
            <input 
              type="text" 
              className="input w-full bg-black/40 mt-1" 
              value={capabilitiesStr}
              onChange={e => setCapabilitiesStr(e.target.value)}
            />
          </div>
        </div>

        <button 
          onClick={handleSimulate}
          disabled={evalMutation.isPending}
          className="btn w-full bg-purple-600 hover:bg-purple-500 shadow-lg shadow-purple-500/25 mt-4"
        >
          {evalMutation.isPending ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : (
            <Play className="h-5 w-5 mr-2" />
          )}
          Run Simulation
        </button>
      </div>

      <div className="bg-black/30 rounded-xl p-6 border border-white/5 relative flex flex-col justify-center min-h-[250px]">
        {!evalMutation.data && !evalMutation.isPending && (
          <div className="text-center text-muted-foreground">
            <AlertTriangle className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>Run the simulator to see how policies evaluate this request.</p>
          </div>
        )}
        
        {evalMutation.isPending && (
          <div className="text-center">
            <Loader2 className="h-10 w-10 animate-spin mx-auto text-purple-500" />
            <p className="mt-4 text-purple-300 animate-pulse">Evaluating rules...</p>
          </div>
        )}

        {evalMutation.data && !evalMutation.isPending && (
          <div className="animate-fade-in space-y-6">
            <div className={`p-6 rounded-xl border flex flex-col items-center justify-center text-center ${getDecisionColor(evalMutation.data.decision)}`}>
              {getDecisionIcon(evalMutation.data.decision)}
              <h2 className="text-3xl font-bold mt-2">{evalMutation.data.decision}</h2>
            </div>

            <div className="space-y-4">
              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Matched Policies</h4>
                {evalMutation.data.matched_policies.length === 0 ? (
                  <p className="text-sm">No policies matched.</p>
                ) : (
                  <ul className="space-y-2">
                    {evalMutation.data.matched_policies.map(p => (
                      <li key={p.policy_id} className="text-sm bg-white/5 p-2 rounded flex justify-between">
                        <span className="font-medium">{p.name}</span>
                        <span className="text-xs text-muted-foreground font-mono">{p.policy_id.substring(0,8)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Reasons</h4>
                <ul className="list-disc list-inside space-y-1">
                  {evalMutation.data.reasons.map((r, i) => (
                    <li key={i} className="text-sm">{r}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
