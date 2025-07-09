from enum import Enum
from typing import List

from sqlalchemy import BigInteger, VARCHAR, Integer
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.future import select
from sqlalchemy.orm import mapped_column, Mapped, relationship

from db.base import TimeBaseModel
from db.base import db


class User(TimeBaseModel):
    class Type(Enum):
        USER = "user"
        ADMIN = "admin"
        SUPER_ADMIN = "super_admin"

    first_name: Mapped[str] = mapped_column(VARCHAR(255))
    last_name: Mapped[str] = mapped_column(VARCHAR(255), nullable=True)
    username: Mapped[str] = mapped_column(VARCHAR(255), nullable=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    phone_number: Mapped[str] = mapped_column(VARCHAR(255), nullable=True)
    type: Mapped[Type] = mapped_column(SQLEnum(Type), default=Type.USER)
    orders: Mapped[List['Order']] = relationship(back_populates='user', cascade="all, delete")
    baskets: Mapped[List['Basket']] = relationship(back_populates='user', cascade="all, delete")
    order_items: Mapped[List['OrderItem']] = relationship(back_populates='user', cascade="all, delete")


class Basket(TimeBaseModel):
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    user_telegram_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.telegram_id'))
    user: Mapped[List['User']] = relationship(back_populates="baskets", cascade="all, delete")
    product: Mapped[List['Product']] = relationship(back_populates="baskets", cascade="all, delete")
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('products.id'))


class Category(TimeBaseModel):
    name: Mapped[str] = mapped_column(VARCHAR(255))
    products: Mapped[list['Product']] = relationship('Product', back_populates='category')

    def __repr__(self):
        return self.name


class Product(TimeBaseModel):
    title: Mapped[str] = mapped_column(VARCHAR(255))
    image: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    price: Mapped[float] = mapped_column(Float())
    discount_price: Mapped[float] = mapped_column(Float(), default=0.0)
    quantity: Mapped[int] = mapped_column(BigInteger, default=0)
    category_id: Mapped[int] = mapped_column(BigInteger, ForeignKey(Category.id, ondelete='CASCADE'))
    category: Mapped['Category'] = relationship('Category', back_populates='products')
    baskets: Mapped[List['Basket']] = relationship(back_populates='product', cascade="all, delete")
    order_items: Mapped[List['OrderItem']] = relationship(back_populates='product', cascade="all, delete")

    @classmethod
    async def get_products_by_category_id(cls, category_id):
        query = select(cls).where(cls.category_id == category_id)
        return (await db.execute(query)).scalars()


class Order(TimeBaseModel):
    class Status(Enum):
        DELIVERING = "☑️ Yetqazilmoqda"
        DELIVERED = "✅ Yetqazilgan"
        PENDING = "🕐 Kutish holatida"
        RETURNED = "⬅️ Qaytarilgan"
        CANCELLED = "❌ Bekor qilingan"

    user_telegram_id: Mapped[int] = mapped_column(BigInteger,ForeignKey('users.telegram_id'), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    order_status: Mapped[Status] = mapped_column(
        SQLEnum(Status), default=Status.PENDING
    )
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    user: Mapped["User"] = relationship('User', back_populates='orders')
    order_items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="order", cascade="all, delete")


class OrderItem(TimeBaseModel):
    quantity: Mapped[int] = mapped_column(Integer, default=1)

    order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('orders.id'))
    order: Mapped["Order"] = relationship(back_populates='order_items', cascade="all, delete")

    user_telegram_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.telegram_id'))
    user: Mapped["User"] = relationship(back_populates="order_items", cascade="all, delete")

    product: Mapped["Product"] = relationship(back_populates="order_items", cascade="all, delete")
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('products.id'))
