import os
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv
load_dotenv()


host = os.getenv('host')
port = os.getenv('port')
user = os.getenv('user')
password = os.getenv('password')
database = os.getenv('database')

DATABASE_URL = f"postgresql+asyncpg://{user}:{password}@{host}/{database}"

engine = create_async_engine(url=DATABASE_URL)
new_session = async_sessionmaker(engine, expire_on_commit=False)

class Model(DeclarativeBase):
    id = Column(Integer, primary_key=True, autoincrement=True)


class DUser(Model):
    __tablename__ = "_userbot"
    login = Column(String(30), unique=True, index=True)
    name = Column(String(30))
    status = Column(String(15))
    password = Column(String(100))
    phone = Column(String(14))
    email = Column(String(50), unique=True)
    tg_id = Column(String(50), unique=True)


class DVisitedUser(Model):
    __tablename__ = "_visited_users"
    login = Column(String(30))
    date_created = Column(DateTime(timezone=True))
    action = Column(String(200))
    hash_name = Column(String(200), index=True)
