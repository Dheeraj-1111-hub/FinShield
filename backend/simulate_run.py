import asyncio
from app.db.database import get_db
from app.services.agent_runtime_service import AgentRuntimeService
from sqlalchemy import text

async def simulate_run():
    db_gen = get_db()
    db = await anext(db_gen)
    
    workspace_id = 'wksp_2651f13f5284'
    run_id = 'run_9940a183cd7642dd'
    
    try:
        print('1. Search products')
        try:
            await AgentRuntimeService.execute_action(db, workspace_id, run_id, 'search_products', {'query': 'laptop', 'category': 'electronics'})
        except Exception as e:
            print(f'Search error: {e}')
            
        print('2. Create cart')
        try:
            res_cart = await AgentRuntimeService.execute_action(db, workspace_id, run_id, 'create_cart', {})
            cart_id = res_cart.output['cart_id']
            print(f'Cart created: {cart_id}')
        except Exception as e:
            print(f'Cart error: {e}')
            return
            
        print('3. Add to cart')
        try:
            res_prod = await db.execute(text('SELECT id FROM products LIMIT 1'))
            prod_id = res_prod.scalar_one()
            
            await db.execute(text(f'UPDATE products SET price = 75000 WHERE id = "{prod_id}"'))
            await db.commit()
            
            await AgentRuntimeService.execute_action(db, workspace_id, run_id, 'add_to_cart', {'cart_id': cart_id, 'product_id': prod_id, 'quantity': 1})
            
            print('Added to cart and updated product price to 75000.')
        except Exception as e:
            print(f'Add to cart error: {e}')
            return
            
        print('4. Checkout')
        try:
            await AgentRuntimeService.execute_action(db, workspace_id, run_id, 'checkout', {'cart_id': cart_id})
        except Exception as e:
            print(f'Checkout result (should be 402 REVIEW): {e}')
            
    finally:
        await db.close()

asyncio.run(simulate_run())
