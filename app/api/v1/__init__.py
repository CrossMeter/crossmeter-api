from fastapi import APIRouter
from .payment_intents import router as payment_intents_router
from .subscriptions import router as subscriptions_router
from .webhooks import router as webhooks_router
from .router import router as router_router
from .vendors import router as vendors_router
from .products import router as products_router
from .analytics import router as analytics_router

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

# Vendor management endpoints
api_router.include_router(
    vendors_router,
    prefix="/vendors",
    tags=["vendors"]
)

# Product management endpoints (nested under vendors)
api_router.include_router(
    products_router,
    prefix="/vendors",
    tags=["products"]
)

# Analytics endpoints (nested under vendors)
api_router.include_router(
    analytics_router,
    prefix="/vendors",
    tags=["analytics"]
)
