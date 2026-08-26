import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

API_TOKEN = "8909435935:AAHQbmRPwisHka6HI9LoXiobHUoESPkL3EY"
ADMIN_ID = 1890042054  
CHANNEL_USERNAME = "@Doniyorbek_math"  # Shu yerga kanalingiz usernamesini yozing (masalan: @statfutbol)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

tests = {}      # {test_code: {name, answers, photo_id}}
results = {}    # {test_code: [{name, score, total, percent}, ...]}
users = {}      # {user_id: full_name}

class Form(StatesGroup):
    waiting_for_name = State()
    waiting_for_test_code = State()
    waiting_for_test_name = State()
    waiting_for_photo = State()
    waiting_for_answers = State()

# Kanalga obuna bo'lganini tekshirish funksiyasi
async def check_sub(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ["creator", "administrator", "member"]:
            return True
        return False
    except Exception as e:
        logging.error(f"Obuna tekshirishda xatolik: {e}")
        return True  # Kanal sozlanmagan bo'lsa, xatolik bermay o'tkazib yuboradi

def get_sub_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_subscription")]
    ])
    return keyboard

@dp.message(Command("start"))
async def start_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    
    # Obunani tekshirish (Admin bundan mustasno)
    if user_id != ADMIN_ID:
        is_sub = await check_sub(user_id)
        if not is_sub:
            await message.answer(
                f"⚠️ **Botdan foydalanish uchun avval rasmiy kanalimizga obuna bo'ling!**",
                reply_markup=get_sub_keyboard(),
                parse_mode="Markdown"
            )
            return

    if user_id not in users:
        await message.answer("Assalomu alaykum! Botdan foydalanish uchun Ism va Familiyangizni kiriting:\n(Masalan: Mamazokirov Doniyorbek)")
        await state.set_state(Form.waiting_for_name)
    else:
        await send_main_menu(message)

