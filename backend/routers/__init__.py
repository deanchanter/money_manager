from .transactions import router as transactions_router
from .categories import router as categories_router
from .budgets import router as budgets_router
from .savings_goals import router as savings_goals_router
from .analytics import router as analytics_router
from .import_export import router as import_export_router
from .accounts import router as accounts_router
from .simplefin import router as simplefin_router

__all__ = [
    "transactions_router",
    "categories_router",
    "budgets_router",
    "savings_goals_router",
    "analytics_router",
    "import_export_router",
    "accounts_router",
    "simplefin_router"
]
