from datetime import datetime

import pytz
import sqlalchemy
from sqlalchemy import delete as sqlalchemy_delete, update as sqlalchemy_update, select, func, BigInteger, and_
from sqlalchemy.ext.asyncio import AsyncAttrs, create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, declared_attr, sessionmaker, Mapped, mapped_column, selectinload
from sqlalchemy.types import TypeDecorator, DateTime

from config import conf


class Base(AsyncAttrs, DeclarativeBase):

    @declared_attr
    def __tablename__(self) -> str:
        __name = self.__name__[:1]
        for i in self.__name__[1:]:
            if i.isupper():
                __name += '_'
            __name += i
        __name = __name.lower()

        if __name.endswith('y'):
            __name = __name[:-1] + 'ie'
        return __name + 's'


class AsyncDatabaseSession:
    def __init__(self):
        self._session = None
        self._engine = None

    def __getattr__(self, name):
        return getattr(self._session, name)

    def init(self):
        self._engine = create_async_engine(
            conf.db.db_url
        )
        self._session = sessionmaker(self._engine, expire_on_commit=False, class_=AsyncSession)()

    async def create_all(self):
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_all(self):
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)


db = AsyncDatabaseSession()
db.init()


class AbstractClass:
    @staticmethod
    async def commit():
        try:
            await db.commit()
        except Exception:
            await db.rollback()
            raise

    @classmethod
    async def create(cls, **kwargs):
        object_ = cls(**kwargs)
        db.add(object_)
        await cls.commit()
        return object_

    @classmethod
    async def update(cls, id_=None, telegram_id=None, **kwargs):
        if id_:
            query = (
                sqlalchemy_update(cls)
                .where(cls.id == id_)
                .values(**kwargs)
                .execution_options(synchronize_session="fetch")
            )
        else:
            query = (
                sqlalchemy_update(cls)
                .where(cls.telegram_id == telegram_id)
                .values(**kwargs)
                .execution_options(synchronize_session="fetch")
            )
        await db.execute(query)
        await cls.commit()

    @classmethod
    async def get(cls, id_=None, user_telegram_id=None):
        if id_:
            query = select(cls).where(cls.id == id_)
            return (await db.execute(query)).scalar()
        else:
            query = select(cls).where(cls.user_telegram_id == user_telegram_id)
            return (await db.execute(query)).scalars()

    @classmethod
    async def get_products_by_user(cls, user_id, order_id=None):
        async with db._session as session:
            if user_id and order_id:
                query = (
                    sqlalchemy.select(cls)
                    .options(selectinload(cls.product))
                    .where(cls.user_telegram_id == user_id, cls.order_id == order_id)
                )
            else:
                query = (
                    sqlalchemy.select(cls)
                    .options(selectinload(cls.product))
                    .where(cls.user_telegram_id == user_id)
                )
            result = await session.execute(query)
            return result.scalars().all()

    @classmethod
    async def get_with_telegram_id(cls, telegram_id):
        query = select(cls).where(cls.telegram_id == telegram_id)
        return (await db.execute(query)).scalar()

    @classmethod
    async def delete(cls, id_=None, user_telegram_id=None):
        if id_:
            query = sqlalchemy_delete(cls).where(cls.id == id_)
        else:
            query = sqlalchemy_delete(cls).where(cls.user_telegram_id == user_telegram_id)
        await db.execute(query)
        await cls.commit()

    @classmethod
    async def count_grouped_by_user_telegram_id(cls, user_telegram_id):
        query = (
            sqlalchemy.select(sqlalchemy.func.count(sqlalchemy.distinct(cls.product_id)))
            .where(cls.user_telegram_id == user_telegram_id)
            .group_by(cls.user_telegram_id)
        )
        async with db._session as session:
            result = await session.execute(query)
            count = result.scalar_one_or_none()
        return count if count else 0

    @classmethod
    async def get_all(cls):
        return (await db.execute(select(cls))).scalars()

    @classmethod
    async def is_admin(cls, telegram_id):
        query = select(cls).where(
            and_(cls.telegram_id == telegram_id, cls.type == "ADMIN")
        )

        return (await db.execute(query)).scalars().first()

    @classmethod
    async def get_name(cls, id_: int):
        query = select(cls).where(cls.id == id_)
        result = await db.execute(query)
        instance = result.scalars().first()

        if instance:
            return instance.name
        return None


class BaseModel(Base, AbstractClass):
    __abstract__ = True
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    def __str__(self):
        return f"{self.id}"


class TimeStamp(TypeDecorator):
    impl = DateTime(timezone=True)
    cache_ok = True
    TASHKENT_TIMEZONE = pytz.timezone("Asia/Tashkent")

    def process_bind_param(self, value: datetime, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            value = self.TASHKENT_TIMEZONE.localize(value)
        return value.astimezone(self.TASHKENT_TIMEZONE)

    def process_result_value(self, value, dialect):
        if value is not None:
            return value.astimezone(self.TASHKENT_TIMEZONE)
        return value


class TimeBaseModel(BaseModel):
    __abstract__ = True
    created_at: Mapped[TimeStamp] = mapped_column(TimeStamp, server_default=func.now())
    updated_at: Mapped[TimeStamp] = mapped_column(TimeStamp, server_default=func.now(), server_onupdate=func.now())