# Obuna tugmasini bosganda tekshirish
@dp.callback_query(F.data == "check_subscription")
async def callback_check_sub(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    is_sub = await check_sub(user_id)
    
    if is_sub:
        await call.message.delete()
        await call.message.answer("✅ Obuna tasdiqlandi!")
        if user_id not in users:
            await call.message.answer("Ism va Familiyangizni kiriting:\n(Masalan: Mamazokirov Doniyorbek)")
            await state.set_state(Form.waiting_for_name)
        else:
            await send_main_menu(call.message)
    else:
        await call.answer("❌ Siz hali kanalga obuna bo'lmadingiz!", show_alert=True)

@dp.message(Command("addtest"))
async def add_test_start(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    
    if user_id != ADMIN_ID:
        await message.answer(f"❌ Siz admin emassiz!", parse_mode="Markdown")
        return
        
    await message.answer("📝 Yangi test kodini kiriting (Masalan: 101):")
    await state.set_state(Form.waiting_for_test_code)

@dp.message(Form.waiting_for_test_code)
async def process_test_code(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text.startswith("/"): return
    await state.update_data(test_code=text)
    await message.answer("📌 Test nomini yoki mavzusini kiriting (Masalan: Matematika 1-variant):")
    await state.set_state(Form.waiting_for_test_name)

@dp.message(Form.waiting_for_test_name)
async def process_test_name(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text.startswith("/"): return
    await state.update_data(test_name=text)
    await message.answer("🖼 Test rasmini yuboring (Agar rasm bo'lmasa, /skip deb yozing):")
    await state.set_state(Form.waiting_for_photo)

@dp.message(Form.waiting_for_photo, F.photo)
async def process_test_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)
    await message.answer("🔑 Testning to'g'ri javoblarini kiriting (Masalan: abcdab...):")
    await state.set_state(Form.waiting_for_answers)

@dp.message(Form.waiting_for_photo, Command("skip"))
async def skip_photo(message: types.Message, state: FSMContext):
    await state.update_data(photo_id=None)
    await message.answer("🔑 Testning to'g'ri javoblarini kiriting (Masalan: abcdab...):")
    await state.set_state(Form.waiting_for_answers)

@dp.message(Form.waiting_for_answers)
async def process_test_answers(message: types.Message, state: FSMContext):
    text = message.text.strip().lower()
    if text.startswith("/"): return
    
    data = await state.get_data()
    code = data['test_code']
    name = data['test_name']
    photo_id = data.get('photo_id')
    
    tests[code] = {
        "name": name,
        "answers": text,
        "photo_id": photo_id
    }
    results[code] = []
    await state.clear()
    
    bot_info = await bot.get_me()
    bot_link = f"https://t.me/{bot_info.username}"
    
    post_text = (
        f"📢 **TEST TAYYOR!**\n\n"
        f"📋 **Test nomi:** {name}\n"
        f"🔹 **Test kodi:** `{code}`\n"
        f"❓ **Savollar soni:** {len(text)} ta\n\n"
        f"📥 **Javob yuborish tartibi:**\n"
        f"Test javoblarini tekshirish uchun ushbu botga kiring:\n"
        f"👉 [{bot_info.first_name}]({bot_link})\n\n"
        f"Botga javoblarni quyidagi formatda yuboring:\n"
        f"`{code}#javoblaringiz`\n\n"
        f"*(Masalan: `{code}#{text[:5]}...`)*"
    )
    
    await message.answer("✅ Test muvaffaqiyatli saqlandi!\n\nO'quvchilar uchun e'lon matni 👇")
    if photo_id:
        await message.answer_photo(photo=photo_id, caption=post_text, parse_mode="Markdown")
    else:
        await message.answer(post_text, parse_mode="Markdown")

@dp.message(Command("natijalar"))
async def get_results(message: types.Message, state: FSMContext):
    await state.clear()
    if message.from_user.id != ADMIN_ID: return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("⚠️ Test kodini ham yozing. Masalan: `/natijalar 101`", parse_mode="Markdown")
        return
    
    code = args[1].strip()
    if code not in results or not results[code]:
        await message.answer("❌ Bu kod bo'yicha hech kim test topshirmagan yoki test kodi xato.")
        return
    
    test_info = tests.get(code, {})
    test_name = test_info.get("name", "Noma'lum test")
    
    sorted_res = sorted(results[code], key=lambda x: x['score'], reverse=True)
    res_text = f"📊 **TEST #{code} NATIJALARI RO'YXATI:**\n"
    res_text += f"📌 **Mavzu:** {test_name}\n\n"
    
    for i, res in enumerate(sorted_res, 1):
        res_text += f"{i}. {res['name']} — **{res['score']}/{res['total']}** ({res['percent']}%)\n"
    
    await message.answer(res_text, parse_mode="Markdown")

@dp.message(Form.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text.startswith("/"): return
    
    users[message.from_user.id] = text
    await state.clear()
    await message.answer(f"✅ Rahmat, {text}! Ma'lumotlaringiz saqlandi.")
    await send_main_menu(message)

async def send_main_menu(message: types.Message):
    txt = (
        "📌 **Javob yuborish formati:** `TEST_KODI#JAVOBLAR`\n"
        "*(Masalan: `101#abcdab...`)*\n\n"
    )
    if message.from_user.id == ADMIN_ID:
        txt += (
            "🛠 **Admin buyruqlari:**\n"
            "➕ /addtest — Yangi test qo'shish\n"
            "📊 /natijalar TEST_KODI — Natijalar ro'yxatini olish"
        )
    await message.answer(txt, parse_mode="Markdown")

@dp.message(F.text.contains("#"))
async def check_answers(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    # Javob yuborishda ham obuna tekshiriladi
    if user_id != ADMIN_ID:
        is_sub = await check_sub(user_id)
        if not is_sub:
            await message.answer(
                "⚠️ **Javobingizni qabul qilish uchun avval kanalimizga obuna bo'ling!**",
                reply_markup=get_sub_keyboard(),
                parse_mode="Markdown"
            )
            return

    if user_id not in users:
        await message.answer("Iltimos, avval /start tugmasini bosib ismingizni kiriting!")
        return

    try:
        parts = message.text.strip().replace("'", "").replace("`", "").split("#")
        code = parts[0].strip()
        user_ans = parts[1].strip().lower()
    except Exception:
        await message.answer("⚠️ Javob formati xato! Masalan: `101#abcd...` deb yuboring.")
        return

    if code not in tests:
        await message.answer("❌ Bunday kodli test topilmadi!")
        return

    correct_ans = tests[code]["answers"]
    test_name = tests[code]["name"]
    total = len(correct_ans)
    user_len = len(user_ans)
    
    score = 0
    wrong = []
    
    for i in range(min(total, user_len)):
        if user_ans[i] == correct_ans[i]:
            score += 1
        else:
            wrong.append(str(i + 1))
            
    percent = round((score / total) * 100, 1)
    user_name = users[user_id]

    results[code].append({
        "name": user_name,
        "score": score,
        "total": total,
        "percent": percent
    })

    msg = (
        f"📊 **Test Natijangiz ({user_name}):**\n"
        f"📌 **Test:** {test_name}\n\n"
        f"🔹 Test kodi: {code}\n"
        f"✅ To'g'ri javoblar: {score}/{total} ta\n"
        f"📈 Foiz: {percent}%\n"
    )
    if wrong:
        msg += f"❌ Xato savollar: {', '.join(wrong)}"
    await message.answer(msg, parse_mode="Markdown")

    admin_alert = (
        f"🔔 **Yangi javob keldi!**\n\n"
        f"👤 O'quvchi: {user_name}\n"
        f"📌 Test: {test_name}\n"
        f"🔹 Kodi: {code}\n"
        f"🎯 Natija: {score}/{total} ({percent}%)"
    )
    try:
        await bot.send_message(chat_id=ADMIN_ID, text=admin_alert, parse_mode="Markdown")
    except Exception:
        pass

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
