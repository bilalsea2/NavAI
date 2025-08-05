from aiogram import Dispatcher

from .start import router as start_router
from .survey import router as survey_router
from .admin import router as admin_router

def setup_routers(dp: Dispatcher):
    dp.include_router(start_router)
    dp.include_router(survey_router)
    dp.include_router(admin_router)