Техническое задание (ТЗ): LegalDocComparer MVP

1. Концепция проекта

Система для интеллектуального сравнения двух редакций нормативного или локального нормативного документа. В отличие от стандартного word diff, система понимает структуру документа (разделы, пункты, абзацы) и сопоставляет их даже при изменении нумерации, слиянии или разделении пунктов. Главная ценность — автоматическая подсветка юридических рисков (изменение сроков, сумм, модальности, появление отрицаний) с помощью цветовой маркировки (Green, Yellow, Red).

2. Стек технологий

Backend (Сервер & ML): Python + FastAPI. Идеально подходит для связки быстрых API и тяжелых ML/NLP скриптов.

NLP/ML Инструменты: python-docx (Word), pdfplumber/PyMuPDF (PDF), razdel / natasha / pymorphy3 (токенизация, лемматизация, NER), rapidfuzz (fuzzy string matching), sentence-transformers (векторное представление текста).

Frontend (Клиент): Next.js + TypeScript + Tailwind. Современный стандарт для создания быстрых, реактивных и красивых SPA/SSR интерфейсов.

База данных: SQLite. Достаточно для хакатонного MVP (хранение метаданных сравнений и кэширование блоков).

3. Архитектура обработки (Pipeline) и Данные

Процесс проходит через строгий pipeline:

document parsing: Извлечение структуры в список блоков. Блок содержит: id, number, heading, path, raw_text, clean_text, lemma_text, position.

block normalization: Лемматизация, очистка от мусора.

block alignment: Поиск кандидатов на основе скоринга (combination of exact/soft match number, heading/lexical/embedding similarity, entity overlap, position). Поддержка 1_to_1, 1_to_many, many_to_1, deleted, added, uncertain.

difference detection: Поиск текстовых и семантических отличий внутри сопоставленных блоков.

legal-risk classification: Rule-based + ML классификация:

RED: Критический триггер (модальность "может"->"обязан", числа, сроки, "не допускается").

YELLOW: Significant diff без явных триггеров или uncertain alignment.

GREEN: Редакционная правка, синонимы, полное совпадение.

report generation: Формирование JSON/HTML (и опционально DOCX) отчета.

4. Пользовательский интерфейс (UI)

Upload Page: Зона Drag&Drop для загрузки старой и новой редакций (.docx, best-effort .pdf).

Comparison Results (Dashboard): Summary cards (Total blocks, matched, changed, added, deleted, распределение green/yellow/red).

Side-by-side Panel: Главный экран. Две колонки (Было / Стало). Визуальная связь (линии или подсветка) между сопоставленными блоками.

Details Page/Modal: При клике на измененный блок — детальное объяснение (explainability score), почему присвоен конкретный риск, какие триггеры сработали.

Report Table: Сводная таблица с фильтрами по risk level (Red/Yellow/Green) и типу (changed/split/merge).

5. Как мы будем работать (Взаимодействие с ИИ)

ИИ предлагает архитектуру и структуру папок (frontend / backend монорепозиторий или два сервиса).

ИИ генерирует код модульно. На бэкенде обязательны модули: parsers/, preprocess/, alignment/, diff/, risk/, reports/, api/.

ИИ пишет тестируемый код. Настройка черного ящика не допускается — все алгоритмы вычисления скора и поиска рисков должны быть прозрачны и понятны жюри хакатона.

6. Этапы разработки (Roadmap)

Шаг 1. Архитектура: Проектирование схемы данных и взаимодействия сервисов.

Шаг 2. Структура репозитория: Создание каркаса проекта.

Шаг 3. Backend-код: Реализация парсеров, нормализации, алгоритма alignment (скоринг), движка рисков (rule_engine) и API-эндпоинтов (/upload, /compare, /report).

Шаг 4. Frontend-код: Верстка экранов загрузки, дашборда, side-by-side вьюера на Next.js.

Шаг 5. Финализация: Написание README (инструкция по запуску), добавление mock-данных для проверки, написание Unit-тестов для критических узлов (normalization, risk trigger detection, alignment scoring).