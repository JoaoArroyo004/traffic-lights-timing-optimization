from sqlmodel import SQLModel, create_engine, Session

SQL_FILE_NAME = "simulations.db"
SQLITE_URL = f"sqlite:///{SQL_FILE_NAME}"

engine = create_engine(SQLITE_URL, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session