from datetime import datetime
from sqlalchemy import select
from database import DUser, DVisitedUser, new_session

class Repo:
    @classmethod
    async def select_pass(cls, login, psw, tg_id):
        print(psw,"\n")
        async with new_session() as session:
            tg_id = str(tg_id)
            pswrd = psw.decode("UTF-8")
            password = str(pswrd)
            q = select(DUser).where(DUser.login == login, DUser.password == password,
                                    DUser.tg_id == tg_id)
            result = await session.execute(q)
            answer = result.scalar()
            await session.close()
            return answer

    @classmethod
    async def insert_into_visited_date(cls, login, action):
        async with new_session() as session:
            date_created = datetime.now()
            q = DVisitedUser(login=login, date_created=date_created, action=action)
            session.add(q)
            await session.commit()
            await session.close()