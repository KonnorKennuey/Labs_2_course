# Лабораторная работа № 5, вариант 4

Проект обходит учебный сайт `quotes.toscrape.com` по тегам, переходит на
страницы авторов и сохраняет данные в SQLite.

## Установка

```powershell
python3.10 -m pip install -r requirements.txt
```

## Итоговый запуск

```powershell
python3.10 -m scrapy crawl quotes_tags `
  -a run_id=final `
  -O data/items.jsonl
```

## Проверка качества

```powershell
python3.10 quality/smoke_check.py --db data/crawl.db
```

В полном каталоге 100 цитат, но три из них не имеют тегов и поэтому недоступны
при обходе варианта 4. Ожидаемый результат: 97 уникальных цитат и 232 связи
«цитата–тег», всего 329 строк нормализованной базы.
