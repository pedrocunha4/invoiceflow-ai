from __future__ import annotations

from fastapi import APIRouter


router = APIRouter()


@router.get("/")
def root():
    return {
        "message": "InvoiceFlow AI API is running",
        "status": "ok",
    }


@router.get("/health")
def health_check():
    return {
        "status": "healthy",
    }