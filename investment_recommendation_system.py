import numpy as np
import pandas as pd
from scipy.stats import percentileofscore

def calculate_volatility(historical_data, window=30):
    """Розрахунок історичної волатильності"""
    returns = historical_data['Close'].pct_change()
    return returns.rolling(window=window).std().iloc[-1]

def get_recommendation(symbol, last_price, predicted_price, sentiment, historical_data):
    expected_change = (predicted_price - last_price) / last_price

    volatility = calculate_volatility(historical_data)

    volatility_percentile = percentileofscore(
        historical_data['Close'].pct_change().rolling(window=30).std(), 
        volatility
    )
    
    if volatility_percentile < 33:
        risk_level = "низький"
    elif volatility_percentile < 66:
        risk_level = "середній"
    else:
        risk_level = "високий"

    if expected_change > 0.05 and sentiment > 0:
        action = "купити"
    elif expected_change < -0.05 and sentiment < 0:
        action = "продати"
    else:
        action = "утримувати"

    recommendation = f"Рекомендація для {symbol}:\n"
    recommendation += f"Дія: {action.capitalize()}\n"
    recommendation += f"Очікувана зміна ціни: {expected_change:.2%}\n"
    recommendation += f"Поточний настрій: {sentiment:.2f}\n"
    recommendation += f"Рівень ризику: {risk_level}\n\n"

    if action == "купити":
        recommendation += "Обґрунтування: Прогнозується значне зростання ціни, і настрій ринку позитивний."
    elif action == "продати":
        recommendation += "Обґрунтування: Прогнозується значне падіння ціни, і настрій ринку негативний."
    else:
        recommendation += "Обґрунтування: Немає чітких сигналів для купівлі чи продажу. Рекомендується спостерігати за ситуацією."

    recommendation += f"\n\nЗастереження: Рівень ризику {risk_level}. "
    if risk_level == "високий":
        recommendation += "Будьте особливо обережні при прийнятті рішень."
    elif risk_level == "середній":
        recommendation += "Зважте всі за і проти перед прийняттям рішення."
    else:
        recommendation += "Ризик відносно низький, але завжди враховуйте можливість несподіваних змін на ринку."

    return recommendation

def generate_investment_recommendation(symbol, last_price, predicted_price, sentiment, historical_data):
    return get_recommendation(symbol, last_price, predicted_price, sentiment, historical_data)