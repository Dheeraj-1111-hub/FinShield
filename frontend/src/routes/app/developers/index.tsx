import React, { useState } from 'react';
import { useDeveloper } from '../../../hooks/useDeveloper';
import { 
  Key, Box, Activity, Settings, 
  TerminalSquare, Webhook, FileText, 
  Plus, Check, Copy, Trash2
} from 'lucide-react';
import { format } from 'date-fns';

export const DevelopersDashboard = () => {
  const { 
    clients, credentials, webhooks, requestLogs,
    createClient, createCredential, revokeCredential, createWebhook,
    isLoadingClients, isLoadingCredentials
  } = useDeveloper();

  const [activeTab, setActiveTab] = useState<'overview' | 'clients' | 'keys' | 'webhooks' | 'logs'>('overview');

  // Modal states
  const [isCreateKeyModalOpen, setIsCreateKeyModalOpen] = useState(false);
  const [newKeyData, setNewKeyData] = useState<{name: string, client_id: string, scopes: string[]}>({
    name: '',
    client_id: '',
    scopes: ['agents:write', 'intents:write']
  });
  const [createdSecret, setCreatedSecret] = useState<string | null>(null);

  // Webhook form states
  const [isCreateWebhookModalOpen, setIsCreateWebhookModalOpen] = useState(false);
  const [newWebhookData, setNewWebhookData] = useState<{url: string, description: string, subscribed_events: string[]}>({
    url: '',
    description: '',
    subscribed_events: ['intent.created', 'payment.success']
  });

  const handleCreateKey = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const result = await createCredential({
        api_client_id: newKeyData.client_id || (clients && clients[0]?.id) || '',
        name: newKeyData.name,
        scopes: newKeyData.scopes
      });
      setCreatedSecret(result.secret);
    } catch (err) {
      console.error(err);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const handleCreateWebhook = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createWebhook({
        url: newWebhookData.url,
        description: newWebhookData.description,
        subscribed_events: newWebhookData.subscribed_events
      });
      setIsCreateWebhookModalOpen(false);
      setNewWebhookData({url: '', description: '', subscribed_events: ['intent.created', 'payment.success']});
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="flex-1 overflow-auto bg-black text-white p-8">
      <div className="max-w-6xl mx-auto space-y-8">
        
        <header>
          <h1 className="text-3xl font-light tracking-tight">Developers</h1>
          <p className="text-gray-400 mt-2 text-sm">
            Integration platform, API credentials, and webhooks.
          </p>
        </header>

        {/* Tabs */}
        <div className="flex border-b border-gray-800 space-x-6">
          <button 
            className={`pb-3 text-sm transition-colors ${activeTab === 'overview' ? 'border-b-2 border-indigo-500 text-indigo-400' : 'text-gray-400 hover:text-gray-300'}`}
            onClick={() => setActiveTab('overview')}
          >
            Overview
          </button>
          <button 
            className={`pb-3 text-sm transition-colors ${activeTab === 'keys' ? 'border-b-2 border-indigo-500 text-indigo-400' : 'text-gray-400 hover:text-gray-300'}`}
            onClick={() => setActiveTab('keys')}
          >
            API Keys
          </button>
          <button 
            className={`pb-3 text-sm transition-colors ${activeTab === 'webhooks' ? 'border-b-2 border-indigo-500 text-indigo-400' : 'text-gray-400 hover:text-gray-300'}`}
            onClick={() => setActiveTab('webhooks')}
          >
            Webhooks
          </button>
          <button 
            className={`pb-3 text-sm transition-colors ${activeTab === 'logs' ? 'border-b-2 border-indigo-500 text-indigo-400' : 'text-gray-400 hover:text-gray-300'}`}
            onClick={() => setActiveTab('logs')}
          >
            Request Logs
          </button>
        </div>

        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-400">Total API Requests (24h)</p>
                  <p className="text-2xl mt-1">{requestLogs?.length || 0}</p>
                </div>
                <div className="p-3 bg-gray-800 rounded-lg">
                  <Activity className="w-5 h-5 text-indigo-400" />
                </div>
              </div>
            </div>
            
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-400">Active API Keys</p>
                  <p className="text-2xl mt-1">{credentials?.filter(c => c.status === 'ACTIVE').length || 0}</p>
                </div>
                <div className="p-3 bg-gray-800 rounded-lg">
                  <Key className="w-5 h-5 text-indigo-400" />
                </div>
              </div>
            </div>

            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-400">Active Webhooks</p>
                  <p className="text-2xl mt-1">{webhooks?.length || 0}</p>
                </div>
                <div className="p-3 bg-gray-800 rounded-lg">
                  <Webhook className="w-5 h-5 text-indigo-400" />
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'keys' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-medium">API Credentials</h2>
              <button 
                onClick={() => setIsCreateKeyModalOpen(true)}
                className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm flex items-center transition-colors"
              >
                <Plus className="w-4 h-4 mr-2" />
                Generate New Key
              </button>
            </div>

            <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-gray-800 text-gray-400 bg-gray-950/50">
                    <th className="px-6 py-4 font-medium">Name</th>
                    <th className="px-6 py-4 font-medium">Prefix</th>
                    <th className="px-6 py-4 font-medium">Status</th>
                    <th className="px-6 py-4 font-medium">Created</th>
                    <th className="px-6 py-4 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800">
                  {credentials?.map((cred) => (
                    <tr key={cred.id} className="hover:bg-gray-800/50 transition-colors">
                      <td className="px-6 py-4 font-medium">{cred.name}</td>
                      <td className="px-6 py-4 font-mono text-gray-400">{cred.credential_prefix}...</td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded-full text-xs ${cred.status === 'ACTIVE' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
                          {cred.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-gray-400">
                        {format(new Date(cred.created_at), 'MMM d, yyyy')}
                      </td>
                      <td className="px-6 py-4">
                        {cred.status === 'ACTIVE' && (
                          <button 
                            onClick={() => revokeCredential(cred.id)}
                            className="text-red-400 hover:text-red-300 text-xs"
                          >
                            Revoke
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                  {credentials?.length === 0 && (
                    <tr>
                      <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                        No API credentials found. Generate one to get started.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'webhooks' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-medium">Webhooks</h2>
              <button 
                onClick={() => setIsCreateWebhookModalOpen(true)}
                className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm flex items-center transition-colors"
              >
                <Plus className="w-4 h-4 mr-2" />
                Add Webhook
              </button>
            </div>

            <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-gray-800 text-gray-400 bg-gray-950/50">
                    <th className="px-6 py-4 font-medium">URL</th>
                    <th className="px-6 py-4 font-medium">Status</th>
                    <th className="px-6 py-4 font-medium">Events</th>
                    <th className="px-6 py-4 font-medium">Created</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800">
                  {webhooks?.map((wh) => (
                    <tr key={wh.id} className="hover:bg-gray-800/50 transition-colors">
                      <td className="px-6 py-4 font-medium max-w-xs truncate">{wh.url}</td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded-full text-xs ${wh.status === 'ACTIVE' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
                          {wh.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-gray-400">
                        {wh.subscribed_events.length} events
                      </td>
                      <td className="px-6 py-4 text-gray-400">
                        {format(new Date(wh.created_at), 'MMM d, yyyy')}
                      </td>
                    </tr>
                  ))}
                  {webhooks?.length === 0 && (
                    <tr>
                      <td colSpan={4} className="px-6 py-8 text-center text-gray-500">
                        No webhooks configured. Add one to receive real-time updates.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'logs' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-medium">API Request Logs</h2>
            </div>

            <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-gray-800 text-gray-400 bg-gray-950/50">
                    <th className="px-6 py-4 font-medium">Time</th>
                    <th className="px-6 py-4 font-medium">Method</th>
                    <th className="px-6 py-4 font-medium">Route</th>
                    <th className="px-6 py-4 font-medium">Status</th>
                    <th className="px-6 py-4 font-medium">Latency</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800">
                  {requestLogs?.map((log) => (
                    <tr key={log.id} className="hover:bg-gray-800/50 transition-colors">
                      <td className="px-6 py-4 text-gray-400">
                        {format(new Date(log.occurred_at), 'MMM d, yyyy HH:mm:ss')}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded text-xs font-mono
                          ${log.method === 'GET' ? 'bg-blue-500/10 text-blue-400' : 
                            log.method === 'POST' ? 'bg-green-500/10 text-green-400' : 
                            'bg-gray-500/10 text-gray-400'}`}
                        >
                          {log.method}
                        </span>
                      </td>
                      <td className="px-6 py-4 font-mono text-gray-300 text-xs">{log.route}</td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded-full text-xs
                          ${log.status_code >= 200 && log.status_code < 300 ? 'bg-green-500/10 text-green-400' : 
                            log.status_code >= 400 ? 'bg-red-500/10 text-red-400' : 
                            'bg-yellow-500/10 text-yellow-400'}`}
                        >
                          {log.status_code}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-gray-400 font-mono text-xs">
                        {log.latency_ms}ms
                      </td>
                    </tr>
                  ))}
                  {requestLogs?.length === 0 && (
                    <tr>
                      <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                        No API requests recorded yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

      </div>

      {/* Create Key Modal */}
      {isCreateKeyModalOpen && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-2xl w-full max-w-md overflow-hidden">
            <div className="p-6 border-b border-gray-800">
              <h3 className="text-xl font-medium">Generate API Key</h3>
            </div>
            
            {createdSecret ? (
              <div className="p-6 space-y-6">
                <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4 text-sm text-yellow-200">
                  <p className="font-medium mb-1">Save your secret key!</p>
                  <p className="text-yellow-200/70">This is the only time it will be shown. If you lose it, you will need to generate a new one.</p>
                </div>
                
                <div className="relative">
                  <input 
                    type="text" 
                    readOnly 
                    value={createdSecret}
                    className="w-full bg-black border border-gray-800 rounded-lg py-3 px-4 text-mono text-sm pr-12"
                  />
                  <button 
                    onClick={() => copyToClipboard(createdSecret)}
                    className="absolute right-3 top-3 text-gray-400 hover:text-white"
                  >
                    <Copy className="w-5 h-5" />
                  </button>
                </div>

                <div className="flex justify-end pt-2">
                  <button 
                    onClick={() => {
                      setIsCreateKeyModalOpen(false);
                      setCreatedSecret(null);
                    }}
                    className="bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-2 rounded-lg text-sm transition-colors"
                  >
                    I have saved it
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleCreateKey} className="p-6 space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-2">Key Name</label>
                  <input 
                    type="text" 
                    required
                    value={newKeyData.name}
                    onChange={e => setNewKeyData({...newKeyData, name: e.target.value})}
                    className="w-full bg-black border border-gray-800 rounded-lg py-2 px-3 text-sm focus:outline-none focus:border-indigo-500"
                    placeholder="e.g. Production Backend"
                  />
                </div>
                
                <div className="flex justify-end space-x-3 pt-2">
                  <button 
                    type="button"
                    onClick={() => setIsCreateKeyModalOpen(false)}
                    className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors"
                  >
                    Cancel
                  </button>
                  <button 
                    type="submit"
                    className="bg-white text-black hover:bg-gray-200 px-6 py-2 rounded-lg text-sm font-medium transition-colors"
                  >
                    Generate
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* Create Webhook Modal */}
      {isCreateWebhookModalOpen && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-2xl w-full max-w-md overflow-hidden">
            <div className="p-6 border-b border-gray-800">
              <h3 className="text-xl font-medium">Add Webhook</h3>
            </div>
            
            <form onSubmit={handleCreateWebhook} className="p-6 space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">Endpoint URL</label>
                <input 
                  type="url" 
                  required
                  value={newWebhookData.url}
                  onChange={e => setNewWebhookData({...newWebhookData, url: e.target.value})}
                  className="w-full bg-black border border-gray-800 rounded-lg py-2 px-3 text-sm focus:outline-none focus:border-indigo-500"
                  placeholder="https://api.yourdomain.com/webhooks/finshield"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">Description (Optional)</label>
                <input 
                  type="text" 
                  value={newWebhookData.description}
                  onChange={e => setNewWebhookData({...newWebhookData, description: e.target.value})}
                  className="w-full bg-black border border-gray-800 rounded-lg py-2 px-3 text-sm focus:outline-none focus:border-indigo-500"
                  placeholder="Production Webhook"
                />
              </div>
              
              <div className="flex justify-end space-x-3 pt-2">
                <button 
                  type="button"
                  onClick={() => setIsCreateWebhookModalOpen(false)}
                  className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors"
                >
                  Cancel
                </button>
                <button 
                  type="submit"
                  className="bg-white text-black hover:bg-gray-200 px-6 py-2 rounded-lg text-sm font-medium transition-colors"
                >
                  Add Webhook
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
