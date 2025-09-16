from datetime import datetime
from sqlalchemy import select
from schemas.database import DUser, DVisitedUser, new_session

class Repo:
    @classmethod
    async def select_pass(cls, login, psw, tg_id):
        """authorization"""
        async with new_session() as session:
            q = select(DUser).where(DUser.login == login, DUser.password == psw,
                                    DUser.tg_id == str(tg_id))
            result = await session.execute(q)
            answer = result.scalar()
            return answer

    @classmethod
    async def insert_into_visited_date(cls, login, action):
        """enter into database if three unsuccessful attempts of authorization"""
        async with new_session() as session:
            date_created = datetime.now()
            q = DVisitedUser(login=str(login), date_created=date_created, action=action)
            session.add(q)
            await session.commit()
            await session.close()
