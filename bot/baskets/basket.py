from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.i18n import gettext as _
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards import show_category, make_plus_minus
from bot.states.count_state import CountState
from db import Basket, Product

basket_router = Router()

quantity = 1


async def basket_msg(user_id):
    msg = f'🛒 Savat \n\n'
    all_sum = 0
    for basket in (await Basket.get_products_by_user(user_id)):
        summa = float(basket.quantity) * float(basket.product.price)
        msg += f"<i>{basket.product.title}</i> \n{basket.quantity} x {basket.product.price} = {str(summa)} sum\n\n"
        all_sum += summa
    msg += _("<b>Jami: {all_sum} sum</b>").format(all_sum=all_sum)
    return msg


@basket_router.callback_query(F.data.startswith('categoryga'))
async def to_category(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(_('Categoriyalardan birini tanlang 👇🏻'),
                                  reply_markup=await show_category(callback.from_user.id))


@basket_router.callback_query(F.data.startswith('add_to_card_'))
async def to_basket(callback: CallbackQuery):
    product_id = int(callback.data.split('_')[-2])
    quantity = int(callback.data.split('_')[-1])

    product = await Product.get(id_=product_id)
    await Basket.create(
        product_id=product_id,
        quantity=quantity,
        user_telegram_id=callback.from_user.id
    )
    await to_category(callback)


@basket_router.callback_query((F.data.startswith('change-')) | (F.data.startswith('change+')), CountState.count)
async def update_page_handler(callback: CallbackQuery, state: FSMContext):
    data = (await state.get_data())
    if callback.data.startswith("change-"):
        if data['count'] > 1:
            data['count'] -= 1
            await state.update_data(count=data['count'])
        else:
            await callback.answer(_('Eng kamida 1 ta kitob buyurtma qilishingiz mumkin! 😊'), show_alert=True)
            return
    else:
        product = await Product.get(id_=int(callback.data.split('+')[-1]))
        if product.quantity <= data['count']:
            await callback.answer(_('Ayni vaqtda bu kitobdan shuncha {product_count} miqdorda mavjud! 😊').format(
                product_count=data['count']), show_alert=True)
            return
        else:
            data['count'] += 1
            await state.update_data(count=data['count'])
    ikb = make_plus_minus(data['count'], callback.data[7:])
    await callback.message.edit_reply_markup(str(callback.message.message_id), reply_markup=ikb.as_markup())


@basket_router.callback_query(F.data.startswith('savat'))
async def basket(callback: CallbackQuery):
    msg = await basket_msg(callback.from_user.id)
    ikb = InlineKeyboardBuilder()
    ikb.row(InlineKeyboardButton(text=_('❌ Savatni tozalash'), callback_data='clear'))
    ikb.row(InlineKeyboardButton(text=_('✅ Buyurtmani tasdiqlash'), callback_data='confirm'))
    ikb.row(InlineKeyboardButton(text=_('◀️ orqaga'), callback_data='categoryga'))
    await callback.message.edit_text(msg, reply_markup=ikb.as_markup(), parse_mode=ParseMode.HTML)
