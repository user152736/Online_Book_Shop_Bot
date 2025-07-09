from aiogram import Router

from bot.admins import admin_router
from bot.baskets import order_router
from bot.baskets.basket import basket_router
from bot.handlers import main_router
from bot.inlinemode import inline_router

router = Router()

router.include_routers(
    admin_router,
    main_router,
    inline_router,
    basket_router,
    order_router,
)
