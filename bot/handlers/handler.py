from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, CallbackQuery
from aiogram.types import Message, FSInputFile
from aiogram.utils.i18n import gettext as _, lazy_gettext as __
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards import show_category, main_buttons, lang_commands, \
    main_links_buttons, make_plus_minus
from bot.states.count_state import CountState
from db import Product, Category
from db.models import User

main_router = Router()


@main_router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    msg = _('Assalomu alaykum! Tanlovingiz 👇🏻.')
    user_data = message.from_user.model_dump(include={'id', 'first_name', 'last_name', 'username'})
    if not await User.get_with_telegram_id(telegram_id=message.from_user.id):
        await User.create(
            first_name=user_data['first_name'],
            last_name=user_data['last_name'],
            username=user_data['username'],
            telegram_id=user_data['id']
        )
        msg = _('Assalomu alaykum! \nXush kelibsiz!')
    await message.answer(text=msg, reply_markup=main_buttons())


@main_router.message(Command(commands='help'))
async def command_help_handler(message: Message) -> None:
    await message.answer(_('''Buyruqlar:
/start - Botni ishga tushirish 🫡
/help - Yordam 📖
/language - Tilni almashtirish 🔄'''))


@main_router.message(F.text == __('🌐 Tilni almshtirish'))
async def change_language(message: Message) -> None:
    await message.answer(_('Tilni tanlang  👇🏻'), reply_markup=lang_commands())


@main_router.message(Command(commands='language'))
async def language_handler(message: Message) -> None:
    await change_language(message)


@main_router.callback_query(F.data.startswith('lang_'))
async def languages(callback: CallbackQuery, state: FSMContext) -> None:
    lang_code = callback.data.split('lang_')[-1]
    await state.update_data(locale=lang_code)
    lang_map = {
        'uz': _('Uzbek', locale=lang_code),
        'en': _('English', locale=lang_code),
        'tur': _('Turk', locale=lang_code),
        'ru': _('Rus', locale=lang_code),
        'ko': _('Korean', locale=lang_code),
    }
    current_lang = lang_map.get(lang_code, _('Til', locale=lang_code))
    await callback.answer(_('{lang} tili tanlandi', locale=lang_code).format(lang=current_lang))
    msg = _('Assalomu alaykum! Tanlang.', locale=lang_code)
    await callback.message.answer(text=msg, reply_markup=main_buttons(locale=lang_code))


@main_router.message(F.text == __("🔵 Biz ijtimoyi tarmoqlarda"))
async def social_handler(message: Message) -> None:
    await message.answer('Biz ijtimoiy tarmoqlarda', reply_markup=main_links_buttons())


@main_router.message(F.text == __("📚 Kitoblar"))
async def books_handler(message: Message) -> None:
    await message.answer(_('Categoriyalardan birini tanlang 👇🏻'),
                         reply_markup=await show_category(message.from_user.id))


@main_router.callback_query(F.data.startswith('orqaga'))
async def back_handler(callback: CallbackQuery):
    await callback.message.edit_text(_('Categoriyalardan birini tanlang 👇🏻'),
                                     reply_markup=await show_category(callback.from_user.id))


@main_router.message(F.text == __("📞 Biz bilan bog'lanish"))
async def contact_us_handler(message: Message) -> None:
    text = _(
        """
        \n
        \n
        Telegram: @Mexmonjonovuz\n
        📞  +{number}\n
        🤖 Bot Mexmonjon Asadbek @Mexmonjonovuz tomonidan tayorlandi.\n
        """
    ).format(number=998901209552)
    await message.answer(text=text, parse_mode=ParseMode.HTML)


@main_router.callback_query(F.data.startswith('category_name_'))
async def category_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CountState.count)
    await state.update_data(count=1)
    category_id = int(callback.data.split('category_name_')[-1])
    categories = await Category.get_all()
    category = next((cat for cat in categories if cat.id == category_id), None)
    if category is None:
        await callback.message.edit_text(text="Categoriya topilmadi!", reply_markup=None)
        return
    products = await Product.get_products_by_category_id(category_id=category_id)
    ikb = InlineKeyboardBuilder()
    for product in products:
        ikb.add(InlineKeyboardButton(text=product.title, callback_data=f"product_name_{product.id}"))
    ikb.add(InlineKeyboardButton(text=_("◀️ orqaga"), callback_data='orqaga'))
    ikb.adjust(2, repeat=True)
    await callback.message.edit_text(text=f"{category.name}", reply_markup=ikb.as_markup())


@main_router.callback_query(F.data.startswith('product_name_'))
async def product_handler(callback: CallbackQuery):
    product_id = int(callback.data.split('product_name_')[-1])
    product = await Product.get(product_id)
    ikb = make_plus_minus(1, str(product.id))
    await callback.message.delete()
    await callback.message.answer_photo(photo=FSInputFile(product.image), caption=product.description,
                                        reply_markup=ikb.as_markup())
