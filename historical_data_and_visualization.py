import yfinance as yf
import matplotlib.pyplot as plt
from io import BytesIO
from PIL import Image
import pandas as pd

def get_historical_data(symbol, period="1mo"):
    """
    Отримує історичні дані для вказаного символу.
    
    :param symbol: Символ акції або криптовалюти
    :param period: Період часу для отримання даних (наприклад, "1mo" для одного місяця)
    :return: DataFrame з історичними даними
    """
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)
        return hist
    except Exception as e:
        print(f"Помилка при отриманні даних для {symbol}: {e}")
        return None

def create_price_volume_chart(data, symbol):
    """
    Створює графік цін та об'ємів торгів.
    
    :param data: DataFrame з історичними даними
    :param symbol: Символ акції або криптовалюти
    :return: Байтовий об'єкт з зображенням графіка
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    
    ax1.plot(data.index, data['Close'], label='Ціна закриття')
    ax1.set_title(f"Історичні дані для {symbol}")
    ax1.set_ylabel('Ціна')
    ax1.legend()
    
    ax2.bar(data.index, data['Volume'], label="Об'єм торгів")
    ax2.set_xlabel('Дата')
    ax2.set_ylabel("Об'єм")
    ax2.legend()
    
    plt.tight_layout()
    
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    
    plt.close(fig)
    
    return buf

def get_historical_data_summary(data):
    """
    Створює текстовий звіт на основі історичних даних.
    
    :param data: DataFrame з історичними даними
    :return: Рядок з текстовим звітом
    """
    summary = f"Період: з {data.index[0].date()} по {data.index[-1].date()}\n\n"
    summary += f"Початкова ціна: ${data['Close'].iloc[0]:.2f}\n"
    summary += f"Кінцева ціна: ${data['Close'].iloc[-1]:.2f}\n"
    summary += f"Мінімальна ціна: ${data['Low'].min():.2f}\n"
    summary += f"Максимальна ціна: ${data['High'].max():.2f}\n"
    summary += f"Середній об'єм торгів: {data['Volume'].mean():.0f}\n"
    
    price_change = (data['Close'].iloc[-1] - data['Close'].iloc[0]) / data['Close'].iloc[0] * 100
    summary += f"Зміна ціни: {price_change:.2f}%\n"
    
    return summary

def get_historical_data_and_chart(symbol, period="1mo"):
    """
    Отримує історичні дані та створює графік і текстовий звіт.
    
    :param symbol: Символ акції або криптовалюти
    :param period: Період часу для отримання даних
    :return: Кортеж (текстовий_звіт, байтовий_об'єкт_з_графіком)
    """
    data = get_historical_data(symbol, period)
    if data is None:
        return "Не вдалося отримати дані.", None
    
    summary = get_historical_data_summary(data)
    chart = create_price_volume_chart(data, symbol)
    
    return summary, chart