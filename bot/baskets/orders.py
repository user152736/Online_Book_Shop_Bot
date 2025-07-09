from aiogram import F, Router, Bot
from aiogram.enums import ContentType, ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, InlineKeyboardButton, ReplyKeyboardMarkup, \
    KeyboardButton, Message, InlineKeyboardMarkup
from aiogram.utils.i18n import gettext as _, lazy_gettext as __
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.baskets import to_category, basket_msg
from bot.config import ADMIN_LIST
from bot.keyboards import main_buttons
from db import Basket, User, Order, Product
from db.models import OrderItem

order_router = Router()


class BasketState(StatesGroup):
    phone_number = State()


async def order_message(user_id):
    all_sum = 0
    msg = ''
    orders = await Order.get(user_telegram_id=user_id)
    for order in orders:
        msg += _(
            '🔢 Buyurtma raqami: <b>{order_id}</b>\n'
            '📆 Buyurtma qilingan sana: <b>{date_time}</b>\n'
            '🟣 Buyurtma holati: <b>{order_status}</b>\n\n').format(
            order_id=order.id,
            date_time=str(order.created_at.strftime('%Y-%m-%d %H:%M:%S')),
            order_status=order.order_status.value
        )
        order_items = await OrderItem.get_products_by_user(user_id=order.user_telegram_id, order_id=order.id)
        i = 1
        summa = 0
        for item in order_items:
            summa += int(item.quantity) * int(item.product.price)
            msg += f'\n{i}. 📕 Kitob nomi: {item.product.title} \n{item.quantity} x {item.product.price} = {str(int(item.quantity) * int(item.product.price))} sum\n\n'
            i += 1
        all_sum += summa
        msg += '~~~~~~~~~~~~~~~~~~~~~~~~~\n'
    msg += f'\n💸 Umumiy narxi: {all_sum} sum'
    return msg


async def clear_users_basket(user_telegram_id):
    await Basket.delete(user_telegram_id=user_telegram_id)


@order_router.callback_query(F.data.startswith('clear'))
async def clear(callback: CallbackQuery):
    await clear_users_basket(callback.from_user.id)
    await to_category(callback)


@order_router.callback_query(F.data.endswith('confirm'))
async def confirm(callback: CallbackQuery, state: FSMContext):
    rkb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=_('📞 Telefon raqam'), request_contact=True)]], resize_keyboard=True)
    await callback.message.delete()
    await callback.message.answer(
        _('Telefon raqamingizni qoldiring (📞 Telefon raqam tugmasini bosing): 👇🏻'),
        reply_markup=rkb
    )

    await state.set_state(BasketState.phone_number)
    await callback.answer(
        _('📞 Raqamingiz qabul qilindi. Tashakkur!'),
        reply_markup=main_buttons()
    )


@order_router.message(F.content_type == ContentType.CONTACT, BasketState.phone_number)
async def phone_number(message: Message, state: FSMContext):
    await state.update_data(phone_number=message.contact.phone_number)
    phone_number = (await state.get_data())['phone_number'][1:]
    user = await User.get_with_telegram_id(telegram_id=message.from_user.id)
    if user:
        await User.update(phone_number=phone_number, telegram_id=message.from_user.id)
        await message.answer(
            _('📞 Raqamingiz qabul qilindi. Tashakkur!'),
            reply_markup=main_buttons()
        )
    if not message.contact:
        await message.answer(_("Telefon raqamingizni olishda xatolik yuz berdi. Iltimos, qayta urinib ko'ring."))
        return

    msg = f"{await basket_msg(message.from_user.id)}\nTelefon raqamingiz: {message.contact.phone_number}\n\n<i>Buyurtma berasizmi?</i>"
    ikb = InlineKeyboardBuilder()
    ikb.row(
        InlineKeyboardButton(text=_("❌ Yo'q"), callback_data='canceled_order'),
        InlineKeyboardButton(text=_('✅ Ha'),
                             callback_data=f'confirm_order_{int(message.from_user.id)}_{message.contact.phone_number}')
    )

    await message.answer(msg, reply_markup=ikb.as_markup())
    await state.clear()


