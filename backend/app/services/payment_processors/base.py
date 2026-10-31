from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional
from app.models.payment import Payment

class PaymentProcessor(ABC):
    
    @abstractmethod
    async def authorize(self, payment: Payment) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Authorize the payment.
        Returns: (success, failure_code, failure_reason)
        """
        pass

    @abstractmethod
    async def capture(self, payment: Payment) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Capture a previously authorized payment.
        Returns: (success, failure_code, failure_reason)
        """
        pass

    @abstractmethod
    async def cancel(self, payment: Payment) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Cancel a payment.
        Returns: (success, failure_code, failure_reason)
        """
        pass
