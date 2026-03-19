  1. Терминал №1: Бэкенд (API)
  Убедитесь, что вы находитесь в корневой папке проекта (AI BSUIR).

    1 # 1. Активируйте виртуальное окружение
    2 source venv/bin/activate
    3
    4 # 2. Установите зависимости (если еще не сделано)
    5 pip install -r backend/requirements.txt
    6
    7 # 3. Решение проблемы с pkg_resources (обязательно для Python 3.12+)
    8 pip install "setuptools<70"
    9
   10 # 4. Запустите сервер (я изменил порт на 8001, так как 8000 часто занят)
   11 python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8001 --reload
  Если увидите Application startup complete, значит бэкенд готов.

  ---

  2. Терминал №2: Фронтенд (Интерфейс)
  Перейдите в папку frontend.

   1 # 1. Перейдите в папку фронтенда
   2 cd frontend
   3
   4 # 2. Установите зависимости (если запускаете впервые)
   5 npm install
   6
   7 # 3. Запустите сервер разработки
   8 npm run dev -- -p 3000
  После этого откройте в браузере: http://localhost:3000 (http://localhost:3000)




# LegalDocComparer MVP

Интеллектуальная система сравнения юридических документов с автоматическим выявлением рисков.

## Возможности
- **Умное сопоставление (Alignment):** Сопоставляет пункты даже при изменении нумерации.
- **Детекция рисков:** Цветовая маркировка (Green, Yellow, Red) изменений.
- **Explainability:** Текстовое пояснение, почему системе не понравилась правка (изменение сроков, модальности, отрицания).
- **Поддержка форматов:** `.docx` и `.pdf`.

## Технологический стек
- **Backend:** FastAPI, Natasha (NLP), RapidFuzz, Python-Docx, PDFPlumber.
- **Frontend:** Next.js, TypeScript, Tailwind CSS.

## Как запустить

### 1. Бэкенд
```bash
# Убедитесь, что вы в корне проекта
source venv/bin/activate
pip install -r backend/requirements.txt
# Если возникнут ошибки с pkg_resources:
pip install "setuptools<70"
uvicorn backend.app.main:app --host 0.0.0.0 --port 8001
```

### 2. Фронтенд
```bash
cd frontend
npm install
npm run dev
```
Откройте [http://localhost:3000](http://localhost:3000).

## Логика классификации рисков (MVP)
- **RED:** Изменение дат, сумм, процентов; смена модальности ("обязан" <-> "вправе"); появление/исчезновение частицы "не".
- **YELLOW:** Значительные текстовые изменения без явных триггеров.
- **GREEN:** Редакционные правки, синонимы.
