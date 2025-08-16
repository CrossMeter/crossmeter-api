from fastapi import APIRouter
from .payment_intents import router as payment_intents_router
from .subscriptions import router as subscriptions_router
from .webhooks import router as webhooks_router
from .router import router as router_router

api_router = APIRouter()

# Include all route modules
api_router.include_router(
    payment_intents_router,
    prefix="/payment_intents",
    tags=["payment-intents"]
)

api_router.include_router(
    subscriptions_router,
    prefix="/subscriptions",
    tags=["subscriptions"]
)

api_router.include_router(
    webhooks_router,
    prefix="/webhooks",
    tags=["webhooks"]
)

api_router.include_router(
    router_router,
    prefix="/router",
    tags=["router"]
)
