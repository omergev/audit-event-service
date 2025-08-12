# alembic/env.py

import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# -- Logging config --
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# -- Import application's SQLAlchemy Base for autogenerate support --
# Try common locations; fallback to None if not available.
try:
    from app.models import Base as AppBase
except Exception:
    try:
        from app.database import Base as AppBase
    except Exception:
        AppBase = None

# Alembic uses target_metadata for autogenerate diffs. It's OK to be None if not used.
target_metadata = getattr(AppBase, "metadata", None)

# -- Resolve SQLAlchemy URL at runtime --
# Prefer DATABASE_URL from env, otherwise try app.config.DATABASE_URL.
try:
    from app.config import DATABASE_URL as APP_DATABASE_URL
except Exception:
    APP_DATABASE_URL = None

url = os.getenv("DATABASE_URL", APP_DATABASE_URL or "")
# Normalize driver to psycopg3 if URL is PostgreSQL without explicit driver.
if url.startswith("postgresql://"):
    url = url.replace("postgresql://", "postgresql+psycopg://", 1)

if url:
    config.set_main_option("sqlalchemy.url", url)

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
