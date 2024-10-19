import logging
import sqlite3
from historical_data_and_visualization import get_historical_data_and_chart
from investment_terms_nlp import get_investment_term_explanation, initialize_bot_data
import yfinance as yf
import requests_cache
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters,ConversationHandler
from stock_price_prediction_model import train_and_predict
from investment_recommendation_system import generate_investment_recommendation
from user_profile_system import UserProfileManager, UserProfile, InvestmentExperience, InvestmentGoal, get_personalized_recommendation
from investment_risk_assessment import get_risk_assessment
from dotenv import load_dotenv
import os

load_dotenv() 

telegram_token = os.getenv('TELEGRAM_API_KEY')

requests_cache.install_cache('finance_cache', backend='sqlite', expire_after=300)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

profile_manager = UserProfileManager()

EXPERIENCE, GOAL, RISK = range(3)

async def start_profile_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_keyboard = [[e.value for e in InvestmentExperience]]
    await update.message.reply_text(
        "Давайте створимо ваш інвестиційний профіль. Спочатку оберіть ваш рівень досвіду:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return EXPERIENCE

async def set_experience(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['experience'] = InvestmentExperience(update.message.text)
    reply_keyboard = [[g.value for g in InvestmentGoal]]
    await update.message.reply_text(
        "Чудово! Тепер оберіть вашу основну інвестиційну мету:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return GOAL

async def set_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['goal'] = InvestmentGoal(update.message.text)
    await update.message.reply_text(
        "Останнє питання: оцініть вашу толерантність до ризику від 1 (дуже низька) до 10 (дуже висока):",
        reply_markup=ReplyKeyboardRemove()
    )
    return RISK

async def set_risk_and_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    risk = int(update.message.text)
    if risk < 1 or risk > 10:
        await update.message.reply_text("Будь ласка, введіть число від 1 до 10.")
        return RISK
    
    profile = UserProfile(
        user_id=update.effective_user.id,
        experience=context.user_data['experience'],
        goal=context.user_data['goal'],
        risk_tolerance=risk
    )
    profile_manager.create_or_update_profile(profile)
    
    await update.message.reply_text("Дякую! Ваш інвестиційний профіль створено.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Створення профілю скасовано.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def predict_and_recommend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("Будь ласка, вкажіть символ акції після команди /analyze")
        return

    symbol = context.args[0].upper()
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')

    await update.message.reply_text(f"Починаю аналіз для {symbol}. Це може зайняти кілька хвилин...")

    try:
        historical_data = yf.download(symbol, start=start_date, end=end_date)
        last_price, predicted_price, sentiment = train_and_predict(symbol, start_date, end_date)
        
        user_profile = profile_manager.get_profile(update.effective_user.id)
        if user_profile:
            recommendation = get_personalized_recommendation(user_profile, symbol, last_price, predicted_price, sentiment, historical_data)
        else:
            recommendation = generate_investment_recommendation(symbol, last_price, predicted_price, sentiment, historical_data)
        
        response = f"Аналіз для {symbol}:\n\n"
        response += f"Остання ціна закриття: ${last_price:.2f}\n"
        response += f"Прогнозована наступна ціна: ${predicted_price:.2f}\n"
        response += f"Очікувана зміна: {((predicted_price - last_price) / last_price) * 100:.2f}%\n"
        response += f"Поточний настрій новин: {sentiment:.2f}\n\n"
        response += recommendation

        await update.message.reply_text(response)
    except Exception as e:
        logging.error(f"Помилка при аналізі {symbol}: {str(e)}", exc_info=True)
        await update.message.reply_text(f"Вибачте, сталася помилка при аналізі {symbol}. Будь ласка, спробуйте ще раз пізніше або зверніться до адміністратора.")


def get_term_definition(term):
    conn = sqlite3.connect('investment_knowledge.db')
    cursor = conn.cursor()
    cursor.execute("SELECT definition FROM investment_terms WHERE term LIKE ? COLLATE NOCASE", ('%'+term+'%',))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def get_current_price(symbol):
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1d")
        if not data.empty:
            return data['Close'].iloc[-1]
        else:
            return None
    except Exception as e:
        logging.error(f"Помилка при отриманні ціни для {symbol}: {e}")
        return None

def get_historical_data(symbol, period="1mo"):
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period)
        return data
    except Exception as e:
        logging.error(f"Помилка при отриманні історичних даних для {symbol}: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Вітаю! Я ваш інвестиційний консультант-бот. Запитайте мене про інвестиційні терміни або поточні ціни акцій та криптовалют.')

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
    Вітаю! Я ваш персональний інвестиційний асистент. Ось список доступних команд:

    /start - Почати роботу з ботом
    /help - Показати це повідомлення допомоги
    /create_profile - Створити або оновити ваш інвестиційний профіль
    /price <символ> - Отримати поточну ціну акції або криптовалюти
    /history <символ> <період> - Отримати історичні дані та графік для акції або криптовалюти
    /risk <символ> - Отримати оцінку ризиків для інвестиційного інструменту
    
    Періоди для /history: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
    
    Ви також можете просто написати інвестиційний термін, і я спробую дати його визначення.
    """
    await update.message.reply_text(help_text)

async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("Будь ласка, вкажіть символ акції або криптовалюти після команди /price")
        return

    symbol = context.args[0].upper()
    price = get_current_price(symbol)
    if price:
        await update.message.reply_text(f"Поточна ціна {symbol}: ${price:.2f}")
    else:
        await update.message.reply_text(f"Не вдалося отримати ціну для {symbol}. Перевірте правильність символу.")

async def get_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("Будь ласка, вкажіть символ акції або криптовалюти після команди /history")
        return
    
    symbol = context.args[0].upper()
    period = "1mo" 
    if len(context.args) > 1:
        period = context.args[1]
    
    summary, chart = get_historical_data_and_chart(symbol, period)
    
    if chart:
        await update.message.reply_photo(photo=chart, caption=summary)
    else:
        await update.message.reply_text(summary)

async def assess_risk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("Будь ласка, вкажіть символ акції або криптовалюти після команди /risk")
        return
    
    symbol = context.args[0].upper()
    risk_assessment = get_risk_assessment(symbol)
    await update.message.reply_text(f"Оцінка ризиків для {symbol}:\n\n{risk_assessment}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    response = get_investment_term_explanation(query)
    await update.message.reply_text(response)

async def predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("Будь ласка, вкажіть символ акції після команди /predict")
        return

    symbol = context.args[0].upper()
    start_date = (datetime.now() - timedelta(days=365*3)).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')

    await update.message.reply_text(f"Починаю прогнозування для {symbol}. Це може зайняти кілька хвилин...")

    try:
        last_price, predicted_price, sentiment = train_and_predict(symbol, start_date, end_date)
        percent_change = ((predicted_price - last_price) / last_price) * 100

        response = f"Прогноз для {symbol}:\n"
        response += f"Остання ціна закриття: ${last_price:.2f}\n"
        response += f"Прогнозована наступна ціна: ${predicted_price:.2f}\n"
        response += f"Очікувана зміна: {percent_change:.2f}%\n"
        response += f"Поточний настрій новин: {sentiment:.2f}\n"
        
        if sentiment > 0:
            response += "Настрій позитивний, що може підтримати зростання ціни."
        elif sentiment < 0:
            response += "Настрій негативний, що може призвести до зниження ціни."
        else:
            response += "Настрій нейтральний."

        await update.message.reply_text(response)
    except Exception as e:
        logging.error(f"Помилка при прогнозуванні для {symbol}: {str(e)}", exc_info=True)
        await update.message.reply_text(f"Вибачте, сталася помилка при прогнозуванні для {symbol}. Будь ласка, спробуйте ще раз пізніше або зверніться до адміністратора.")


def main():
    db_file = 'investment_knowledge.db'
    initialize_bot_data(db_file)
    application = ApplicationBuilder().token(telegram_token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('create_profile', start_profile_creation)],
        states={
            EXPERIENCE: [MessageHandler(filters.Regex(f"^({'|'.join(e.value for e in InvestmentExperience)})$"), set_experience)],
            GOAL: [MessageHandler(filters.Regex(f"^({'|'.join(g.value for g in InvestmentGoal)})$"), set_goal)],
            RISK: [MessageHandler(filters.Regex("^[1-9]|10$"), set_risk_and_finish)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("price", get_price))
    application.add_handler(CommandHandler("history", get_history))
    application.add_handler(CommandHandler("analyze", predict_and_recommend))
    application.add_handler(CommandHandler("risk", assess_risk))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    application.run_polling()

if __name__ == '__main__':
    main()