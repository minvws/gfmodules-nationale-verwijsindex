import inject

from app import application, container, dependencies
from app.config import Config

if __name__ == "__main__":
    container.configure()

    config = inject.instance(Config)
    application.setup_logging(config)

    db = dependencies.get_database()
    db.generate_tables()
