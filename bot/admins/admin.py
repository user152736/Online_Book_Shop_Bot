import os

from aiogram import F, Router, Bot
from aiogram.enums import ChatType
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ReplyKeyboardRemove, Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.filters.is_admin import ChatTypeFilter, IsAdmin
from bot.keyboards import show_category, admin_buttons
from db.models import Category, Product

admin_router = Router()
admin_router.message.filter(ChatTypeFilter([ChatType.PRIVATE]), IsAdmin())

MEDIA_DIRECTORY = './media'
os.makedirs(MEDIA_DIRECTORY, exist_ok=True)


class FormAdministrator(StatesGroup):
    product_title = State()
    product_image = State()
    product_description = State()
    product_price = State()
    product_discount_price = State()
    product_quantity = State()
    product_category = State()
    category_name = State()
    show_category = State()
    product_delete = State()
    category_delete = State()
    social_link = State()


@admin_router.message(CommandStart())
async def start_for_admin(message: Message):
    await message.answer(
        f'<i> Assalomu aleykum </i> <b> {message.from_user.full_name} </b> 🫡 Tanlovingiz <tg-spoiler>ADMIN</tg-spoiler> ❕',
        reply_markup=admin_buttons())


@admin_router.message(F.text == '📚 Kitoblar')
async def books_handler(message: Message) -> None:
    await message.answer('Categoriyalardan birini tanlang 👇🏻', reply_markup=await show_category(message.from_user.id))


@admin_router.message(F.text == 'Category ➕')
async def add_category(message: Message, state: FSMContext):
    await state.set_state(FormAdministrator.category_name)
    await message.answer('Category nomini kiriting 👇🏻', reply_markup=ReplyKeyboardRemove())


