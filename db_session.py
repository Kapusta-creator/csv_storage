import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.orm import Session
import sqlalchemy.ext.declarative as dec

SQLAlchemyBase = dec.declarative_base()

__factory = None


def global_init(db_file):
    global __factory
    if __factory:
        return
    if not db_file.strip():
        raise Exception("Необходимо указать файл базы данных")
    #            тип БД       имя файла БД
    conn_str = f'sqlite:///{db_file.strip()}?check_same_thread=False'
    engine = sa.create_engine(conn_str, echo=False)
    __factory = orm.sessionmaker(bind=engine)

    SQLAlchemyBase.metadata.create_all(engine)


def create_session() -> Session:
    global __factory
    return __factory()
