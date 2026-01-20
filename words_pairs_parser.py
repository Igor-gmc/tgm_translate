import csv
import re
from typing import Generator


def read_raw_dictionary(file_path: str,
                        delimiter: str = "_____",
                        buffer_size: int = 4096) -> Generator[str, None, None]:
    """
    Читает файл частями по разделителю.
    Возвращает генератор строк (записей словаря).
    """
    buffer = ""
    with open(file_path, 'r', encoding='UTF-8') as f:
        while True:
            chunk = f.read(buffer_size)

            if not chunk:
                if (stripped := buffer.strip()):
                    yield stripped
                break

            buffer += chunk

            while delimiter in buffer:
                part, buffer = buffer.split(delimiter, 1)
                if (stripped := part.strip()):
                    yield stripped


def parse_entry(entry: str) -> dict | None:
    """
    Парсит одну запись словаря.
    Возвращает словарь с полями: word, transcription, translations
    """
    lines = [line.strip() for line in entry.splitlines() if line.strip()]

    if not lines:
        return None

    # Первая строка может быть буквой алфавита (A, B, C...)
    # Пропускаем одиночные буквы
    start_idx = 0
    if len(lines[0]) == 1 and lines[0].isalpha():
        start_idx = 1

    if start_idx >= len(lines):
        return None

    # Извлекаем слово (может быть на первой или второй строке)
    first_line = lines[start_idx]

    # Пропускаем записи без явного слова
    if first_line.startswith('[') or first_line.startswith('_'):
        return None

    # Проверяем, есть ли транскрипция на первой строке (формат: "word [transcription] ...")
    if '[' in first_line:
        # Слово - всё до первой квадратной скобки
        word = first_line.split('[')[0].strip()
        # Остальной текст начинается с транскрипции
        rest_text = first_line[first_line.index('['):] + ' ' + ' '.join(lines[start_idx + 1:])
    else:
        word = first_line
        # Собираем остальной текст
        rest_text = ' '.join(lines[start_idx + 1:])

    # Пропускаем пустые слова
    if not word:
        return None

    # Извлекаем транскрипцию (первую найденную)
    transcription_match = re.search(r'\[([^\]]+)\]', rest_text)
    transcription = f"[{transcription_match.group(1)}]" if transcription_match else ""
    # Убираем кавычки вокруг транскрипции (если есть)
    transcription = transcription.strip('"\'""')
    # Убираем запятые внутри транскрипции (чтобы CSV не добавлял кавычки)
    transcription = transcription.replace(',', '')

    # Извлекаем переводы
    translations = extract_translations(rest_text)

    if not translations:
        return None

    return {
        'word': word,
        'transcription': transcription,
        'translations': translations
    }


def extract_translations(text: str) -> list[str]:
    """
    Извлекает переводы из текста записи.
    Обрабатывает нумерованные переводы (1), 2)...) и простые переводы.
    """
    translations = []

    # Удаляем транскрипцию
    text = re.sub(r'\[[^\]]+\]', '', text)

    # Удаляем метки частей речи в начале (_n., _v., _a., etc.)
    text = re.sub(r'^_[a-z]+\.?\s*', '', text.strip())

    # Проверяем наличие нумерованных переводов
    numbered_pattern = r'(\d+\))\s*'
    if re.search(numbered_pattern, text):
        # Разбиваем по номерам
        parts = re.split(numbered_pattern, text)

        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                # clean_translation возвращает список
                cleaned_list = clean_translation(parts[i + 1])
                translations.extend(cleaned_list)
    else:
        # Простой перевод без нумерации
        cleaned_list = clean_translation(text)
        translations.extend(cleaned_list)

    return translations


def clean_translation(text: str) -> list[str]:
    """
    Очищает текст перевода от лишних символов и меток.
    Возвращает список переводов (разбивает по ', ' и '; ').
    """
    # Удаляем все метки типа _амер., _библ., _греч. _миф. и т.д.
    text = re.sub(r'_[a-zа-яё]+\.?\s*', '', text)

    # Удаляем вложенные пояснения типа (*) ...
    text = re.sub(r'\*\)[^;,]*', '', text)

    # Удаляем ссылки на другие слова (= something)
    text = re.sub(r'=\s*\w+', '', text)

    # Удаляем скобки с пояснениями типа (attr. ...), (употр. как ...)
    text = re.sub(r'\([^)]*\)', '', text)

    # Удаляем фигурные скобки и их содержимое {ср. forty-niner}
    text = re.sub(r'\{[^}]*\}', '', text)
    # Удаляем незакрытые фигурные скобки до конца строки
    text = re.sub(r'\{.*$', '', text)

    # Удаляем конструкции типа "1. ... 2. ..."
    text = re.sub(r'\d+\.\s*', '', text)

    # Очищаем от лишних пробелов
    text = ' '.join(text.split())

    # Разбиваем по разделителям ", " и "; "
    parts = re.split(r'[;,]\s+', text)

    # Очищаем каждую часть и фильтруем пустые
    result = []
    for part in parts:
        cleaned = part.strip()
        # Удаляем все кавычки (внутри и снаружи)
        cleaned = re.sub(r'["\'"«»]+', '', cleaned)
        # Удаляем знаки препинания в начале (:, -)
        cleaned = re.sub(r'^[\s:,\-–—]+', '', cleaned)
        # Удаляем знаки препинания в конце
        cleaned = re.sub(r'[\s:;\-–—]+$', '', cleaned)
        # Пропускаем пустые и слишком короткие (1 символ)
        if cleaned and len(cleaned) > 1:
            result.append(cleaned)

    return result


def write_to_csv(input_file: str, output_file: str):
    """
    Обрабатывает словарь и записывает результат в CSV файл.
    Каждый перевод слова записывается отдельной строкой с уникальным id.
    """
    word_id = 0

    with open(output_file, "w", encoding="UTF-8", newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["id", "word", "transcription", "translation"])

        for entry in read_raw_dictionary(input_file):
            parsed = parse_entry(entry)

            if not parsed:
                continue

            word = parsed['word']
            transcription = parsed['transcription']

            for translation in parsed['translations']:
                word_id += 1
                row_id = f"id_{word_id:06d}"
                # Приводим слово и перевод к нижнему регистру
                writer.writerow([row_id, word.lower(), transcription, translation.lower()])

    print(f"Записано {word_id} пар слово-перевод в {output_file}")


if __name__ == "__main__":
    write_to_csv("mueller-base.txt", "mueller_dictionary.csv")
