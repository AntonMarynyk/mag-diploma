import sqlite3
from enum import Enum

from investment_recommendation_system import generate_investment_recommendation

class InvestmentExperience(Enum):
    BEGINNER = "Початківець"
    INTERMEDIATE = "Середній"
    ADVANCED = "Досвідчений"

class InvestmentGoal(Enum):
    SAVINGS = "Заощадження"
    INCOME = "Пасивний дохід"
    GROWTH = "Зростання капіталу"
    SPECULATION = "Спекуляція"

class UserProfile:
    def __init__(self, user_id, experience, goal, risk_tolerance):
        self.user_id = user_id
        self.experience = experience
        self.goal = goal
        self.risk_tolerance = risk_tolerance

class UserProfileManager:
    def __init__(self, db_name='user_profiles.db'):
        self.conn = sqlite3.connect(db_name)
        self.create_table()

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_profiles
        (user_id INTEGER PRIMARY KEY,
        experience TEXT,
        goal TEXT,
        risk_tolerance INTEGER)
        ''')
        self.conn.commit()

    def create_or_update_profile(self, profile):
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT OR REPLACE INTO user_profiles (user_id, experience, goal, risk_tolerance)
        VALUES (?, ?, ?, ?)
        ''', (profile.user_id, profile.experience.value, profile.goal.value, profile.risk_tolerance))
        self.conn.commit()

    def get_profile(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM user_profiles WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        if row:
            return UserProfile(
                user_id=row[0],
                experience=InvestmentExperience(row[1]),
                goal=InvestmentGoal(row[2]),
                risk_tolerance=row[3]
            )
        return None

    def close(self):
        self.conn.close()

def get_personalized_recommendation(profile, symbol, last_price, predicted_price, sentiment, historical_data):
    base_recommendation = generate_investment_recommendation(symbol, last_price, predicted_price, sentiment, historical_data)
    
    if profile.experience == InvestmentExperience.BEGINNER:
        base_recommendation += "\n\nЯк початківцю, вам слід бути особливо обережним та розглянути можливість консультації з фінансовим радником перед прийняттям рішень."
    
    if profile.goal == InvestmentGoal.INCOME:
        base_recommendation += "\n\nВраховуючи вашу мету отримання пасивного доходу, зверніть увагу на дивідендну політику компанії."
    elif profile.goal == InvestmentGoal.GROWTH:
        base_recommendation += "\n\nДля досягнення мети зростання капіталу, розгляньте довгострокові перспективи компанії та галузі."
    
    if profile.risk_tolerance < 3:
        base_recommendation += "\n\nВраховуючи ваш низький рівень толерантності до ризику, розгляньте більш консервативні інвестиційні варіанти."
    elif profile.risk_tolerance > 7:
        base_recommendation += "\n\nВаш високий рівень толерантності до ризику дозволяє розглядати більш агресивні інвестиційні стратегії, але не забувайте про диверсифікацію."
    
    return base_recommendation