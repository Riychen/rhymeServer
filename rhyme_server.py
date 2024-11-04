




import os
import json
from collections import defaultdict
from flask import Flask, request, jsonify
from flask_caching import Cache
import pymorphy2
import random
import time
import nltk
from nltk.corpus import cmudict

# Инициализация Flask и кэша
app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache'})

# Инициализация pymorphy2
morph = pymorphy2.MorphAnalyzer()

# Фонетический словарь для английских слов из NLTK
nltk.download('cmudict')
phonetic_dict = cmudict.dict()

def normalize_word(word):
    """Нормализуем слово до его начальной формы, но избегаем изменений для коротких слов."""
    try:
        parsed = morph.parse(word)[0]
        if len(word) <= 4 and 'NOUN' in parsed.tag:
            return word  # Возвращаем исходное слово для коротких существительных
        return parsed.normal_form
    except Exception as e:
        print(f"Ошибка нормализации слова '{word}': {e}")
        return word

def word_to_phonetic(word):
    """Конвертируем слово в фонетическое представление с использованием NLTK (англ. примеры)."""
    try:
        return phonetic_dict[word][0]  # Получаем фонетическое представление слова
    except KeyError:
        return []

def create_rhyme_index(words):
    """Создаем индекс рифм на основе фонетического анализа или последних 2-4 букв."""
    print("Начинаем создание индекса рифм...")
    rhyme_index = defaultdict(list)
    
    for i, word in enumerate(words):
        if i % 10000 == 0:
            print(f"Обработано {i} слов")

        normalized_word = normalize_word(word)
        if len(normalized_word) > 2:
            # Индексация по последним 2-4 буквам
            for suffix_length in range(2, 5):
                if len(normalized_word) >= suffix_length:
                    suffix = normalized_word[-suffix_length:]
                    rhyme_index[suffix].append(normalized_word)
    
    print("Индексирование завершено.")
    return rhyme_index

def save_rhyme_index(rhyme_index, filename):
    """Сохраняем индекс в JSON файл."""
    print(f"Сохраняем индекс в файл {filename}...")
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(rhyme_index, f, ensure_ascii=False)
    print("Индекс сохранен.")

def load_rhyme_index(filename):
    """Загружаем индекс из JSON файла."""
    if os.path.exists(filename):
        print(f"Загружаем индекс из файла {filename}...")
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

# Загружаем слова и создаем/загружаем индекс
rhyme_index_file = 'rhyme_index.json'
rhyme_index = load_rhyme_index(rhyme_index_file)

if not rhyme_index:
    print("Загружаем слова из файла...")
    with open('russian.txt', 'r', encoding='cp1251') as f:
        words = [line.strip().lower() for line in f.readlines()]
    print(f"Загружено {len(words)} слов.")
    
    rhyme_index = create_rhyme_index(words)
    save_rhyme_index(rhyme_index, rhyme_index_file)  # Сохраняем созданный индекс в файл
else:
    print("Индекс успешно загружен.")

def find_rhymes(word):
    """Поиск рифм с учетом фонетики и последних букв."""
    normalized_word = normalize_word(word)
    print(f"Normalized word: {normalized_word}")

    word_len = len(normalized_word)
    possible_rhymes = []

    # Суффиксы различной длины для поиска
    suffix_lengths = [2, 3, 4]

    # Пытаемся найти рифмы по нескольким суффиксам
    for length in suffix_lengths:
        if word_len >= length:
            suffix = normalized_word[-length:]
            print(f"Suffix for search ({length}): {suffix}")
            rhymes_for_suffix = rhyme_index.get(suffix, [])
            possible_rhymes.extend(rhymes_for_suffix)

    print(f"Possible rhymes (before filtering duplicates): {possible_rhymes}")

    # Убираем дубликаты и исключаем нормализованное слово
    unique_rhymes = list(set(w for w in possible_rhymes if w != normalized_word))
    print(f"Unique rhymes before filtering: {unique_rhymes}")

    # Фильтрация по длине и фонетической схожести
    filtered_rhymes = []
    for rhyme in unique_rhymes:
        # Проверяем на близость по длине и окончанию
        if rhyme[-2:] == normalized_word[-2:] or rhyme[-3:] == normalized_word[-3:]:
            filtered_rhymes.append(rhyme)

    print(f"Filtered rhymes: {filtered_rhymes}")


    return filtered_rhymes

# Кэшируем результаты поиска рифм на 10 минут
@cache.memoize(timeout=600)
def get_cached_rhymes(word):
    return find_rhymes(word)

@app.route('/api/rhyme', methods=['POST'])
def get_rhymes():
    data = request.json
    print("Received data:", data)  # Логируем полученные данные

    word = data.get('word', '').strip().lower()

    if not word:
        return jsonify({"error": "Word is required"}), 400  # Если слово не передано, возвращаем ошибку

    # Получаем рифмы из кэша или выполняем расчет
    rhymes = get_cached_rhymes(word)

    return jsonify(rhymes)  # Возвращаем список рифм в JSON

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

