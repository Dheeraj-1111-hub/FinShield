import { useState } from "react";
import { 
  X, CheckCircle2, ShieldAlert, XCircle, ArrowRight, Activity, 
  Terminal, ShieldCheck, Box, Search, Package, MapPin, Target,
  FileCheck, MoreHorizontal, RotateCcw
} from "lucide-react";
import { Link } from "@tanstack/react-router";
import { Order } from "@/api/commerce";
import { Button } from "@/components/ui/button";

interface OrderDetailsDrawerProps {
  order: Order;
  onClose: () => void;
}

export function OrderDetailsDrawer({ order, onClose }: OrderDetailsDrawerProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'items'>('overview');
  
  const isCancelled = order.status === 'CANCELLED';
  const isPending = order.status === 'PENDING_PAYMENT' || order.status === 'DRAFT';
  const isPaid = order.status === 'PAID' || order.status === 'PROCESSING' || order.status === 'FULFILLED';
  
  const healthStatus = isCancelled ? 'CANCELLED' : isPending ? 'ATTENTION' : 'GOOD';

  return (
    <div className="absolute inset-y-0 right-0 w-[550px] bg-background border-l border-border shadow-2xl flex flex-col z-50 animate-in slide-in-from-right duration-300">
      
      {/* Drawer Header */}
      <div className="h-14 border-b border-border flex items-center justify-between px-5 bg-surface shrink-0">
        <div className="flex items-center gap-3">
          <div className="text-sm font-semibold text-muted-foreground flex items-center gap-2">
            <Button variant="ghost" size="icon" onClick={onClose} className="size-6 -ml-2 rounded-full">
              <ArrowRight className="size-3.5 rotate-180" />
            </Button>
            Orders
          </div>
          <span className="text-muted-foreground">/</span>
          <div className="font-mono text-sm font-bold">{order.id}</div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" className="size-8 rounded-full">
            <MoreHorizontal className="size-4" />
          </Button>
          <Button variant="ghost" size="icon" onClick={onClose} className="size-8 rounded-full">
            <X className="size-4" />
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar">
        
        {/* Hero Section */}
        <div className="p-6 border-b border-border">
          <div className="flex items-center gap-2 mb-4">
            <div className={`size-2.5 rounded-full ${
              healthStatus === 'GOOD' ? 'bg-safe shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 
              healthStatus === 'CANCELLED' ? 'bg-muted-foreground' : 'bg-warn shadow-[0_0_8px_rgba(245,158,11,0.5)]'
            }`} />
            <span className="text-xs font-semibold tracking-wider text-muted-foreground uppercase">
              {order.status.replace(/_/g, ' ')}
            </span>
          </div>
          
          <div className="text-3xl font-bold tracking-tight mb-2">
            {order.currency === 'INR' ? '₹' : (order.currency === 'USD' ? '$' : `${order.currency} `)}{order.total.toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </div>
          <div className="text-lg text-muted-foreground flex items-center justify-between">
            {order.items && order.items.length > 0 ? order.items[0].merchant_name_snapshot : 'Unknown Merchant'}
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-border bg-surface shrink-0 px-2 overflow-x-auto hide-scrollbar">
          {[
            { id: 'overview', label: 'Overview' },
            { id: 'items', label: 'Order Items' },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-4 py-3 text-sm font-semibold tracking-wide border-b-2 transition-colors whitespace-nowrap ${
                activeTab === tab.id 
                  ? 'border-foreground text-foreground' 
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="p-6">
          
          {/* OVERVIEW TAB */}
          {activeTab === 'overview' && (
            <div className="space-y-6">
              
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-background border border-border p-4 rounded-xl">
                  <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Agent</div>
                  <div className="flex items-center gap-2">
                    <Terminal className="size-4 text-primary" />
                    <span className="font-semibold">{order.agent_id ? order.agent_id : 'User Checkout'}</span>
                  </div>
                </div>
                <div className="bg-background border border-border p-4 rounded-xl">
                  <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Payment</div>
                  <div className="font-medium font-mono">{order.payment_id || 'N/A'}</div>
                  <div className={`text-xs font-semibold mt-1 ${isPaid ? 'text-safe' : 'text-warn'}`}>
                    {isPaid ? 'Captured' : 'Pending'}
                  </div>
                  {order.payment_id ? (
                    <Button variant="link" className="h-auto p-0 mt-3 text-xs text-primary" asChild>
                      <Link to="/app/payments">
                        View Payments →
                      </Link>
                    </Button>
                  ) : isPending && !order.agent_id ? (
                    <Button 
                      className="mt-3 w-full" 
                      onClick={async () => {
                        try {
                          await import("@/api/payments").then(m => m.paymentsApi.createIntent({
                            payment_intent_id: `pi_${crypto.randomUUID().replace(/-/g, '')}`,
                            idempotency_key: `idem_${crypto.randomUUID().replace(/-/g, '')}`,
                            order_id: order.id
                          }));
                          window.location.href = '/app/payments';
                        } catch (e) {
                          console.error("Failed to create payment", e);
                        }
                      }}
                    >
                      Pay Order
                    </Button>
                  ) : isPending && order.agent_id ? (
                    <div className="mt-3 p-2.5 rounded-lg bg-surface border border-border text-xs text-muted-foreground flex items-center gap-2">
                      <ShieldCheck className="size-4 text-primary shrink-0" />
                      <div>
                        <div className="font-semibold text-foreground">Action Gate Governed</div>
                        <div>Agent orders must be authorized via the Approval Center.</div>
                      </div>
                    </div>
                  ) : null}
                </div>
              </div>

            </div>
          )}

          {/* ITEMS TAB */}
          {activeTab === 'items' && (
            <div className="space-y-4">
              {(!order.items || order.items.length === 0) && (
                <div className="text-muted-foreground text-sm text-center py-8">
                  No items found for this order.
                </div>
              )}
              {order.items && order.items.map(item => (
                <div key={item.id} className="bg-background border border-border rounded-xl overflow-hidden p-4">
                  <div className="font-medium text-lg mb-1">{item.product_name_snapshot}</div>
                  <div className="flex items-center justify-between text-sm mt-4">
                    <span className="text-muted-foreground">Quantity</span>
                    <span className="font-medium">{item.quantity}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm mt-2">
                    <span className="text-muted-foreground">Unit Price</span>
                    <span className="font-medium">{order.currency === 'INR' ? '₹' : (order.currency === 'USD' ? '$' : `${order.currency} `)}{item.unit_price_at_order.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm mt-2 font-bold border-t border-border/50 pt-2">
                    <span>Total</span>
                    <span>{order.currency === 'INR' ? '₹' : (order.currency === 'USD' ? '$' : `${order.currency} `)}{item.total.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                  </div>
                </div>
              ))}
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
