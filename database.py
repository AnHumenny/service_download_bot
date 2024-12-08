from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv
load_dotenv()
import os

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
    login = Column(String(30))

class DUser(Model):
    __tablename__ = "_userbot"
    name = Column(String(30))
    status = Column(String(15))
    password = Column(String)
    phone = Column(String(14))
    email = Column(String(50))
    tg_id = Column(String(50))

class DVisitedUser(Model):
    __tablename__ = "_visited_users"
    date_created = Column(DateTime(timezone=False))
    action = Column(String(50))
