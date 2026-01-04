import pandas as pd
import numpy as np
import requests
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import asyncio
import aiohttp
from datetime import datetime
import joblib
from functools import partial
from multiprocessing import Pool, cpu_count
import logging

workers = int(cpu_count() / 2) # будем использовать только половину ядер

# Все будет записываться в лог файл чтобы можно было посмотреть что там насчиталось и как)
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[
        logging.FileHandler("data_analysis.log", mode='w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def get_mean_std(df, season, city):
    season_data = df.loc[(df['season'] == season) & (df['city'] == city)]['temperature']
    return season_data.mean(), season_data.std()

def check_if_anomaly(df, temperature, season, city):
    mean_temp, std_temp = get_mean_std(df, season, city)
    low_low_level = mean_temp - 2 * std_temp
    high_high_level = mean_temp + 2 * std_temp
    return not (low_low_level <= temperature <= high_high_level)

def get_anom_dates(city, df, n_sigma=2):
    anomalies = []
    city_data = df[df['city'] == city].copy()
    # Посчитаем скользящее среднее как по тз
    city_data['rolling_mean'] = city_data['temperature'].rolling(window=30, min_periods=1).mean()
    # Проверяем наблюдения на аномалии (при этом все же будем использовать сырую погоду, думаю это лучше чем скользящее среднее)
    for idx, row in city_data.iterrows():
        is_anomaly = check_if_anomaly(
            df, row['temperature'], row['season'], city
        )
        if is_anomaly:
            anomalies.append({
                'timestamp': row['timestamp'],
                'temperature': row['temperature'],
                'season': row['season'],
            })
    return pd.DataFrame(anomalies)

def get_anom_dates_parallel(cities, df_to_pass):
    with ProcessPoolExecutor(max_workers=workers) as executor:
        worker_func = partial(get_anom_dates, df=df_to_pass)
        results = list(executor.map(worker_func, cities))
    valid_results = [res for res in results if not res.empty]
    return pd.concat(valid_results, ignore_index=True)

# Сравнение скорости последовательного и параллельного выполнения
def compare_execution_speed(data):
    print('Start')
    cities = data['city'].unique()

    # Последовательное выполнение
    start_time = time.time()
    sequential_results = []
    for city in cities:
        print(city)
        anomalies = get_anom_dates(city, data)
        sequential_results.append(anomalies)
    sequential_time = time.time() - start_time
    
    # Параллельное выполнение
    logging.info('Start parallel')
    start_time = time.time()
    parallel_results = get_anom_dates_parallel(cities, data)
    parallel_time = time.time() - start_time
    logging.info('End parallel')

    sequential_combined = pd.concat(sequential_results, ignore_index=True)

    logging.info(f"Последовательное выполнение заняло {sequential_time:.2f} секунд")
    logging.info(f"Параллельное выполнение заняло {parallel_time:.2f} секунд")
    logging.info(f"Последовательное выполнение нашло аномалий {len(sequential_combined)}")
    logging.info(f"Параллельное выполнение нашло аномалий {len(parallel_results)}")
    
    # Давайте еще проверим, правильно ли все выполнилось (нужно чтобы оба подхода дали одинаковые результаты)
    seq_dates = set(sequential_combined['timestamp'].astype(str))
    par_dates = set(parallel_results['timestamp'].astype(str))
    logging.info(f"Верно ли все? {seq_dates == par_dates}")
    return sequential_time, parallel_time

# Еще напишем функцию которая создает таблицу с диапазонами погоды, когда температура считается нормальной (это потом нужно будет)
def get_city_season_ranges(df):
    stats = df.groupby(['city', 'season'])['temperature'].agg(['mean', 'std']).reset_index()
    stats['min_temperature'] = stats['mean'] - 2 * stats['std']
    stats['max_temperature'] = stats['mean'] + 2 * stats['std']
    return stats[['city', 'season', 'min_temperature', 'max_temperature']]

if __name__ == '__main__':
    df = pd.read_csv('temperature_data.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values(["city", "timestamp"]).reset_index(drop=True)
    seasons = list(set(df.season.tolist()))
    # месяцы и сезоны сопоставляем
    month_to_season = {12: "winter", 1: "winter", 2: "winter",
                    3: "spring", 4: "spring", 5: "spring",
                    6: "summer", 7: "summer", 8: "summer",
                    9: "autumn", 10: "autumn", 11: "autumn"}
    data = df.copy()
    seq_time, par_time = compare_execution_speed(data)

    ranges_df = get_city_season_ranges(data)
    logging.info(ranges_df.head())
    ranges_df.to_csv('normal_temperature_ranges.csv', index=False)
    logging.info('Success (FINALLY!!!!!!!! aaaaaaaaaaaaaaaaaaaa)')