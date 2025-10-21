import os
from sqlalchemy import engine_from_config, pool
from alembic import context
from models_module2 import Base

config = context.config
sqlalchemy_url = os.environ.get("DATABASE_URL", "postgresql://localhost/soeurise_dev")
config.set_main_option("sqlalchemy.url", sqlalchemy_url)

def run_migrations_online():
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = os.environ.get("DATABASE_URL", configuration.get("sqlalchemy.url"))
    connectable = engine_from_config(configuration, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()

run_migrations_online()
