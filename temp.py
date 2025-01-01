import json

with open("lib_list.json", "r", encoding='utf-8') as f:
    json_data = json.load(f)

for key, value in json_data.items():
    a = value.get('안산도서관')
    if a:
        print(key, a)
        break
