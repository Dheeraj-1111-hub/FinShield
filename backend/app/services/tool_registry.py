from typing import Dict, Any, Callable, Type
from pydantic import BaseModel, Field

class ToolDefinition(BaseModel):
    name: str
    description: str
    required_capabilities: list[str]
    input_schema: Type[BaseModel]

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._handlers: Dict[str, Callable] = {}

    def register_tool(self, definition: ToolDefinition, handler: Callable):
        self._tools[definition.name] = definition
        self._handlers[definition.name] = handler

    def get_tool(self, name: str) -> ToolDefinition:
        if name not in self._tools:
            raise ValueError(f"Tool {name} not found in registry")
        return self._tools[name]
        
    def get_handler(self, name: str) -> Callable:
        if name not in self._handlers:
            raise ValueError(f"Handler for tool {name} not found")
        return self._handlers[name]
        
    def list_tools(self) -> list[ToolDefinition]:
        return list(self._tools.values())

# Global registry
registry = ToolRegistry()

# ----------------- Tool Schemas -----------------
class SearchProductsInput(BaseModel):
    query: str = Field(description="Search query for products")
    category: str | None = Field(default=None, description="Category filter")
    min_price: int | None = Field(default=None, description="Minimum price")
    max_price: int | None = Field(default=None, description="Maximum price")

class CreateCartInput(BaseModel):
    pass

class AddToCartInput(BaseModel):
    cart_id: str = Field(description="The ID of the cart")
    product_id: str = Field(description="The ID of the product to add")
    quantity: int = Field(default=1, description="Quantity to add")

class CheckoutInput(BaseModel):
    cart_id: str = Field(description="The ID of the cart to checkout")

class PayOrderInput(BaseModel):
    order_id: str = Field(description="The ID of the order to pay")

# ----------------- Register Tools -----------------

registry.register_tool(
    ToolDefinition(
        name="search_products",
        description="Search for products available from merchants",
        required_capabilities=["SEARCH_PRODUCTS"],
        input_schema=SearchProductsInput
    ),
    handler=None # Handlers will be mapped in the service layer where DB session is available
)

registry.register_tool(
    ToolDefinition(
        name="create_cart",
        description="Create a new shopping cart",
        required_capabilities=["CREATE_CART"],
        input_schema=CreateCartInput
    ),
    handler=None
)

registry.register_tool(
    ToolDefinition(
        name="add_to_cart",
        description="Add a product to an existing cart",
        required_capabilities=["MANAGE_CART"],
        input_schema=AddToCartInput
    ),
    handler=None
)

registry.register_tool(
    ToolDefinition(
        name="checkout",
        description="Checkout a cart to create an order",
        required_capabilities=["CREATE_ORDER"],
        input_schema=CheckoutInput
    ),
    handler=None
)

registry.register_tool(
    ToolDefinition(
        name="pay_order",
        description="Pay for an order",
        required_capabilities=["PAY_ORDER"],
        input_schema=PayOrderInput
    ),
    handler=None
)
