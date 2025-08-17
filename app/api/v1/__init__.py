from fastapi import APIRouter
from .payment_intents import router as payment_intents_router
from .subscriptions import router as subscriptions_router
from .webhooks import router as webhooks_router
from .router import router as router_router
from .vendors import router as vendors_router
from .products import router as products_router
from .analytics import router as analytics_router
from .auth import router as auth_router
from .client import router as client_router
from .users import router as users_router

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

# User management endpoints
api_router.include_router(
    users_router,
    prefix="/users",
    tags=["users"]
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

# Authentication endpoints
api_router.include_router(
    auth_router,
    prefix="/auth",
    tags=["authentication"]
)

# Client API endpoints (API key authentication)
api_router.include_router(
    client_router,
    prefix="/client",
    tags=["client-api"]
)
