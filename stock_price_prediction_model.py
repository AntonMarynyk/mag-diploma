import os
import nltk
from textblob import TextBlob
import pandas as pd
import numpy as np
import yfinance as yf
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.optimizers.legacy import Adam
import requests
import numpy as np
from dotenv import load_dotenv

load_dotenv() 
news_api_key = os.getenv('NEWS_API_KEY')

nltk.download('punkt')

def get_company_news(company_name, api_key):
    url = f"https://newsapi.org/v2/everything?q={company_name}&apiKey={api_key}&language=en"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()['articles']
    else:
        print(f"Помилка при отриманні новин: {response.status_code}")
        return []

def analyze_sentiment(text):
    blob = TextBlob(text)
    return blob.sentiment.polarity

def get_company_sentiment(company_name, api_key):
    news = get_company_news(company_name, api_key)
    sentiments = [analyze_sentiment(article['title'] + " " + article['description']) for article in news if article['title'] and article['description']]
    return np.mean(sentiments) if sentiments else 0

def get_stock_data(symbol, start_date, end_date, news_api_key = news_api_key):
    data = yf.download(symbol, start=start_date, end=end_date)
    df = data[['Close']].reset_index()
    df = df.rename(columns={'Date': 'date', 'Close': 'close'})
    
    company_name = yf.Ticker(symbol).info['longName']
    df['sentiment'] = [get_company_sentiment(company_name, news_api_key) for _ in range(len(df))]
    
    return df

def prepare_data(data, look_back=60):
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(data[['close', 'sentiment']])
    
    X, y = [], []
    for i in range(look_back, len(scaled_data)):
        X.append(scaled_data[i-look_back:i])
        y.append(scaled_data[i, 0])
    
    X, y = np.array(X), np.array(y)
    
    return X, y, scaler

def create_model(look_back, features):
    model = Sequential()
    model.add(LSTM(units=50, return_sequences=True, input_shape=(look_back, features)))
    model.add(LSTM(units=50))
    model.add(Dense(1))
    
    model.compile(optimizer=Adam(learning_rate=0.001), loss='mean_squared_error')
    return model

def predict_price(model, data, scaler, look_back):
    last_data = data[['close', 'sentiment']].values[-look_back:]
    last_data_scaled = scaler.transform(last_data)
    X_test = np.array([last_data_scaled])
    
    predicted_price_scaled = model.predict(X_test)
    predicted_price = scaler.inverse_transform(np.hstack((predicted_price_scaled, X_test[0, -1, 1].reshape(-1, 1))))[0, 0]
    
    return predicted_price

def train_and_predict(symbol, start_date, end_date, look_back=60):
    data = get_stock_data(symbol, start_date, end_date)
    
    X, y, scaler = prepare_data(data, look_back)
    
    model = create_model(look_back, X.shape[2])
    model.fit(X, y, epochs=50, batch_size=32, verbose=0)
    
    last_price = data['close'].iloc[-1]
    next_price = predict_price(model, data, scaler, look_back)
    
    return last_price, next_price, data['sentiment'].iloc[-1]

