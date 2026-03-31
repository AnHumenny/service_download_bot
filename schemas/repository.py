from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError
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
    async def insert_into_visited_date(cls, login, action, file_unique_id):
        """enter into database if three unsuccessful attempts of authorization"""
        async with new_session() as session:
            date_created = datetime.now()
            q = DVisitedUser(login=str(login), date_created=date_created,
                             action=action, hash_name=file_unique_id)
            session.add(q)
            await session.commit()


    @classmethod
    async def find_duplicate_hash_names(cls) -> List[Dict[str, Any]]:
        """
        Search all duplicates names hash_name in tables _visited_users.
        Return list of dict with information about duplicates.
        """
        async with new_session() as session:
            try:
                stmt = select(
                    DVisitedUser.hash_name,
                    func.count(DVisitedUser.hash_name).label('count')
                ).group_by(
                    DVisitedUser.hash_name
                ).having(
                    func.count(DVisitedUser.hash_name) > 1
                )

                result = await session.execute(stmt)
                duplicates = result.all()

                if not duplicates:
                    return []

                duplicate_details = []
                for hash_name, count in duplicates:
                    detail_stmt = select(DVisitedUser).where(
                        DVisitedUser.hash_name == hash_name
                    ).order_by(DVisitedUser.date_created.desc())

                    detail_result = await session.execute(detail_stmt)
                    records = detail_result.scalars().all()

                    duplicate_details.append({
                        'hash_name': hash_name,
                        'count': count,
                        'records': [
                            {
                                'login': record.login,
                                'date_created': record.date_created,
                                'action': record.action,
                                'hash_name': record.hash_name
                            }
                            for record in records
                        ]
                    })

                return duplicate_details

            except SQLAlchemyError as e:
                print(f"Error finding duplicates: {e}")
                raise

    @classmethod
    async def find_duplicates_by_hash(cls, hash_name: str) -> List[DVisitedUser]:
        """
        Finds all records with the specified hash_name.
        """
        async with new_session() as session:
            try:
                stmt = select(DVisitedUser).where(
                    DVisitedUser.hash_name == hash_name
                ).order_by(DVisitedUser.date_created.desc())

                result = await session.execute(stmt)
                return result.scalars().all()

            except SQLAlchemyError as e:
                print(f"Error finding records by hash: {e}")
                raise

    @classmethod
    async def get_all_visited_records(cls, limit: int = 100) -> List[DVisitedUser]:
        """
        Get last records from table _visited_users.
        """
        async with new_session() as session:
            try:
                stmt = select(DVisitedUser).order_by(
                    DVisitedUser.date_created.desc()
                ).limit(limit)

                result = await session.execute(stmt)
                return result.scalars().all()

            except SQLAlchemyError as e:
                print(f"Error getting records: {e}")
                raise

    @classmethod
    async def get_duplicate_statistics(cls) -> Dict[str, Any]:
        """
        Return duplicates statistic.
        """
        async with new_session() as session:
            try:
                total_stmt = select(func.count()).select_from(DVisitedUser)
                total_result = await session.execute(total_stmt)
                total_records = total_result.scalar()

                unique_stmt = select(func.count(func.distinct(DVisitedUser.hash_name))).select_from(DVisitedUser)
                unique_result = await session.execute(unique_stmt)
                unique_hashes = unique_result.scalar()

                duplicate_stmt = select(
                    DVisitedUser.hash_name,
                    func.count(DVisitedUser.hash_name).label('count')
                ).group_by(
                    DVisitedUser.hash_name
                ).having(
                    func.count(DVisitedUser.hash_name) > 1
                )

                duplicate_result = await session.execute(duplicate_stmt)
                duplicates = duplicate_result.all()

                duplicate_count = len(duplicates)
                duplicate_records_count = sum([dup[1] for dup in duplicates])

                return {
                    'total_records': total_records,
                    'unique_hashes': unique_hashes,
                    'duplicate_count': duplicate_count,
                    'duplicate_records_count': duplicate_records_count,
                    'duplicates': duplicates
                }

            except SQLAlchemyError as e:
                print(f"Error getting statistics: {e}")
                raise
