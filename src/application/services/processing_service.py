import asyncio
import random

from domain.enums import PaymentStatus


class PaymentGatewaySimulator:
    async def process(self) -> tuple[PaymentStatus, str | None]:
        await asyncio.sleep(random.uniform(2, 5))
        if random.random() <= 0.9:
            return PaymentStatus.SUCCEEDED, None
        return PaymentStatus.FAILED, "Gateway processing failed"
