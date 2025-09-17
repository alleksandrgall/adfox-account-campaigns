#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для получения кампаний из AdFox API и парсинга их в Python объекты
"""

import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import json
import re

# Константы
LIMIT = 100  # Глобальная константа для лимита
BASE_URL = "https://adfox.yandex.ru/api/v1"

def get_start_of_month():
    """Получить начало текущего месяца в формате YYYY-MM-DD"""
    now = datetime.now()
    return now.replace(day=1).strftime('%Y-%m-%d')

def clean_xml_response(xml_content):
    """Очистить XML ответ от проблемных символов"""
    # Найдем последний валидный тег </response>
    last_response_end = xml_content.rfind('</response>')
    if last_response_end != -1:
        # Обрежем до конца тега </response>
        clean_content = xml_content[:last_response_end + len('</response>')]
        return clean_content
    return xml_content

def xml_to_dict(element):
    """Рекурсивно конвертирует XML элемент в словарь"""
    result = {}
    
    # Если элемент имеет дочерние элементы
    if len(element) > 0:
        for child in element:
            child_data = xml_to_dict(child)
            
            # Если уже есть ключ с таким именем, создаем список
            if child.tag in result:
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_data)
            else:
                result[child.tag] = child_data
    else:
        # Если элемент содержит только текст
        return element.text
    
    return result

def parse_campaigns_data(xml_data):
    """Парсит данные кампаний из XML структуры"""
    campaigns = []
    
    if 'result' in xml_data and 'data' in xml_data['result']:
        data = xml_data['result']['data']
        
        # Извлекаем все строки (row0, row1, row2, ...)
        for key, value in data.items():
            if key.startswith('row') and isinstance(value, dict):
                campaigns.append(value)
    
    return campaigns

def get_campaigns():
    """Получить список кампаний из AdFox API"""
    
    # Получение токена из переменных окружения
    auth_token = os.getenv('AUTH_TOKEN')
    if not auth_token:
        raise ValueError("AUTH_TOKEN не найден в переменных окружения")
    
    # Параметры запроса
    params = {
        'object': 'account',
        'action': 'list',
        'actionObject': 'campaign',
        'dateAddedFrom': get_start_of_month(),
        'show': 'advanced',
        'limit': LIMIT
    }
    
    # Заголовки
    headers = {
        'Authorization': f'OAuth {auth_token}'
    }
    
    try:
        print(f"Выполняется запрос к {BASE_URL}")
        print(f"Параметры: {params}")
        
        # Выполнение запроса
        response = requests.get(BASE_URL, params=params, headers=headers)
        response.raise_for_status()
        
        print(f"Ответ получен, статус: {response.status_code}")
        
        # Определяем кодировку из заголовка Content-Type или используем windows-1251 по умолчанию
        encoding = 'windows-1251'
        content_type = response.headers.get('Content-Type', '')
        if 'charset=' in content_type:
            encoding = content_type.split('charset=')[1].split(';')[0].strip()
        
        # Декодируем содержимое с правильной кодировкой
        xml_content = response.content.decode(encoding)
        
        # Очищаем XML от проблемных символов
        clean_xml = clean_xml_response(xml_content)
        
        # Парсинг XML ответа
        root = ET.fromstring(clean_xml)
        
        # Конвертация XML в Python объекты
        result = xml_to_dict(root)
        
        return result
        
    except requests.RequestException as e:
        print(f"Ошибка при выполнении запроса: {e}")
        return None
    except ET.ParseError as e:
        print(f"Ошибка при парсинге XML: {e}")
        return None
    except UnicodeDecodeError as e:
        print(f"Ошибка декодирования: {e}")
        return None

def print_campaign_stats(campaigns):
    """Вывести статистику по кампаниям"""
    if not campaigns:
        print("Нет данных для анализа")
        return
    
    print(f"\nСтатистика по кампаниям:")
    print(f"Всего кампаний: {len(campaigns)}")
    
    # Подсчет по статусам
    status_counts = {}
    for campaign in campaigns:
        status = campaign.get('status', 'unknown')
        status_counts[status] = status_counts.get(status, 0) + 1
    
    status_names = {
        '0': 'Активные',
        '1': 'Приостановленные', 
        '2': 'Завершенные'
    }
    
    for status, count in status_counts.items():
        status_name = status_names.get(status, f'Статус {status}')
        print(f"{status_name}: {count}")
    
    # Общая статистика
    total_impressions = sum(int(c.get('impressionsAll', 0) or 0) for c in campaigns)
    total_clicks = sum(int(c.get('clicksAll', 0) or 0) for c in campaigns)
    
    print(f"\nОбщие показатели:")
    print(f"Всего показов: {total_impressions:,}")
    print(f"Всего кликов: {total_clicks:,}")
    
    if total_impressions > 0:
        overall_ctr = (total_clicks / total_impressions) * 100
        print(f"Общий CTR: {overall_ctr:.3f}%")

def main():
    """Основная функция"""
    print("=" * 60)
    print("AdFox Campaigns Parser")
    print("=" * 60)
    
    print(f"Получение кампаний с {get_start_of_month()}")
    print(f"Лимит: {LIMIT}")
    
    try:
        # Получение данных
        data = get_campaigns()
        
        if data:
            # Парсинг кампаний
            campaigns = parse_campaigns_data(data)
            
            if campaigns:
                print_campaign_stats(campaigns)
                
                # Вывод первых нескольких кампаний для проверки
                print(f"\nПервые 3 кампании:")
                for i, campaign in enumerate(campaigns[:3]):
                    print(f"\n--- Кампания {i+1} ---")
                    print(f"ID: {campaign.get('ID', 'N/A')}")
                    print(f"Название: {campaign.get('name', 'N/A')}")
                    print(f"Статус: {campaign.get('status', 'N/A')}")
                    print(f"Лимит показов в день: {campaign.get('maxImpressionsPerDay', 'N/A')}")
                    print(f"Показы всего: {campaign.get('impressionsAll', 'N/A')}")
                    print(f"Клики всего: {campaign.get('clicksAll', 'N/A')}")
                    print(f"CTR: {campaign.get('CTR', 'N/A')}")
                    print(f"Дата начала: {campaign.get('dateStart', 'N/A')}")
                    print(f"Дата окончания: {campaign.get('dateEnd', 'N/A')}")
                
                # Сохранение в JSON файл
                output_file = 'adfox_campaigns.json'
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'metadata': {
                            'total_campaigns': len(campaigns),
                            'fetch_date': datetime.now().isoformat(),
                            'date_from': get_start_of_month(),
                            'limit': LIMIT
                        },
                        'campaigns': campaigns
                    }, f, ensure_ascii=False, indent=2)
                
                print(f"\nДанные сохранены в {output_file}")
            else:
                print("Кампании не найдены в ответе")
        else:
            print("Не удалось получить данные")
            
    except Exception as e:
        print(f"Произошла ошибка: {e}")

if __name__ == "__main__":
    main()
