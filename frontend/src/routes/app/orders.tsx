import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { 
  ArrowUpRight, Download, Filter, Search, CheckCircle2, 
  ShieldAlert, XCircle, ArrowRight, Package, Truck, Activity, RotateCcw, Box, ShieldCheck, CreditCard
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useQuery } from "@tanstack/react-query";
import { commerceApi, Order } from "@/api/commerce";
import { agentsApi } from "@/api/agents";
import { OrderDetailsDrawer } from "@/components/orders/OrderDetailsDrawer";
import { useAuth } from "@/lib/auth-context";
import { formatCurrency } from "@/lib/utils";

export const Route = createFileRoute("/app/orders")({
  component: OrdersRoute,
});

function OrdersRoute() {
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);

  const { data: orders = [] } = useQuery({
    queryKey: ['orders'],
    queryFn: commerceApi.orders.list
  });

  const { data: agents = [] } = useQuery({
    queryKey: ['agents'],
    queryFn: agentsApi.list
  });

  const { workspace } = useAuth();
  const selectedOrder = orders.find(o => o.id === selectedOrderId);

  // Currency-aware order value calculations
  const totalOrders = orders.length;
  const activeFulfillment = orders.filter(o => o.status === 'PROCESSING' || o.status === 'SHIPPED').length;
  const needsAttention = orders.filter(o => o.status === 'ATTENTION').length;

  // Group order totals by currency strictly to prevent cross-currency summation
  const totalsByCurrency = orders.reduce<Record<string, number>>((acc, o) => {
    const curr = o.currency || workspace?.currency || 'INR';
    acc[curr] = (acc[curr] || 0) + (o.total || 0);
    return acc;
  }, {});

  const settledTotalsByCurrency = orders.filter(o => o.status === 'PAID' || o.status === 'FULFILLED' || o.status === 'COMPLETED').reduce<Record<string, number>>((acc, o) => {
    const curr = o.currency || workspace?.currency || 'INR';
    acc[curr] = (acc[curr] || 0) + (o.total || 0);
    return acc;
  }, {});

  const pendingTotalsByCurrency = orders.filter(o => o.status === 'PENDING_PAYMENT' || o.status === 'PROCESSING' || o.status === 'SHIPPED').reduce<Record<string, number>>((acc, o) => {
    const curr = o.currency || workspace?.currency || 'INR';
    acc[curr] = (acc[curr] || 0) + (o.total || 0);
    return acc;
  }, {});

  const currencies = Object.keys(totalsByCurrency);
  const primaryCurrency = (workspace?.currency && totalsByCurrency[workspace.currency] !== undefined)
    ? workspace.currency
    : (currencies[0] || workspace?.currency || 'INR');
  const primaryTotal = totalsByCurrency[primaryCurrency] || 0;

  return (
    <div className="flex-1 flex flex-col h-full bg-background relative overflow-hidden">
      
      {/* Header */}
      <div className="px-8 py-8 border-b border-border bg-surface shrink-0">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-6">
          <div className="max-w-2xl">
            <h1 className="text-3xl font-bold tracking-tight mb-2">Orders</h1>
            <p className="text-muted-foreground text-lg">
              Monitor purchases, fulfillment, and commerce activity initiated by your autonomous agents.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="outline" className="gap-2">
              <Download className="size-4" /> Export
            </Button>
            <Button variant="outline" className="gap-2">
              <Filter className="size-4" /> Filter
            </Button>
          </div>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-8">
          <div className="bg-surface-raised border border-border rounded-xl p-5 shadow-sm">
            <div className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-2">Total Orders</div>
            <div className="text-3xl font-bold mb-1">{totalOrders}</div>
            <div className="flex items-center gap-2 text-sm">
              <span className="text-muted-foreground">{orders.filter(o => o.status === 'PAID' || o.status === 'FULFILLED' || o.status === 'COMPLETED').length} completed · {activeFulfillment} active</span>
            </div>
          </div>
          <div className="bg-surface-raised border border-border rounded-xl p-5 shadow-sm">
            <div className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-2">
              Gross Order Value ({primaryCurrency})
            </div>
            <div className="text-3xl font-bold mb-1">
              {formatCurrency(primaryTotal, primaryCurrency)}
            </div>
            <div className="flex flex-col gap-1 text-xs">
              {currencies.length > 1 ? (
                <div className="flex flex-wrap items-center gap-1.5 text-muted-foreground">
                  <span>Breakdown:</span>
                  {currencies.map(c => (
                    <span key={c} className="font-mono bg-muted/60 px-1.5 py-0.5 rounded text-[11px] font-medium text-foreground">
                      {formatCurrency(totalsByCurrency[c], c)}
                    </span>
                  ))}
                </div>
              ) : (
                <div className="flex items-center gap-2 text-xs text-muted-foreground font-medium">
                  <span>
                    {formatCurrency(settledTotalsByCurrency[primaryCurrency] || 0, primaryCurrency)} settled · {formatCurrency(pendingTotalsByCurrency[primaryCurrency] || 0, primaryCurrency)} pending
                  </span>
                </div>
              )}
            </div>
          </div>
          <div className="bg-surface-raised border border-border rounded-xl p-5 shadow-sm">
            <div className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-2">In Transit</div>
            <div className="text-3xl font-bold mb-1">{activeFulfillment}</div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span>{orders.filter(o => o.status === 'PROCESSING').length} processing · {orders.filter(o => o.status === 'SHIPPED').length} in transit</span>
            </div>
          </div>
          <div className="bg-warn/5 border border-warn/20 rounded-xl p-5 shadow-sm">
            <div className="text-sm font-semibold text-warn uppercase tracking-wider mb-2">Needs Attention</div>
            <div className="text-3xl font-bold text-warn mb-1">{needsAttention}</div>
            <div className="flex items-center gap-2 text-sm text-warn/80">
              <span>{needsAttention} orders require review</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-auto custom-scrollbar bg-surface/30 p-8">
        
        {/* Fulfillment visualization */}
        <div className="mb-8 p-6 bg-surface-raised border border-border rounded-xl">
          <div className="text-sm font-semibold tracking-wider text-muted-foreground mb-6">ORDER FULFILLMENT PIPELINE</div>
          <div className="flex items-center justify-between relative px-4">
            <div className="absolute top-1/2 left-8 right-8 h-px bg-border -translate-y-1/2 z-0" />
            
            {[
              { label: "Intent", icon: Activity },
              { label: "Placed", icon: CreditCard },
              { label: "Confirmed", icon: CheckCircle2 },
              { label: "Packed", icon: Box },
              { label: "Shipped", icon: Truck },
              { label: "Delivered", icon: Package }
            ].map((step, i) => (
              <div key={i} className="relative z-10 flex flex-col items-center gap-3">
                <div className="size-10 rounded-full bg-background border-2 border-primary/20 flex items-center justify-center text-primary shadow-sm">
                  <step.icon className="size-4" />
                </div>
                <span className="text-xs font-semibold tracking-wider">{step.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Filters & Search */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
          <div className="flex items-center gap-1 overflow-x-auto pb-2 sm:pb-0 hide-scrollbar">
            {['ALL', 'PAID', 'PENDING_PAYMENT', 'PROCESSING', 'SHIPPED', 'DELIVERED', 'CANCELLED'].map((filter) => (
              <button
                key={filter}
                onClick={() => setStatusFilter(filter)}
                className={`px-4 py-2 rounded-full text-xs font-semibold tracking-wider whitespace-nowrap transition-colors ${
                  statusFilter === filter 
                    ? 'bg-foreground text-background' 
                    : 'text-muted-foreground hover:bg-surface-raised hover:text-foreground'
                }`}
              >
                {filter} {filter === 'ALL' ? orders.length : orders.filter(o => o.status === filter).length || ''}
              </button>
            ))}
          </div>
          
          <div className="relative w-full sm:w-64 shrink-0">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
            <input 
              type="text" 
              placeholder="Search orders, products..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 rounded-full bg-surface border border-border text-sm focus:outline-none focus:ring-1 focus:ring-primary transition-all"
            />
          </div>
        </div>

        {/* Data Table */}
        <div className="border border-border rounded-xl bg-surface overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-border bg-background/50">
                  <th className="p-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider whitespace-nowrap">Order</th>
                  <th className="p-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider whitespace-nowrap">Agent</th>
                  <th className="p-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider min-w-[200px]">Product</th>
                  <th className="p-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider whitespace-nowrap">Merchant</th>
                  <th className="p-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider whitespace-nowrap text-right">Value</th>
                  <th className="p-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider whitespace-nowrap text-center">FINSHIELD</th>
                  <th className="p-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider whitespace-nowrap text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {orders.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="p-8 text-center text-muted-foreground">
                      No activity yet.
                    </td>
                  </tr>
                ) : orders.map((order) => {
                  const agent = agents.find(a => a.id === order.agent_id);
                  const finshieldDecision = order.metadata?.finshield_decision || 'ALLOW';
                  const isBlock = finshieldDecision === 'BLOCK';
                  const isReview = finshieldDecision === 'REVIEW';
                  
                  return (
                    <tr 
                      key={order.id} 
                      onClick={() => setSelectedOrderId(order.id)}
                      className="hover:bg-surface-raised cursor-pointer transition-colors group"
                    >
                      {/* Order ID */}
                      <td className="p-4 align-top">
                        <div className="flex items-center gap-2">
                          {!isBlock && !isReview && order.status !== 'CANCELLED' && <CheckCircle2 className="size-4 text-safe" />}
                          {isReview && <ShieldAlert className="size-4 text-warn" />}
                          {isBlock && <XCircle className="size-4 text-danger" />}
                          {order.status === 'CANCELLED' && !isBlock && <RotateCcw className="size-4 text-muted-foreground" />}
                          <span className="font-mono text-sm font-medium">{order.id}</span>
                        </div>
                      </td>
                      
                      {/* Agent */}
                      <td className="p-4 align-top">
                        <div className="text-sm font-medium">{agent?.name || 'Unknown Agent'}</div>
                        <div className="text-xs text-muted-foreground font-mono mt-1">{order.agent_id}</div>
                      </td>

                      {/* Product */}
                      <td className="p-4 align-top">
                        <div className="text-sm font-medium">{order.items?.[0]?.product?.name || 'Unknown Product'}</div>
                        <div className="text-xs text-muted-foreground mt-1 truncate max-w-[200px]" title={order.items?.[0]?.product?.description}>
                          {order.items?.[0]?.product?.description || 'N/A'}
                        </div>
                      </td>
                      
                      {/* Merchant */}
                      <td className="p-4 align-top">
                        <div className="text-sm">{order.items?.[0]?.merchant_name_snapshot || 'Unknown Merchant'}</div>
                      </td>
                      
                      {/* Value */}
                      <td className="p-4 align-top text-right">
                        <div className="text-sm font-medium whitespace-nowrap">
                          {formatCurrency(order.total, order.currency)}
                        </div>
                      </td>
                      
                      {/* Finshield */}
                      <td className="p-4 align-top">
                        <div className="flex justify-center">
                          <div className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-bold tracking-wider ${
                            isBlock ? 'bg-danger/10 text-danger border border-danger/20' : 
                            isReview ? 'bg-warn/10 text-warn border border-warn/20' : 
                            'bg-safe/10 text-safe border border-safe/20'
                          }`}>
                            {isBlock ? 'BLOCKED' : isReview ? 'REVIEW' : 'ALLOW'}
                          </div>
                        </div>
                      </td>

                      {/* Fulfillment Status */}
                      <td className="p-4 align-top text-right">
                        <div className={`text-sm font-bold tracking-wide ${
                          order.status === 'CANCELLED' ? 'text-muted-foreground' : 'text-foreground'
                        }`}>
                          {order.status.replace(/_/g, ' ')}
                        </div>
                        <div className="text-xs text-muted-foreground mt-1">
                          {new Date(order.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>

      </div>

      {/* Order Details Drawer */}
      {selectedOrder && (
        <>
          <div 
            className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40 animate-in fade-in duration-200"
            onClick={() => setSelectedOrderId(null)}
          />
          <OrderDetailsDrawer 
            order={selectedOrder} 
            onClose={() => setSelectedOrderId(null)} 
          />
        </>
      )}

    </div>
  );
}
