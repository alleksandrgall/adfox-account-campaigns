#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простая версия скрипта для тестирования парсинга AdFox API
"""

import os
import requests  
import xml.etree.ElementTree as ET
from datetime import datetime
import json

# Константы
LIMIT = 100
BASE_URL = "https://adfox.yandex.ru/api/v1"

def get_start_of_month():
    """Получить начало текущего месяца в формате YYYY-MM-DD"""
    now = datetime.now()
    return now.replace(day=1).strftime('%Y-%m-%d')

def clean_xml_response(xml_content):
    """Очистить XML ответ от проблемных символов"""
    last_response_end = xml_content.rfind('</response>')
    if last_response_end != -1:
        clean_content = xml_content[:last_response_end + len('</response>')]
        return clean_content
    return xml_content

def xml_to_dict(element):
    """Рекурсивно конвертирует XML элемент в словарь"""
    result = {}
    
    if len(element) > 0:
        for child in element:
            child_data = xml_to_dict(child)
            
            if child.tag in result:
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_data)
            else:
                result[child.tag] = child_data
    else:
        return element.text
    
    return result

def parse_campaigns_data(xml_data):
    """Парсит данные кампаний из XML структуры"""
    campaigns = []
    
    if 'result' in xml_data and 'data' in xml_data['result']:
        data = xml_data['result']['data']
        
        for key, value in data.items():
            if key.startswith('row') and isinstance(value, dict):
                parse_campaign_value(value)
                campaigns.append(value)
                print(campaigns)
    
    return campaigns

def parse_campaign_value(value):
    """Парсит саму кампанию"""
    for field_name in [
                  'maxImpressions', 'maxClicks', 'maxImpressionsPerDay', 'maxClicksPerDay',
                  'maxImpressionsPerHour', 'maxClicksPerHour', 'impressionsHour', 
                  'clicksHour' , 'impressionsToday' , 'clicksToday' , 'impressionsAll' , 
                  'clicksAll' , 'priority', 'status', 
                  'level', 'cpm', 'cpc', 'kind_id', 'sectorID',
                  'rotationMethodID', 'trafficPercents', 'logicType']:
        value[field_name] = int(value[field_name]) if value[field_name] else 0

def get_campaigns():
    """Получить список кампаний из AdFox API"""
    
    auth_token = os.getenv('AUTH_TOKEN')
    if not auth_token:
        raise ValueError("AUTH_TOKEN не найден в переменных окружения")
    
    params = {
        'object': 'account',
        'action': 'list', 
        'actionObject': 'campaign',
        'dateAddedFrom': get_start_of_month(),
        'show': 'advanced',
        'limit': LIMIT
    }
    
    headers = {
        'Authorization': f'OAuth {auth_token}'
    }
    
    try:
        print(f"Выполняется запрос к {BASE_URL}")
        response = requests.get(BASE_URL, params=params, headers=headers)
        response.raise_for_status()
        
        # Определяем кодировку (обычно windows-1251 для AdFox)
        encoding = 'windows-1251'
        content_type = response.headers.get('Content-Type', '')
        if 'charset=' in content_type:
            encoding = content_type.split('charset=')[1].split(';')[0].strip()
        
        xml_content = response.content.decode(encoding)
        clean_xml = clean_xml_response(xml_content)
        
        root = ET.fromstring(clean_xml)
        result = xml_to_dict(root)
        
        return result
        
    except requests.RequestException as e:
        print(f"Ошибка при выполнении запроса: {e}")
        return None
    except ET.ParseError as e:
        print(f"Ошибка при парсинге XML: {e}")
        return None

if __name__ == "__main__":
    print("AdFox API Campaign Parser")
    print("=" * 40)
    
    # Установите ваш токен здесь для тестирования
    # os.environ['AUTH_TOKEN'] = 'your_token_here'
    
    data = get_campaigns()
    
    if data:
        campaigns = parse_campaigns_data(data)
        
        print(f"Получено кампаний: {len(campaigns)}")
        
        # Статистика по статусам
        statuses = {}
        for c in campaigns:
            status = c.get('status', 'unknown')
            statuses[status] = statuses.get(status, 0) + 1
        
        print("Статистика по статусам:")
        status_names = {'0': 'Активные', '1': 'Приостановленные', '2': 'Завершенные'}
        for status, count in statuses.items():
            name = status_names.get(status, f'Статус {status}')
            print(f"  {name}: {count}")
        
        # Сохранение в JSON
        with open('campaigns.json', 'w', encoding='utf-8') as f:
            json.dump(campaigns, f, ensure_ascii=False, indent=2)
        
        print("Данные сохранены в campaigns.json")
    else:
        print("Не удалось получить данные")
            
