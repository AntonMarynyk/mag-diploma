import pandas as pd
import sqlite3
import torch
from transformers import AutoTokenizer, AutoModelForQuestionAnswering, pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re

def create_table_if_not_exists(conn):
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS investment_terms_translated (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        term TEXT NOT NULL,
        definition TEXT NOT NULL
    )
    ''')
    conn.commit()

def load_csv_to_db(csv_file, db_file):
    df = pd.read_csv(csv_file)
    
    conn = sqlite3.connect(db_file)
    
    create_table_if_not_exists(conn)
    
    df.to_sql('investment_terms_translated', conn, if_exists='replace', index=False)
    
    print(f"Завантажено {len(df)} термінів у базу даних.")
    
    conn.close()

def load_investment_terms(db_file):
    conn = sqlite3.connect(db_file)
    create_table_if_not_exists(conn)
    df = pd.read_sql_query("SELECT * FROM investment_terms_translated", conn)
    conn.close()
    return df

model_name = "bert-base-multilingual-cased"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForQuestionAnswering.from_pretrained(model_name)
nlp = pipeline("question-answering", model=model, tokenizer=tokenizer)

def initialize_nlp_model():
    model_name = "bert-base-multilingual-cased"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForQuestionAnswering.from_pretrained(model_name)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    model = model.to(device)
    
    nlp = pipeline("question-answering", model=model, tokenizer=tokenizer, device=0 if torch.cuda.is_available() else -1)
    
    return nlp


terms_df = None
vectorizer = None
term_vectors = None


def initialize_term_data(db_file):
    global terms_df, vectorizer, term_vectors, nlp
    terms_df = load_investment_terms(db_file)
    
    if terms_df.empty:
        print("Помилка: База даних термінів порожня")
        return False
    
    vectorizer = TfidfVectorizer()
    term_vectors = vectorizer.fit_transform(terms_df['term'])
    nlp = initialize_nlp_model()
    return True

def preprocess_text(text):
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text.lower()

def find_most_relevant_term(query):
    global vectorizer, term_vectors, terms_df
    if vectorizer is None or term_vectors is None or terms_df is None:
        raise ValueError("Дані термінів не були ініціалізовані.")
    
    query = preprocess_text(query)
    query_vector = vectorizer.transform([query])
    similarities = cosine_similarity(query_vector, term_vectors)
    most_similar_idx = similarities.argmax()
    return terms_df.iloc[most_similar_idx], similarities[0][most_similar_idx]

def extract_key_information(definition, query):
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', definition)
    
    query_words = set(preprocess_text(query).split())
    relevant_sentences = []
    
    for sentence in sentences:
        sentence_words = set(preprocess_text(sentence).split())
        if query_words.intersection(sentence_words):
            relevant_sentences.append(sentence)
    
    return ' '.join(relevant_sentences) if relevant_sentences else definition

def generate_answer(query):
    global nlp
    if nlp is None:
        raise ValueError("NLP модель не була ініціалізована.")
    
    relevant_term, similarity_score = find_most_relevant_term(query)
    
    if similarity_score < 0.3:
        return "Вибачте, я не можу знайти релевантну інформацію для цього запиту.", None
    
    key_info = extract_key_information(relevant_term['definition'], query)
    
    answer = f"{relevant_term['term']} - це {key_info}"
    
    if len(key_info) < len(relevant_term['definition']):
        answer += f"\n\nПовне визначення: {relevant_term['definition']}"
    
    return answer, relevant_term['term']

def get_investment_term_explanation(query):
    try:
        answer, term = generate_answer(query)
        if term:
            response = f"Термін: {term}\n\nВідповідь: {answer}\n\n"
        else:
            response = answer
    except ValueError as e:
        response = f"Помилка: {str(e)}"
    except Exception as e:
        response = f"Виникла неочікувана помилка: {str(e)}"
    return response


def initialize_bot_data(db_file):
    success = initialize_term_data(db_file)
    if not success:
        print("Помилка ініціалізації даних для бота")
    else:
        print("Дані для бота успішно ініціалізовані")
