import logging
from .core.logging import setup_logging

from contextlib import asynccontextmanager
import uvicorn

from fastapi import FastAPI, status
from .transport.api.v1.handler.expenses import router as expenses_router
from .transport.api.v1.handler.users import router as users_router


logger = logging.getLogger(__name__)
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Запуск приложения")
    yield
    logger.info("Остановка приложения")


app = FastAPI(
    lifespan=lifespan,
    title="SUAI",
    swagger_ui_parameters={"persistAuthorization": True},
)

app.include_router(users_router)
app.include_router(expenses_router)

@app.get("/_info", status_code=status.HTTP_200_OK)
async def info():
    return status.HTTP_200_OK


if __name__ == "__main__":
    uvicorn.run("app.main:app", reload=True)
