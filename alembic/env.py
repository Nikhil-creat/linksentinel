"""Async Alembic environment bound to the app's models and DATABASE_URL."""
import asyncio
from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from app.models.orm import Base

def run(conn):
    context.configure(connection=conn, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()

async def main():
    eng = create_async_engine(settings.database_url)
    async with eng.connect() as c:
        await c.run_sync(run)
    await eng.dispose()

asyncio.run(main())
