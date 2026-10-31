import { createFileRoute } from '@tanstack/react-router';
import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { commerceApi, Product, Order, Cart } from '@/api/commerce';
import { paymentsApi } from '@/api/payments';
import { agentRuntimeApi } from '@/api/agent_runtime';
import { agentsApi } from '@/api/agents';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ShoppingCart, Package, Store, CreditCard, ChevronRight, ShieldCheck } from 'lucide-react';
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { formatCurrency } from '@/lib/utils';

export const Route = createFileRoute('/app/commerce/')({
  component: CommercePage,
});

function CommercePage() {
  const [activeTab, setActiveTab] = useState('products');
  const [activeCartId, setActiveCartId] = useState<string | null>(() => {
    return localStorage.getItem('finshield_sandbox_cart_id') || null;
  });

  useEffect(() => {
    if (activeCartId) {
      localStorage.setItem('finshield_sandbox_cart_id', activeCartId);
    } else {
      localStorage.removeItem('finshield_sandbox_cart_id');
    }
  }, [activeCartId]);
  
  return (
    <div className="flex-1 space-y-4 p-8 pt-6">
      <div className="flex items-center justify-between space-y-2">
        <h2 className="text-3xl font-bold tracking-tight">Commerce Sandbox</h2>
        <div className="flex items-center space-x-2">
           <Button variant="outline" onClick={() => setActiveTab('cart')}>
             <ShoppingCart className="mr-2 h-4 w-4" />
             View Cart
           </Button>
        </div>
      </div>
      
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="products">
            <Store className="mr-2 h-4 w-4" />
            Products
          </TabsTrigger>
          <TabsTrigger value="cart">
            <ShoppingCart className="mr-2 h-4 w-4" />
            Active Cart
          </TabsTrigger>
          <TabsTrigger value="orders">
            <Package className="mr-2 h-4 w-4" />
            Orders
          </TabsTrigger>
        </TabsList>
        
        <TabsContent value="products" className="space-y-4">
          <ProductsTab activeCartId={activeCartId} setActiveCartId={setActiveCartId} />
        </TabsContent>
        
        <TabsContent value="cart" className="space-y-4">
          <CartTab activeCartId={activeCartId} setActiveCartId={setActiveCartId} setActiveTab={setActiveTab} />
        </TabsContent>
        
        <TabsContent value="orders" className="space-y-4">
          <OrdersTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function ProductsTab({ activeCartId, setActiveCartId }: { activeCartId: string | null, setActiveCartId: (id: string) => void }) {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');
  
  const { data: products, isLoading } = useQuery({
    queryKey: ['products'],
    queryFn: commerceApi.products.list,
  });

  const { data: cart } = useQuery({
    queryKey: ['cart', activeCartId],
    queryFn: () => activeCartId ? commerceApi.carts.get(activeCartId) : Promise.resolve(null),
    enabled: !!activeCartId,
  });

  const addToCartMutation = useMutation({
    mutationFn: async (productId: string) => {
      let cartId = activeCartId;
      if (!cartId) {
        const newCart = await commerceApi.carts.create();
        cartId = newCart.id;
        setActiveCartId(cartId);
      }
      const item = await commerceApi.carts.addItem(cartId, productId, 1);
      return { cartId, item };
    },
    onSuccess: (data) => {
      toast.success('Product added to your cart.');
      queryClient.invalidateQueries({ queryKey: ['cart', data.cartId] });
    },
    onError: (err) => {
      toast.error('Could not add to cart.');
    }
  });

  if (isLoading) return <div>Loading products...</div>;

  const filteredProducts = (products || []).filter(p => 
    p.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
    p.description?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-4">
      <div className="flex w-full max-w-sm items-center space-x-2">
         <input 
            type="text" 
            placeholder="Search products..." 
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
         />
      </div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {products?.length === 0 ? (
         <Card className="col-span-full">
           <CardContent className="flex flex-col items-center justify-center h-40">
              <p className="text-muted-foreground mb-4">No products available in sandbox.</p>
           </CardContent>
         </Card>
      ) : (
        filteredProducts.map(product => (
          <Card key={product.id}>
            <CardHeader>
              <CardTitle>{product.name}</CardTitle>
              <CardDescription>
                {product.category || 'General'}
                {product.sku && <span className="ml-2 text-xs opacity-50">SKU: {product.sku}</span>}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{formatCurrency(product.price, product.currency)}</p>
              <p className="text-sm text-muted-foreground mt-2">{product.description}</p>
              <p className="text-xs text-muted-foreground mt-4">Stock: {product.inventory}</p>
            </CardContent>
            <CardFooter>
              <Button 
                className="w-full" 
                onClick={() => addToCartMutation.mutate(product.id)}
                disabled={addToCartMutation.isPending}
              >
                {cart?.items.find(i => i.product_id === product.id) 
                  ? `Add more (${cart.items.find(i => i.product_id === product.id)?.quantity} in cart)` 
                  : 'Add to Cart'}
              </Button>
            </CardFooter>
          </Card>
        ))
      )}
      </div>
    </div>
  );
}

function CartTab({ activeCartId, setActiveCartId, setActiveTab }: { activeCartId: string | null, setActiveCartId: (id: string | null) => void, setActiveTab: (tab: string) => void }) {
  const queryClient = useQueryClient();

  const { data: cart, isLoading } = useQuery({
    queryKey: ['cart', activeCartId],
    queryFn: () => activeCartId ? commerceApi.carts.get(activeCartId) : Promise.resolve(null),
    enabled: !!activeCartId,
  });

  const checkoutMutation = useMutation({
    mutationFn: async () => {
      if (!cart || cart.items.length === 0) throw new Error("Cart is empty");
      
      const merchantId = cart.items[0].product?.merchant_id;
      if (!merchantId) throw new Error("Could not determine merchant for cart items");

      const order = await commerceApi.orders.create(cart.id, merchantId);
      return order;
    },
    onSuccess: (order) => {
      toast.success(`Order created successfully.`);
      setActiveCartId(null);
      queryClient.invalidateQueries({ queryKey: ['orders'] });
      setActiveTab('orders');
    },
    onError: (err: any) => {
      if (err.response?.status === 402) {
         toast.error('Transaction Intercepted: Action requires human approval.', { duration: 10000 });
      } else if (err.response?.status === 403) {
         toast.error('Transaction Blocked: ' + (err.response?.data?.detail || 'Policy Block'), { duration: 10000 });
      } else {
         toast.error(err.response?.data?.detail || err.message || 'Could not checkout');
      }
    }
  });

  const updateQuantityMutation = useMutation({
    mutationFn: async ({ itemId, quantity }: { itemId: string, quantity: number }) => {
      if (!cart) return;
      if (quantity <= 0) {
        await commerceApi.carts.removeItem(cart.id, itemId);
      } else {
        await commerceApi.carts.updateItem(cart.id, itemId, quantity);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cart', activeCartId] });
    },
    onError: (err: any) => {
      toast.error(err.message || 'Could not update cart item');
    }
  });

  if (!activeCartId) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center h-64">
          <ShoppingCart className="h-12 w-12 text-muted-foreground mb-4 opacity-20" />
          <p className="text-muted-foreground text-lg">Your cart is empty.</p>
        </CardContent>
      </Card>
    );
  }

  if (isLoading || !cart) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center h-64">
          <p className="text-muted-foreground">Loading cart...</p>
        </CardContent>
      </Card>
    );
  }

  const subtotal = (cart.items || []).reduce((acc, item) => acc + item.total, 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Sandbox Cart</CardTitle>
        <CardDescription>{cart.id}</CardDescription>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[300px] rounded-md border p-4">
          {(cart.items || []).map((item, i) => (
             <div key={item.id}>
                {i > 0 && <Separator className="my-4" />}
                 <div className="flex items-center justify-between">
                   <div>
                      <p className="font-medium">{item.product?.name || 'Unknown Product'}</p>
                      <div className="flex items-center mt-1 space-x-2">
                        <Button variant="outline" size="icon" className="h-6 w-6" onClick={() => updateQuantityMutation.mutate({ itemId: item.id, quantity: item.quantity - 1 })}>-</Button>
                        <span className="text-sm">Qty: {item.quantity}</span>
                        <Button variant="outline" size="icon" className="h-6 w-6" onClick={() => updateQuantityMutation.mutate({ itemId: item.id, quantity: item.quantity + 1 })}>+</Button>
                      </div>
                   </div>
                   <div className="font-medium">
                      {formatCurrency(item.total, cart.currency)}
                   </div>
                </div>
             </div>
          ))}
        </ScrollArea>
        <div className="flex justify-between items-center mt-6">
           <span className="text-lg font-bold">Total</span>
           <span className="text-2xl font-bold">{formatCurrency(subtotal, cart.currency)}</span>
        </div>
      </CardContent>
      <CardFooter>
        <Button 
          className="w-full" 
          size="lg" 
          onClick={() => checkoutMutation.mutate()}
          disabled={checkoutMutation.isPending || cart.items.length === 0}
        >
          {checkoutMutation.isPending ? 'Processing...' : 'Checkout'}
        </Button>
      </CardFooter>
    </Card>
  );
}

