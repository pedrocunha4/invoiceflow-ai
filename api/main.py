from __future__ import annotations

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles

from api.routes.dashboard import router as dashboard_router
from api.routes.general import router as general_router
from api.routes.invoices import router as invoices_router
from api.routes.processing import router as processing_router

app = FastAPI(
    title="InvoiceFlow AI API",
    description="API for intelligent invoice processing and automation.",
    version="0.1.0",
    docs_url=None,
)


# ---------------------------------------------------------
# Static files
# ---------------------------------------------------------

app.mount(
    "/icon",
    StaticFiles(directory="api/icon"),
    name="icon",
)


# ---------------------------------------------------------
# Custom Swagger UI
# ---------------------------------------------------------

@app.get(
    "/docs",
    include_in_schema=False,
)
def custom_swagger_ui():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title="InvoiceFlow AI API",
        swagger_favicon_url="/icon/favicon.png",
    )


# ---------------------------------------------------------
# API routers
# ---------------------------------------------------------

app.include_router(general_router)
app.include_router(dashboard_router)
app.include_router(invoices_router)
app.include_router(processing_router)