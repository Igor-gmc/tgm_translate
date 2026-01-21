import csv

with open('data_words\mueller_dictionary.csv', 'r', encoding='utf-8') as f:
    data = csv.reader(f)

    for line in data:
        print(line)
