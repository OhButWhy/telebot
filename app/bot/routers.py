"""Aggregates the per-domain routers into a single one.

Order matters: aiogram resolves handlers in inclusion order, so menu text
handlers must stay ahead of the state-scoped text handlers.
"""
from aiogram import Router

from app.bot import (
    account,
    catalog,
    edit,
    materials,
    menu,
    mylists,
    profile,
    search,
    upload,
)

router = Router()
router.include_router(menu.router)
router.include_router(catalog.router)
router.include_router(profile.router)
router.include_router(upload.router)
router.include_router(search.router)
router.include_router(account.router)
router.include_router(materials.router)
router.include_router(edit.router)
router.include_router(mylists.router)
