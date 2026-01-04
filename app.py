import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

def calculate_stats(df):
    stats = df.groupby('season')['temperature'].agg(['mean', 'std']).reset_index()
    stats['min_temperature'] = stats['mean'] - 2 * stats['std']
    stats['max_temperature'] = stats['mean'] + 2 * stats['std']
    return stats

def get_anomalies(city_df, stats):
    merged = city_df.merge(stats, on='season')
    anomalies = merged[(merged['temperature'] < merged['min_temperature']) | (merged['temperature'] > merged['max_temperature'])]
    return anomalies

# def get_current_weather(city, api_key):
#     url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
#     response = requests.get(url)
#     if response.status_code == 200:
#         return response.json()['main']['temp']
#     else:
#         print('Oh, something went wrong (as usually it is)')
#         return None

def get_current_weather(city, api_key):
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    try:
        response = requests.get(url)
        return response.json(), response.status_code
    except Exception as e:
        return {"'Oh, something went wrong (as usually it is)": str(e)}, 500

st.set_page_config(page_title="MY STREAMLIT APP OMG I AM SO HAPPY", layout="wide")
st.title("Погодку хотите узнать?)")
st.sidebar.header("Надо данные загрузить")
uploaded_file = st.sidebar.file_uploader("Загрузите csv с историческими данными по погоде", type="csv")
# это чтобы сходу ошибка не вылезала
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    st.sidebar.header("Теперь поймем чего мы вообще хотим")
    cities = df['city'].unique()
    selected_city = st.sidebar.selectbox("Выберите город", cities)
    st.sidebar.header("Апишку надо")
    api_key = st.sidebar.text_input("Введите OpenWeatherMap API Key", type="password")
    st.header(f"Проводим аналитику для: {selected_city}")
    city_df = df[df['city'] == selected_city].sort_values('timestamp')
    # давайте в красивую таблицу оформим
    col1, col2, col3 = st.columns(3)
    col1.metric("Средняя температура за время анализа", f"{city_df['temperature'].mean():.2f}") # до двух знаков округлим а то очень страшно выглядит
    col2.metric("Максимальная температура за время анализа", f"{city_df['temperature'].max():.2f}")
    col3.metric("Минимальныя температура за время анализа", f"{city_df['temperature'].min():.2f}")

    stats = calculate_stats(city_df)
    anomalies = get_anomalies(city_df, stats)

    # Давайте выведем временной ряд с аномалиями
    st.subheader("Давайте выведем временной ряд с аномалиями")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=city_df['timestamp'], y=city_df['temperature'], mode='lines', name='Температура', line=dict(color='blue')))
    if not anomalies.empty:
        fig.add_trace(go.Scatter(x=anomalies['timestamp'], y=anomalies['temperature'], mode='markers', name='Аномалия', marker=dict(color='red', size=6)))
    fig.update_layout(xaxis_title="Дата", yaxis_title="Температура", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
    # А теперь можно вывести и сезонные профили
    st.subheader("Сезонные профили (Среднее плюс минус 2 стандартных отклонения)")
    st.table(stats.set_index('season').rename(columns={
        'mean': 'Среднее', 'std': 'Стандартное отклонение', 
        'min_temperature': 'Нижняя граница', 'max_temperature': 'Верхняя граница'
    }))
    # Текущую погоду посмотрим
    st.divider()
    st.header("Текущую погоду посмотрим")
    if not api_key:
        st.info("Введите API-ключ чтобы увидеть прекрасное")
    else:
        with st.spinner('Секундочку сейчас все будет'): # спиннер это игрушка такая у меня в детстве была
            weather_data, status_code = get_current_weather(selected_city, api_key)
            if status_code == 200:
                current_temp = weather_data['main']['temp']
                curr_season = 'winter'
                season_stats = stats[stats['season'] == curr_season].iloc[0]
                is_normal = season_stats['min_temperature'] <= current_temp <= season_stats['max_temperature']
                m1, m2 = st.columns(2)
                m1.metric("Текущая температура", f"{current_temp:.2f}")
                if is_normal:
                    m2.success(f"Температура стандартная, приемлемая: {curr_season}")
                else:
                    m2.error(f"Анамальная температура {curr_season}!")
                    st.write(f"Нормальный диапазон для этого времени года для этого города: {season_stats['min_temperature']:.2f} — {season_stats['max_temperature']:.2f}")
            elif status_code == 401:
                st.error(f"Error: {weather_data['message']}")
            else:
                st.warning(f"Что-то пошло не так (а кто-то сомневался?): {status_code}")
else:
    st.info("Велкому, загрузите пожалуйста файл с историческими данными по погоде в формате CSV через боковую панель!")