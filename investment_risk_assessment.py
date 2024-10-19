import yfinance as yf
import numpy as np
import pandas as pd
from scipy import stats

def get_risk_metrics(symbol, market_symbol='^GSPC', period='1mo'):
    """
    Розраховує метрики ризику для заданого символу.
    
    :param symbol: Символ акції або криптовалюти
    :param market_symbol: Символ для ринкового індексу (за замовчуванням S&P 500)
    :param period: Період часу для аналізу
    :return: Словник з метриками ризику
    """
    try:
        asset = yf.Ticker(symbol)
        market = yf.Ticker(market_symbol)
        
        asset_data = asset.history(period=period)['Close']
        market_data = market.history(period=period)['Close']
        
        asset_returns = asset_data.pct_change().dropna()
        market_returns = market_data.pct_change().dropna()
        
        volatility = asset_returns.std() * np.sqrt(252)
        
        covariance = np.cov(asset_returns, market_returns)[0][1]
        market_variance = np.var(market_returns)
        beta = covariance / market_variance
        
        var_95 = np.percentile(asset_returns, 5)
        
        sharpe_ratio = asset_returns.mean() / asset_returns.std() * np.sqrt(252)
        
        return {
            "volatility": volatility,
            "beta": beta,
            "var_95": var_95,
            "sharpe_ratio": sharpe_ratio
        }
    except Exception as e:
        print(f"Помилка при розрахунку метрик ризику для {symbol}: {e}")
        return None

def interpret_risk_metrics(metrics):
    """
    Інтерпретує метрики ризику і надає текстовий опис.
    
    :param metrics: Словник з метриками ризику
    :return: Рядок з інтерпретацією ризиків
    """
    if metrics is None:
        return "Не вдалося розрахувати метрики ризику."
    
    interpretation = "Оцінка ризиків:\n\n"
    
    interpretation += f"Волатильність: {metrics['volatility']:.2%}\n"
    if metrics['volatility'] < 0.15:
        interpretation += "Низька волатильність. Відносно стабільний актив.\n"
    elif metrics['volatility'] < 0.30:
        interpretation += "Середня волатильність. Помірний ризик.\n"
    else:
        interpretation += "Висока волатильність. Підвищений ризик.\n"
    
    interpretation += f"\nБета-коефіцієнт: {metrics['beta']:.2f}\n"
    if metrics['beta'] < 0.8:
        interpretation += "Менш волатильний, ніж ринок. Може бути хорошим для диверсифікації.\n"
    elif metrics['beta'] < 1.2:
        interpretation += "Приблизно така ж волатильність, як і ринок.\n"
    else:
        interpretation += "Більш волатильний, ніж ринок. Підвищений ризик.\n"
    
    interpretation += f"\nValue at Risk (95%): {metrics['var_95']:.2%}\n"
    interpretation += f"З ймовірністю 95%, втрати не перевищать {abs(metrics['var_95']):.2%} за день.\n"
    
    interpretation += f"\nКоефіцієнт Шарпа: {metrics['sharpe_ratio']:.2f}\n"
    if metrics['sharpe_ratio'] < 0.5:
        interpretation += "Низький коефіцієнт Шарпа. Поганий ризик/дохідність баланс.\n"
    elif metrics['sharpe_ratio'] < 1:
        interpretation += "Середній коефіцієнт Шарпа. Помірний ризик/дохідність баланс.\n"
    else:
        interpretation += "Високий коефіцієнт Шарпа. Хороший ризик/дохідність баланс.\n"
    
    return interpretation

def get_risk_assessment(symbol, period='1mo'):
    """
    Отримує та інтерпретує оцінку ризиків для заданого символу.
    
    :param symbol: Символ акції або криптовалюти
    :param period: Період часу для аналізу
    :return: Рядок з оцінкою ризиків
    """
    metrics = get_risk_metrics(symbol, period=period)
    return interpret_risk_metrics(metrics)