@order_router.callback_query(F.data.endswith('canceled_order'))
async def canceled_order(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(_('❌ Bekor qilindi'), reply_markup=main_buttons())


@order_router.callback_query(F.data.startswith('confirm_order'))
async def confirm_order(callback: CallbackQuery, bot: Bot):
    summa = 0
    msg = ''
    total_amount = float(callback.message.text.split("Jami: ")[-1].split()[0])
    phone_number = callback.data.split("_")[-1]
    user_id = callback.data.split("_")[-2]
    order = await Order.create(
        user_telegram_id=callback.from_user.id,
        phone_number=phone_number,
        total_amount=total_amount
    )
    baskets = await Basket.get(user_telegram_id=callback.from_user.id)
    for orderitem in baskets:
        await OrderItem.create(
            quantity=orderitem.quantity,
            order_id=order.id,
            user_telegram_id=orderitem.user_telegram_id,
            product_id=orderitem.product_id,

        )
    msg += _(
        '🔢 Buyurtma raqami: <b>{order_id}</b>\n'
        '📆 Buyurtma qilingan sana: <b>{date_time}</b>\n'
        '🟣 Buyurtma holati: <b>{order_status}</b>\n\n').format(
        order_id=order.id,
        date_time=str(order.created_at.strftime('%Y-%m-%d %H:%M:%S')),
        order_status=order.order_status.value
    )
    order_items = await OrderItem.get_products_by_user(user_id=order.user_telegram_id, order_id=order.id)
    i = 1
    for item in order_items:
        summa += int(item.quantity) * int(item.product.price)
        msg += f'\n{i}. 📕 Kitob nomi: {item.product.title} \n{item.quantity} x {item.product.price} = {str(int(item.quantity) * int(item.product.price))} sum\n\n'
        i += 1
    msg += '~~~~~~~~~~~~~~~~~~~~~~~~~\n'
    msg += f'\n💸 Umumiy narxi: {summa} sum'
    user_telegram_id = callback.from_user.id
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=_("❌ Yo'q"),
                callback_data=f'from_admin_canceled_order-{user_telegram_id}-{user_id}-{order.id}'
            ),
            InlineKeyboardButton(
                text=_('✅ Ha'),
                callback_data=f'from_admin_order_accept-{user_telegram_id}-{user_id}-{order.id}'
            )
        ]
    ])

    user_full_name = callback.from_user.full_name or _("Foydalanuvchi")

    if not ADMIN_LIST:
        await callback.message.answer(_("Admin list is empty; unable to notify admin."))
        return

    try:
        await bot.send_message(
            ADMIN_LIST[0],
            msg +
            f"\n\nKlient: {callback.data[12:].replace('r_', '')} <a href='tg://user?id={callback.from_user.id}'>{user_full_name}</a>\nBuyurtmani qabul qilasizmi?",
            parse_mode=ParseMode.HTML,
            reply_markup=ikb
        )
    except TelegramBadRequest as e:
        print(f"Error sending message: {e}")

    await callback.message.answer(
        _('✅ Hurmatli mijoz! Buyurtmangiz uchun tashakkur.\nBuyurtma raqami: {orders_num}').format(
            orders_num=order.id
        ),
        reply_markup=main_buttons()
    )

    await clear_users_basket(callback.from_user.id)


@order_router.callback_query(F.data.startswith('from_admin'))
async def order_accept_canceled(callback: CallbackQuery, bot: Bot):
    order_id = int(callback.data.split('-')[-1])
    user_telegram_id = int(callback.data.split('-')[-2])
    order = (await Order.get(id_=order_id))
    if callback.data.startswith('from_admin_order_accept'):
        for item in await OrderItem.get_products_by_user(user_id=order.user_telegram_id, order_id=order_id):
            product_quantity = (await Product.get(id_=item.product_id)).quantity
            await Product.update(
                id_=item.product_id,
                quantity=(product_quantity - item.quantity)
            )

        await bot.send_message(chat_id=user_telegram_id,
                               text=('<i>🎉 Sizning {order_num} raqamli buyurtmangizni admin qabul qildi.</i>').format(
                                   order_num=order_id))

        await callback.message.edit_reply_markup()
    elif callback.data.startswith('from_admin_canceled_order'):
        await bot.send_message(chat_id=callback.message.chat.id,
                               text=(
                                   '<i>❌ Sizning {order_num} raqamli buyurtmangizni admin Tomonidan bekor qilindi !!!.</i>').format(
                                   order_num=order_id))
    else:
        await callback.message.delete()


@order_router.message(F.text == __('📃 Mening buyurtmalarim'))
async def my_orders(message: Message):
    user_telegram_id = message.from_user.id
    orders = await Order.get(user_telegram_id=user_telegram_id)
    if not orders:
        await message.answer(_('🤷‍♂️ Sizda hali buyurtmalar mavjud emas. Yoki bekor qilingan'))
    else:
        await message.answer(await order_message(user_telegram_id))
