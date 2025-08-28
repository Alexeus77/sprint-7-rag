import os
import json
import shutil
import re
import unicodedata
from itertools import permutations

def remove_accents(text: str) -> str:
    
    
    """Убираем ударения для сопоставления. Учитывает ё как е."""
    # Нормализуем строку, разбивая символы на базовые и диакритические
    normalized_text = unicodedata.normalize("NFD", text)
    
    # Убираем все диакритические символы (категория Mn)
    text_without_accents = "".join(c for c in normalized_text if unicodedata.category(c) != "Mn")
    
    # Дополнительно заменяем 'ё' и 'Ё' на 'е' и 'Е' для надёжности
    return text_without_accents.replace('ё', 'е').replace('Ё', 'Е')

def build_compound_name_regex(name: str) -> re.Pattern:
    """
    Создает регулярное выражение, которое ищет любое слово из имени для точного совпадения.
    """
    # Разделяем имя на слова по пробелу и запятой
    words = re.split(r'[ ,-]+', name)
    words = [w for w in words if w]  # Убираем пустые строки
    if not words:
        return re.compile(re.escape(name), re.IGNORECASE)
    # Ищем любое отдельное слово (границы слова)
    pattern = r'\b(' + '|'.join(re.escape(w) for w in words) + r')\b'
    return re.compile(pattern, re.IGNORECASE)