function OrdersTab() {
  const queryClient = useQueryClient();
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);

  const { data: orders, isLoading } = useQuery({
    queryKey: ['orders'],
    queryFn: commerceApi.orders.list,
  });

  const payMutation = useMutation({
    mutationFn: async (order: Order) => {
      // 1. Create Payment Intent
      const intent = await paymentsApi.createIntent({
         payment_intent_id: `pi_sb_${Math.random().toString(36).substr(2, 9)}`,
         idempotency_key: `idem_${Math.random().toString(36).substr(2, 9)}`,
         amount: order.total,
         currency: order.currency,
         order_id: order.id,
         payment_method_type: 'sandbox_card'
      });
      // 2. Authorize
      await paymentsApi.authorize(intent.id);
      // 3. Capture
      const captured = await paymentsApi.capture(intent.id);
      return captured;
    },
    onSuccess: () => {
      toast.success('Order has been paid securely.');
      queryClient.invalidateQueries({ queryKey: ['orders'] });
    },
    onError: (err: any) => {
      toast.error(err.message);
      queryClient.invalidateQueries({ queryKey: ['orders'] });
    }
  });

  if (isLoading) return <div>Loading orders...</div>;

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Order History</CardTitle>
        </CardHeader>
        <CardContent>
           <ScrollArea className="h-[500px] pr-4">
              <div className="space-y-4">
                 {orders?.map(order => (
                    <div 
                      key={order.id} 
                      className={`p-4 rounded-lg border cursor-pointer transition-colors ${selectedOrder?.id === order.id ? 'border-primary bg-primary/5' : 'hover:bg-muted/50'}`}
                      onClick={() => setSelectedOrder(order)}
                    >
                       <div className="flex justify-between items-start mb-2">
                          <p className="font-semibold">{order.id.slice(0, 13)}...</p>
                          <Badge variant={order.status === 'PAID' ? 'default' : order.status === 'PENDING_PAYMENT' ? 'outline' : 'secondary'}>
                            {order.status}
                          </Badge>
                       </div>
                       <div className="flex justify-between items-center text-sm text-muted-foreground">
                          <span>{new Date(order.created_at).toLocaleDateString()}</span>
                          <span className="font-medium text-foreground">{formatCurrency(order.total, order.currency)}</span>
                       </div>
                    </div>
                 ))}
                 {orders?.length === 0 && (
                    <p className="text-center text-muted-foreground py-8">No orders yet.</p>
                 )}
              </div>
           </ScrollArea>
        </CardContent>
      </Card>

      {selectedOrder ? (
        <Card>
          <CardHeader>
            <CardTitle>Order Details</CardTitle>
            <CardDescription>{selectedOrder.id}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
              <div>
                <h4 className="font-medium mb-2">Items</h4>
                <div className="space-y-2">
                   {(selectedOrder.items || []).map(item => (
                      <div key={item.id} className="flex justify-between text-sm">
                         <span>{item.quantity}x {item.product_name_snapshot || item.product?.name || item.product_id}</span>
                         <span>{formatCurrency(item.total, selectedOrder.currency)}</span>
                      </div>
                   ))}
                </div>
                <Separator className="my-4" />
                <div className="flex justify-between font-bold">
                   <span>Total</span>
                   <span>{formatCurrency(selectedOrder.total, selectedOrder.currency)}</span>
                </div>
                {selectedOrder.agent_id && (
                  <div className="mt-4 text-sm text-muted-foreground">
                    Purchased by Agent: <span className="font-mono bg-muted px-1 py-0.5 rounded">{selectedOrder.agent_id}</span>
                  </div>
                )}
             </div>

             {selectedOrder.status === 'PENDING_PAYMENT' && (
                <div className="pt-4">
                  {selectedOrder.agent_id ? (
                    <div className="p-3 rounded-lg bg-surface border border-border text-xs text-muted-foreground flex items-center gap-2">
                      <ShieldCheck className="h-4 w-4 text-primary shrink-0" />
                      <div>
                        <span className="font-semibold text-foreground">Action Gate Governed: </span>
                        Agent-initiated orders cannot be paid directly. Review and approve in Approval Center.
                      </div>
                    </div>
                  ) : (
                    <Button 
                       className="w-full" 
                       onClick={() => payMutation.mutate(selectedOrder)}
                       disabled={payMutation.isPending}
                    >
                       <CreditCard className="mr-2 h-4 w-4" />
                       {payMutation.isPending ? 'Processing Payment...' : 'Pay Now (Sandbox)'}
                    </Button>
                  )}
                </div>
             )}
          </CardContent>
        </Card>
      ) : (
        <Card className="flex items-center justify-center h-[200px] text-muted-foreground">
           Select an order to view details
        </Card>
      )}
    </div>
  );
}
