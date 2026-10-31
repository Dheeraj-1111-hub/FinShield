import { api } from "@/lib/api-client";

export interface Merchant {
    id: string;
    workspace_id: string;
    name: string;
    description?: string;
    status: string;
    merchant_reference?: string;
    risk_metadata?: Record<string, any>;
    created_by?: string;
    created_at: string;
    updated_at: string;
}

export interface Product {
    id: string;
    merchant_id: string;
    name: string;
    description?: string;
    category?: string;
    price: number;
    currency: string;
    inventory: number;
    sku?: string;
    status: string;
    metadata?: Record<string, any>;
    created_at: string;
    updated_at: string;
}

export interface CartItem {
    id: string;
    cart_id: string;
    product_id: string;
    quantity: number;
    unit_price: number;
    total: number;
    product?: Product;
}

export interface Cart {
    id: string;
    workspace_id: string;
    agent_id?: string;
    status: string;
    currency: string;
    created_at: string;
    updated_at: string;
    items: CartItem[];
}

export interface OrderItem {
    id: string;
    order_id: string;
    product_id: string;
    product_name_snapshot: string;
    merchant_name_snapshot: string;
    quantity: number;
    unit_price_at_order: number;
    total: number;
    product?: Product;
}

export interface Order {
    id: string;
    workspace_id: string;
    agent_id?: string;
    cart_id?: string;
    merchant_id: string;
    payment_id?: string;
    status: string;
    currency: string;
    subtotal: number;
    total: number;
    metadata?: Record<string, any>;
    created_at: string;
    updated_at: string;
    items: OrderItem[];
}

export const commerceApi = {
    merchants: {
        list: () => api.get<Merchant[]>('/commerce/merchants').then(res => res.data),
        create: (data: Partial<Merchant>) => api.post<Merchant>('/commerce/merchants', data).then(res => res.data),
    },
    products: {
        list: () => api.get<Product[]>('/commerce/products').then(res => res.data),
        create: (data: Partial<Product>) => api.post<Product>('/commerce/products', data).then(res => res.data),
        get: (id: string) => api.get<Product>(`/commerce/products/${id}`).then(res => res.data),
    },
    carts: {
        create: (data: Partial<Cart> = {}) => api.post<Cart>('/commerce/carts', data).then(res => res.data),
        get: (id: string) => api.get<Cart>(`/commerce/carts/${id}`).then(res => res.data),
        addItem: (cartId: string, productId: string, quantity: number = 1) => 
            api.post<CartItem>(`/commerce/carts/${cartId}/items`, { product_id: productId, quantity }).then(res => res.data),
        updateItem: (cartId: string, itemId: string, quantity: number) => 
            api.patch<CartItem>(`/commerce/carts/${cartId}/items/${itemId}`, { quantity }).then(res => res.data),
        removeItem: (cartId: string, itemId: string) => 
            api.delete(`/commerce/carts/${cartId}/items/${itemId}`).then(res => res.data),
    },
    orders: {
        list: () => api.get<Order[]>('/commerce/orders').then(res => res.data),
        create: (cartId: string, merchantId: string, agentId?: string) => 
            api.post<Order>('/commerce/orders', { cart_id: cartId, merchant_id: merchantId, agent_id: agentId }).then(res => res.data),
        get: (id: string) => api.get<Order>(`/commerce/orders/${id}`).then(res => res.data),
        cancel: (id: string) => api.post<Order>(`/commerce/orders/${id}/cancel`).then(res => res.data),
        process: (id: string) => api.post<Order>(`/commerce/orders/${id}/process`).then(res => res.data),
        fulfill: (id: string) => api.post<Order>(`/commerce/orders/${id}/fulfill`).then(res => res.data),
    }
};