def rename_and_replace():
    """
    Основная логика скрипта.
    Добавлена обработка папки 'planets' с выводом в отдельную папку 'output_planets'.
    """
    input_folder = "characters"
    output_folder = "output_characters"
    planets_input_folder = "planets"
    planets_output_folder = "output_planets"
    mapping_file = "mapping.json"
    planets_mapping_file = "planets_mapping.json"

    # Функция обработки одной папки
    def process_folder(input_folder, output_folder, mapping, processed_mapping):
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            print(f"Создана новая папка для результатов: '{output_folder}'.")

        processed_count = 0
        for filename in os.listdir(input_folder):
            old_filepath = os.path.join(input_folder, filename)
            if os.path.isfile(old_filepath):
                new_filename = filename
                try:
                    with open(old_filepath, 'r', encoding='utf-8') as f:
                        file_content = f.read()
                except Exception as e:
                    print(f"Ошибка при чтении файла '{filename}': {e}. Пропускаю.")
                    continue

                content_to_process = remove_accents(file_content)

                for search_pattern, new_value in processed_mapping.items():
                    normalized_filename = remove_accents(new_filename)
                    if search_pattern.search(normalized_filename):
                        new_filename = search_pattern.sub(new_value, normalized_filename)
                    if search_pattern.search(content_to_process):
                        file_content = search_pattern.sub(new_value, remove_accents(file_content))

                new_filepath = os.path.join(output_folder, new_filename)
                try:
                    with open(new_filepath, 'w', encoding='utf-8') as f:
                        f.write(file_content)
                    print(f"  Файл '{filename}' обработан -> сохранён как '{new_filename}'.")
                    processed_count += 1
                except Exception as e:
                    print(f"Ошибка при записи файла '{new_filepath}': {e}. Пропускаю.")
        print(f"\nОбработка завершена. Всего обработано файлов: {processed_count}.")

    # Загрузка маппингов
    with open(mapping_file, 'r', encoding='utf-8') as f:
        mapping = json.load(f)
    print(f"Файл маппинга '{mapping_file}' успешно загружен.")

    with open(planets_mapping_file, 'r', encoding='utf-8') as fp:
        planets_mapping = json.load(fp)
    print(f"Файл маппинга '{planets_mapping_file}' успешно загружен.")

    # Создаем словарь для обработанных шаблонов
    processed_mapping = {}
    for key, value in planets_mapping.items():
        search_pattern = re.compile(re.escape(key), re.IGNORECASE)
        processed_mapping[search_pattern] = value

    for key, value in mapping.items():
        key_words = re.split(r'[ ,-]+', key)
        key_words = [w for w in key_words if w]
        value_words = re.split(r'[ ,-]+', value)
        value_words = [w for w in value_words if w]
        if len(key_words) > 1 and len(key_words) == len(value_words):
            for k_word, v_word in zip(key_words, value_words):
                search_pattern = re.compile(r'\b' + re.escape(remove_accents(k_word)) + r'(\w*)', re.IGNORECASE)
                processed_mapping[search_pattern] = lambda m, v_word=v_word: v_word + m.group(1)
        else:
            search_pattern = re.compile(r'\b' + re.escape(remove_accents(key)) + r'(\w*)', re.IGNORECASE)
            processed_mapping[search_pattern] = lambda m, value=value: value + m.group(1)
        if len(key_words) > 1 and len(key_words) == len(value_words):
            for k_word, v_word in zip(key_words, value_words):
                search_pattern = re.compile(r'\b' + re.escape(remove_accents(k_word)) + r'\w*', re.IGNORECASE)
                processed_mapping[search_pattern] = v_word
        else:
            search_pattern = re.compile(re.escape(remove_accents(key)), re.IGNORECASE)
            processed_mapping[search_pattern] = value

    print("\nНачинаю обработку файлов персонажей...")
    process_folder(input_folder, output_folder, mapping, processed_mapping)

    # Обработка папки планет
    print("\nНачинаю обработку файлов планет...")
    planets_processed_mapping = {}
    for key, value in planets_mapping.items():
        search_pattern = re.compile(re.escape(key), re.IGNORECASE)
        planets_processed_mapping[search_pattern] = value
    process_folder(planets_input_folder, planets_output_folder, planets_mapping, planets_processed_mapping)
    input_folder = "characters"
    output_folder = "output_characters"
    mapping_file = "mapping.json"
    planets_mapping_file = "planets_mapping.json"

    with open(mapping_file, 'r', encoding='utf-8') as f:
        mapping = json.load(f)
    print(f"Файл маппинга '{mapping_file}' успешно загружен.")

    with open(planets_mapping_file, 'r', encoding='utf-8') as fp:
        planets_mapping = json.load(fp)
    print(f"Файл маппинга '{planets_mapping_file}' успешно загружен.")
    # Обработка папки планет с использованием characters mapping
    print("\nНачинаю обработку файлов планет с characters mapping...")
    processed_count = 0

    for filename in os.listdir(planets_input_folder):
        old_filepath = os.path.join(planets_input_folder, filename)

        if os.path.isfile(old_filepath):
            new_filename = filename

            try:
                with open(old_filepath, 'r', encoding='utf-8') as f:
                    file_content = f.read()
            except Exception as e:
                print(f"Ошибка при чтении файла '{filename}': {e}. Пропускаю.")
                continue

            content_to_process = remove_accents(file_content)

            for search_pattern, new_value in processed_mapping.items():
                normalized_filename = remove_accents(new_filename)
                if search_pattern.search(normalized_filename):
                    new_filename = search_pattern.sub(new_value, normalized_filename)

                if search_pattern.search(content_to_process):
                    file_content = search_pattern.sub(new_value, remove_accents(file_content))

            new_filepath = os.path.join(planets_output_folder, new_filename)

            try:
                with open(new_filepath, 'w', encoding='utf-8') as f:
                    f.write(file_content)
                print(f"  Файл '{filename}' обработан -> сохранён как '{new_filename}'.")
                processed_count += 1
            except Exception as e:
                print(f"Ошибка при записи файла '{new_filepath}': {e}. Пропускаю.")

    print(f"\nОбработка планет завершена. Всего обработано файлов: {processed_count}.")
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"Создана новая папка для результатов: '{output_folder}'.")

    # Создаем словарь для обработанных шаблонов
    processed_mapping = {}

    # Добавляем обработку planets_mapping: точная замена как в файле
    for key, value in planets_mapping.items():
        search_pattern = re.compile(re.escape(key), re.IGNORECASE)
        processed_mapping[search_pattern] = value
        
    for key, value in mapping.items():
        # Разделяем ключ и значение на слова
        key_words = re.split(r'[ ,-]+', key)
        key_words = [w for w in key_words if w]
        value_words = re.split(r'[ ,-]+', value)
        value_words = [w for w in value_words if w]
        # Сопоставляем окончания: заменяем только точное совпадение основы, оставляя окончания
        if len(key_words) > 1 and len(key_words) == len(value_words):
            for k_word, v_word in zip(key_words, value_words):
            # Ищем основу слова и сохраняем окончание
                search_pattern = re.compile(r'\b' + re.escape(remove_accents(k_word)) + r'(\w*)', re.IGNORECASE)
                # Используем lambda для замены основы, сохраняя окончание
                processed_mapping[search_pattern] = lambda m, v_word=v_word: v_word + m.group(1)
        else:
            # Обычная замена для одного слова/фразы или если количество слов не совпадает
            search_pattern = re.compile(r'\b' + re.escape(remove_accents(key)) + r'(\w*)', re.IGNORECASE)
            processed_mapping[search_pattern] = lambda m, value=value: value + m.group(1)

        # Если количество слов совпадает, заменяем по позициям
        if len(key_words) > 1 and len(key_words) == len(value_words):
            for k_word, v_word in zip(key_words, value_words):
                search_pattern = re.compile(r'\b' + re.escape(remove_accents(k_word)) + r'\w*', re.IGNORECASE)
                processed_mapping[search_pattern] = v_word
        else:
            # Обычная замена для одного слова/фразы или если количество слов не совпадает
            search_pattern = re.compile(re.escape(remove_accents(key)), re.IGNORECASE)
            processed_mapping[search_pattern] = value
        
    print("\nНачинаю обработку файлов...")
    processed_count = 0
    
    for filename in os.listdir(input_folder):
        old_filepath = os.path.join(input_folder, filename)
        
        if os.path.isfile(old_filepath):
            new_filename = filename
            
            try:
                with open(old_filepath, 'r', encoding='utf-8') as f:
                    file_content = f.read()
            except Exception as e:
                print(f"Ошибка при чтении файла '{filename}': {e}. Пропускаю.")
                continue

            content_to_process = remove_accents(file_content)
            
            for search_pattern, new_value in processed_mapping.items():
                # Проверяем и переименовываем файл
                normalized_filename = remove_accents(new_filename)
                if search_pattern.search(normalized_filename):
                    new_filename = search_pattern.sub(new_value, normalized_filename)
                    
                # Проверяем и заменяем текст
                if search_pattern.search(content_to_process):
                    file_content = search_pattern.sub(new_value, remove_accents(file_content))

            new_filepath = os.path.join(output_folder, new_filename)
            
            try:
                with open(new_filepath, 'w', encoding='utf-8') as f:
                    f.write(file_content)
                print(f"  Файл '{filename}' обработан -> сохранён как '{new_filename}'.")
                processed_count += 1
            except Exception as e:
                print(f"Ошибка при записи файла '{new_filepath}': {e}. Пропускаю.")
    
    print(f"\nОбработка завершена. Всего обработано файлов: {processed_count}.")

if __name__ == "__main__":
    rename_and_replace()