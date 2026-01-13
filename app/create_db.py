from app import application, container, dependencies

if __name__ == "__main__":
    container.configure()

    application.setup_logging()

    db = dependencies.get_database()
    db.generate_tables()
