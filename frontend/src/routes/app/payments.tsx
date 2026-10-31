import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { 
  ArrowUpRight, Download, Filter, Search, CheckCircle2, 
  ShieldAlert, XCircle, ShieldCheck
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { paymentsApi, Payment } from "@/api/payments";
import { PaymentDetailsDrawer } from "@/components/payments/PaymentDetailsDrawer";
import { useAuth } from "@/lib/auth-context";

export const Route = createFileRoute("/app/payments")({
  component: PaymentsRoute,
});

function PaymentsRoute() {
  const [selectedPaymentId, setSelectedPaymentId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'CAPTURED' | 'FAILED'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const { workspace } = useAuth();
  
  const { data: payments = [], refetch } = useQuery({
    queryKey: ['payments', workspace?.id],
    queryFn: paymentsApi.list,
    enabled: !!workspace,
  });

  const { data: metrics } = useQuery({
    queryKey: ['payment-metrics', workspace?.id],
    queryFn: paymentsApi.getMetrics,
    enabled: !!workspace,
  });

  const selectedPayment = payments.find(p => p.id === selectedPaymentId);

  const filteredPayments = payments.filter(p => {
    if (statusFilter !== 'ALL' && p.status !== statusFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const matchId = p.id.toLowerCase().includes(q);
      const matchAgent = (p.agent_name || p.agent_id || '').toLowerCase().includes(q);
      const matchOrder = (p.order_id || '').toLowerCase().includes(q);
      const matchIntent = (p.intent_id || '').toLowerCase().includes(q);
      return matchId || matchAgent || matchOrder || matchIntent;
    }
    return true;
  });

  return (
    <div className="space-y-8 animate-in fade-in duration-500 relative">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Payments</h1>
          <p className="text-muted-foreground mt-1">Monitor and control every financial action initiated by your autonomous agents.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" className="bg-surface hover:bg-surface-raised border-border">
            <Download className="mr-2 size-4" /> Export
          </Button>
          <Button variant="outline" className="bg-surface hover:bg-surface-raised border-border">
            <Filter className="mr-2 size-4" /> Filter
          </Button>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-surface border border-border rounded-xl p-5 shadow-sm">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Total Volume</div>
          <div className="text-2xl font-bold tracking-tight mb-2">
            ₹{metrics ? metrics.total_volume.toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 0}) : '0'}
          </div>
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            Captured Payments Only
          </div>
        </div>
        <div className="bg-surface border border-border rounded-xl p-5 shadow-sm">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Transactions</div>
          <div className="text-2xl font-bold tracking-tight mb-2">{metrics ? metrics.transactions : 0}</div>
          <div className="flex items-center gap-4 text-xs">
            <span className="text-safe">{metrics ? metrics.captured_count : 0} captured</span>
            <span className="text-danger">{metrics ? metrics.failed_count : 0} failed</span>
          </div>
        </div>
        <div className="bg-surface border border-border rounded-xl p-5 shadow-sm">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Success Rate</div>
          <div className="text-2xl font-bold tracking-tight mb-2">
            {metrics && metrics.transactions > 0 ? Math.round((metrics.captured_count / metrics.transactions) * 100) : 0}%
          </div>
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            Captured vs Total
          </div>
        </div>
        <div className="bg-danger/5 border border-danger/20 rounded-xl p-5 shadow-sm">
          <div className="text-xs font-semibold text-danger/80 uppercase tracking-wider mb-2">Failed Value</div>
          <div className="text-2xl font-bold tracking-tight text-danger mb-2">
            ₹{metrics ? metrics.failed_value.toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 0}) : '0'}
          </div>
          <div className="text-xs text-danger/70">{metrics ? metrics.failed_count : 0} actions · Value failed</div>
        </div>
      </div>

      {/* Payment Lifecycle Viz */}
      <div className="bg-surface/50 border border-border rounded-xl p-6 hidden md:block">
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-6">Payment Lifecycle</div>
        <div className="flex items-center justify-between text-sm font-medium relative">
          <div className="absolute top-1/2 left-4 right-4 h-px bg-border -translate-y-1/2 -z-10" />
          
          <div className="flex flex-col items-center gap-2 bg-surface/50 px-2 cursor-pointer hover:text-primary transition-colors">
            <div className="size-3 rounded-full bg-border" />
            <span>Request</span>
          </div>
          <div className="flex flex-col items-center gap-2 bg-surface/50 px-2 text-primary">
            <ShieldCheck className="size-5 mb-[-2px] text-primary" />
            <span>FINSHIELD</span>
          </div>
          <div className="flex flex-col items-center gap-2 bg-surface/50 px-2 cursor-pointer hover:text-primary transition-colors">
            <div className="size-3 rounded-full bg-border" />
            <span>Auth</span>
          </div>
          <div className="flex flex-col items-center gap-2 bg-surface/50 px-2 cursor-pointer hover:text-primary transition-colors">
            <div className="size-3 rounded-full bg-border" />
            <span>Capture</span>
          </div>
          <div className="flex flex-col items-center gap-2 bg-surface/50 px-2 cursor-pointer hover:text-primary transition-colors">
            <div className="size-3 rounded-full bg-border" />
            <span>Settlement</span>
          </div>
        </div>
      </div>

      {/* Table Controls */}
      <div className="flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2 bg-surface border border-border rounded-md p-1 overflow-x-auto max-w-full">
          <button 
            onClick={() => setStatusFilter('ALL')}
            className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
              statusFilter === 'ALL' 
                ? 'bg-background shadow-sm text-foreground' 
                : 'text-muted-foreground hover:text-foreground hover:bg-surface-raised'
            }`}
          >
            All <span className="ml-1 text-muted-foreground font-mono text-xs">{payments.length}</span>
          </button>
          <button 
            onClick={() => setStatusFilter('CAPTURED')}
            className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
              statusFilter === 'CAPTURED' 
                ? 'bg-background shadow-sm text-foreground' 
                : 'text-muted-foreground hover:text-foreground hover:bg-surface-raised'
            }`}
          >
            Captured <span className="ml-1 font-mono text-xs">{payments.filter(p => p.status === 'CAPTURED').length}</span>
          </button>
          <button 
            onClick={() => setStatusFilter('FAILED')}
            className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
              statusFilter === 'FAILED' 
                ? 'bg-background shadow-sm text-foreground' 
                : 'text-muted-foreground hover:text-foreground hover:bg-surface-raised'
            }`}
          >
            Failed <span className="ml-1 font-mono text-xs">{payments.filter(p => p.status === 'FAILED').length}</span>
          </button>
        </div>

        <div className="relative w-full md:w-64">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
          <input 
            type="text" 
            placeholder="Search payments..." 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-surface border border-border rounded-md py-2 pl-9 pr-4 text-sm focus:outline-none focus:ring-1 focus:ring-primary/50"
          />
        </div>
      </div>

      {/* Payments Table */}
      <div className="bg-surface border border-border rounded-xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-surface-raised border-b border-border text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              <tr>
                <th className="px-5 py-4 w-12 text-center">St</th>
                <th className="px-5 py-4">Payment</th>
                <th className="px-5 py-4">Agent</th>
                <th className="px-5 py-4">Purpose</th>
                <th className="px-5 py-4 text-right">Amount</th>
                <th className="px-5 py-4">Risk</th>
                <th className="px-5 py-4">FINSHIELD</th>
                <th className="px-5 py-4 text-right">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filteredPayments.map((payment) => {
                const isFailed = payment.status === 'FAILED' || payment.status === 'CANCELLED';
                const isCaptured = payment.status === 'CAPTURED';
                const isAuthorized = payment.status === 'AUTHORIZED';
                
                return (
                  <tr 
                    key={payment.id} 
                    className="hover:bg-surface-raised cursor-pointer transition-colors group"
                    onClick={() => setSelectedPaymentId(payment.id)}
                  >
                    <td className="px-5 py-4 text-center">
                      {isCaptured && <CheckCircle2 className="size-4 text-safe mx-auto" />}
                      {!isCaptured && !isFailed && <ShieldAlert className="size-4 text-warn mx-auto" />}
                      {isFailed && <XCircle className="size-4 text-danger mx-auto" />}
                    </td>
                    <td className="px-5 py-4 font-mono font-medium">{payment.id}</td>
                    <td className="px-5 py-4">
                      <div className="font-medium group-hover:text-primary transition-colors">{payment.agent_name || payment.agent_id || "None"}</div>
                    </td>
                    <td className="px-5 py-4">
                      <div className="truncate max-w-[200px]">{payment.intent_id || "N/A"}</div>
                      <div className="text-xs text-muted-foreground">{payment.order_id || "N/A"}</div>
                    </td>
                    <td className="px-5 py-4 text-right font-medium">
                      {payment.currency === 'INR' ? '₹' : (payment.currency === 'USD' ? '$' : `${payment.currency} `)}
                      {payment.amount.toLocaleString(undefined, {minimumFractionDigits: 2})}
                    </td>
                    <td className="px-5 py-4">
                      <span className={`px-2 py-0.5 rounded text-xs font-semibold tracking-wider ${
                        payment.risk_level === 'HIGH' || payment.risk_level === 'CRITICAL' ? 'bg-danger/10 text-danger' : 
                        payment.risk_level === 'MEDIUM' ? 'bg-warn/10 text-warn' : 
                        payment.risk_level === 'LOW' ? 'bg-safe/10 text-safe' : 'bg-surface-raised text-muted-foreground'
                      }`}>
                        {payment.risk_level || "N/A"}
                      </span>
                    </td>
                    <td className="px-5 py-4">
                      <div className={`flex items-center gap-1.5 font-semibold text-xs tracking-wider ${
                        payment.gate_decision === 'ALLOW' ? 'text-safe' :
                        payment.gate_decision === 'BLOCK' ? 'text-danger' :
                        payment.gate_decision === 'REVIEW_REQUIRED' ? 'text-warn' : 'text-muted-foreground'
                      }`}>
                        {payment.gate_decision === 'ALLOW' ? <ShieldCheck className="size-3.5" /> : 
                         payment.gate_decision === 'BLOCK' ? <XCircle className="size-3.5" /> : 
                         payment.gate_decision === 'REVIEW_REQUIRED' ? <ShieldAlert className="size-3.5" /> : null}
                        {payment.gate_decision || "N/A"}
                      </div>
                    </td>
                    <td className="px-5 py-4 text-right text-muted-foreground whitespace-nowrap">
                      {new Date(payment.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Drawer Overlay & Component */}
      {selectedPayment && (
        <>
          <div 
            className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40 animate-in fade-in duration-300"
            onClick={() => setSelectedPaymentId(null)}
          />
          <PaymentDetailsDrawer 
            payment={selectedPayment} 
            onClose={() => {
              setSelectedPaymentId(null);
              refetch();
            }} 
          />
        </>
      )}

    </div>
  );
}