@admin_router.message(FormAdministrator.category_name)
async def add_category(message: Message, state: FSMContext) -> None:
    category_name = message.text.strip()

    if category_name.isdigit() or not category_name:
        await message.answer(
            "Category nomi faqat harflardan iborat bo'lishi kerak, raqamlar bo'lmasligi kerak. Iltimos, qayta kiritib ko'ring:",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(FormAdministrator.category_name)
        return
    await Category.create(name=category_name)
    await state.clear()
    await message.answer("Category Bazaga Saqlandi ✅", reply_markup=admin_buttons())


@admin_router.message(F.text == 'Product ➕')
async def add_product(message: Message, state: FSMContext):
    await state.set_state(FormAdministrator.product_title)
    await message.answer('Product nomini kiriting 👇🏻', reply_markup=ReplyKeyboardRemove())


@admin_router.message(FormAdministrator.product_title)
async def add_product_title(message: Message, state: FSMContext):
    await state.update_data(product_title=message.text)
    await state.set_state(FormAdministrator.product_image)
    await message.answer("Product 🖼 rasmini jo'nating 👇🏻")


@admin_router.message(FormAdministrator.product_image)
async def add_product_image(message: Message, state: FSMContext, bot: Bot):
    try:
        file = await bot.get_file(message.photo[-1].file_id)
        file_name = f"{file.file_unique_id}.jpg"
        file_path = os.path.join(MEDIA_DIRECTORY, file_name)
        await bot.download_file(file.file_path, file_path)
        await state.update_data(product_image=file_path)
        await state.set_state(FormAdministrator.product_description)
        await message.answer("Product 📝 description kiriting 👇🏻")
    except Exception as e:
        await message.answer(f"Xatolik yuz berdi Imageni yuklay olmadim: {str(e)}")


@admin_router.message(FormAdministrator.product_description)
async def add_product_description(message: Message, state: FSMContext):
    await state.update_data(product_description=message.text)
    await state.set_state(FormAdministrator.product_price)
    await message.answer("Product narxini kiriting 💸 👇🏻")


@admin_router.message(FormAdministrator.product_price)
async def add_product_price(message: Message, state: FSMContext):
    await state.update_data(product_price=float(message.text))
    await state.set_state(FormAdministrator.product_discount_price)
    await message.answer("Product 🏷 chegirma narxini 💸 kiriting 👇🏻")


@admin_router.message(FormAdministrator.product_discount_price)
async def add_product_discount_price(message: Message, state: FSMContext):
    await state.update_data(product_discount_price=float(message.text))
    await state.set_state(FormAdministrator.product_quantity)
    await message.answer('Productlar sonini kiriting (7️⃣ 👇🏻)')


@admin_router.message(FormAdministrator.product_quantity)
async def add_product_quantity(message: Message, state: FSMContext):
    await state.update_data(product_quantity=int(message.text))
    await state.set_state(FormAdministrator.product_category)
    categories = await Category.get_all()
    ikb = InlineKeyboardBuilder()
    for category in categories:
        ikb.add(
            InlineKeyboardButton(
                text=category.name,
                callback_data=str(category.id)
            )
        )
    ikb.adjust(2, repeat=True)
    await message.answer('Categoryni tanlang 👇🏻', reply_markup=ikb.as_markup())


@admin_router.callback_query(FormAdministrator.product_category)
async def add_product_category(callback: CallbackQuery, state: FSMContext):
    categories = await Category.get_all()
    category_ids = [category.id for category in categories]

    if int(callback.data) not in category_ids:
        await callback.answer('Category tanlashda xatolik Mavjud ‼️')
        return

    data = await state.get_data()
    await Product.create(
        title=data['product_title'],
        image=data['product_image'],
        description=data['product_description'],
        price=float(data['product_price']),
        discount_price=float(data['product_discount_price']),
        quantity=int(data['product_quantity']),
        category_id=int(callback.data),
    )

    await state.clear()
    await callback.message.delete()
    await callback.message.answer('Saqlandi ✅', reply_markup=admin_buttons())


@admin_router.message(F.text == "Product ➖ (🗑 o'chirish)")
async def show_products_for_deletion(message: Message, state: FSMContext) -> None:
    products = await Product.get_all()

    if not products:
        await message.answer("Hozirda hech qanday product mavjud emas.")
        return

    ikb = InlineKeyboardBuilder()
    ikb.row(*[InlineKeyboardButton(text=product.title, callback_data=str(product.id)) for product in products])
    ikb.adjust(2, 2)

    await message.answer("O'chirilishi kerak bo'lgan productni tanlang 👇🏻", reply_markup=ikb.as_markup())
    await state.set_state(FormAdministrator.product_delete)


@admin_router.callback_query(FormAdministrator.product_delete)
async def delete_product(callback: CallbackQuery, state: FSMContext) -> None:
    product_id = int(callback.data)

    product = await Product.get(id_=product_id)
    if product:
        await Product.delete(id_=product_id)
        await callback.message.delete()
        await callback.message.answer(
            f"Product '{product.title}' muvaffaqiyatli o'chirildi ✅",
            reply_markup=admin_buttons()
        )
    else:
        await callback.answer("Bunday product mavjud emas yoki allaqachon o'chirilgan!")

    await state.clear()


@admin_router.message(F.text == "Category ➖ (🗑 o'chirish)")
async def category_delete(message: Message, state: FSMContext) -> None:
    categories = await Category.get_all()
    if not categories:
        await message.answer("Categorylar mavjud emas !!!")
        return

    ikb = InlineKeyboardBuilder()
    for category in categories:
        ikb.add(
            InlineKeyboardButton(
                text=category.name,
                callback_data=str(category.id)
            )
        )
    await message.answer("Category tanlang 👇🏻", reply_markup=ikb.as_markup())
    await state.set_state(FormAdministrator.category_delete)


@admin_router.callback_query(FormAdministrator.category_delete)
async def category_delete(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        category_id = int(callback.data)
        await Category.delete(id_=category_id)
        await callback.message.delete()
        await callback.message.answer(
            text="Category va unga tegishli productlar o'chirildi ✅",
            reply_markup=admin_buttons()
        )
    except ValueError:
        await callback.answer("Category ID noto'g'ri formatda!")
    except Exception as e:
        await callback.answer(f"Xatolik yuz berdi: {e}")
    finally:
        await state.clear()
