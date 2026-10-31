import asyncio
from typing import Tuple, Optional
from app.models.payment import Payment
from app.services.payment_processors.base import PaymentProcessor

class SandboxPaymentProcessor(PaymentProcessor):
    
    async def authorize(self, payment: Payment) -> Tuple[bool, Optional[str], Optional[str]]:
        # Simulate network latency
        await asyncio.sleep(0.5)
        
        # Deterministic failure conditions based on amount
        if payment.amount == 99999900: # ₹999,999.00
            return False, "insufficient_funds", "The simulated card has insufficient funds."
        if payment.amount == 5000000: # ₹50,000.00
            return False, "expired_payment_method", "The simulated card has expired."
        if payment.amount == 100000: # ₹1,000.00
            return False, "processor_decline", "The transaction was declined by the processor."

        return True, None, None

    async def capture(self, payment: Payment) -> Tuple[bool, Optional[str], Optional[str]]:
        await asyncio.sleep(0.3)
        return True, None, None

    async def cancel(self, payment: Payment) -> Tuple[bool, Optional[str], Optional[str]]:
        await asyncio.sleep(0.1)
        return True, None, None
