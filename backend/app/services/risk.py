import re
from typing import Optional, Tuple
from ..models.block import ComparisonResult

class RiskEngine:
    # Ключевые слова для модальности
    MODAL_WORDS = {
        "обязан", "должен", "вправе", "может", 
        "необходимо", "следует", "допускается", "запрещается"
    }

    def analyze(self, comparison: ComparisonResult) -> ComparisonResult:
        if comparison.diff_type in ["added", "deleted"]:
            comparison.risk_level = "red"
            return comparison

        if comparison.diff_type == "equal":
            return comparison

        old_text = comparison.old_block.clean_text.lower()
        new_text = comparison.new_block.clean_text.lower()

        # 1. Игнорирование дат в шапке (позиция < 5 и нет номера пункта)
        is_header = comparison.new_block.position < 5 and not comparison.new_block.number
        if is_header:
            # Проверяем, изменились ли только даты (напр. 12.03.2024 -> 19.03.2026)
            date_pattern = r'\d{2}\.\d{2}\.\d{4}'
            old_dates = set(re.findall(date_pattern, old_text))
            new_dates = set(re.findall(date_pattern, new_text))

            if old_dates != new_dates:
                # Убираем даты и проверяем, осталось ли что-то еще
                old_no_dates = re.sub(date_pattern, '', old_text).strip()
                new_no_dates = re.sub(date_pattern, '', new_text).strip()
                if old_no_dates == new_no_dates:
                    comparison.risk_level = "green"
                    comparison.risk_explanation = "Изменение даты документа в шапке (метаданные)"
                    return comparison

        # 2. Умный анализ чисел (Сроки и Суммы)
        old_nums = [int(n) for n in re.findall(r'\d+', old_text)]
        new_nums = [int(n) for n in re.findall(r'\d+', new_text)]

        if old_nums != new_nums and len(old_nums) == len(new_nums) == 1:
            old_v, new_v = old_nums[0], new_nums[0]

            # Контекст: Сроки (дней, суток, часов)
            is_time = any(w in old_text for w in ["дней", "дня", "день", "суток", "сутки", "срок", "течение"])
            # Контекст: Деньги (рублей, сумма, штраф)
            is_money = any(w in old_text for w in ["рубл", "руб", "сумм", "штраф", "выплат"])

            if is_time:
                if new_v < old_v:
                    comparison.risk_level = "red"
                    comparison.risk_explanation = f"Срок сокращен ({old_v} -> {new_v}): требование стало ЖЕСТЧЕ"
                else:
                    comparison.risk_level = "yellow"
                    comparison.risk_explanation = f"Срок увеличен ({old_v} -> {new_v}): требование стало МЯГЧЕ"
                return comparison

            if is_money:
                if new_v > old_v:
                    comparison.risk_level = "red"
                    comparison.risk_explanation = f"Сумма увеличена ({old_v} -> {new_v}): финансовая нагрузка ВЫШЕ"
                else:
                    comparison.risk_level = "yellow"
                    comparison.risk_explanation = f"Сумма уменьшена ({old_v} -> {new_v}): финансовая нагрузка НИЖЕ"
                return comparison

        # 3. Базовая проверка (Числа, "НЕ", Модальность) как раньше
        if set(old_nums) != set(new_nums):
            comparison.risk_level = "red"
            comparison.risk_explanation = f"Изменение числовых значений: {set(old_nums)} -> {set(new_nums)}"
            return comparison
        # 2. Появление или исчезновение частицы "не" (RED)
        old_has_negation = " не " in f" {old_text} "
        new_has_negation = " не " in f" {new_text} "

        if old_has_negation != new_has_negation:
            comparison.risk_level = "red"
            comparison.risk_explanation = "Появление или исчезновение отрицания ('не')"
            return comparison

        # 3. Изменение модальных слов (RED)
        old_modals = {w for w in self.MODAL_WORDS if f" {w} " in f" {old_text} "}
        new_modals = {w for w in self.MODAL_WORDS if f" {w} " in f" {new_text} "}

        if old_modals != new_modals:
            comparison.risk_level = "red"
            comparison.risk_explanation = f"Изменение модальности: {old_modals} -> {new_modals}"
            return comparison

        # 4. Классификация Green vs Yellow
        if comparison.score > 90:
            comparison.risk_level = "green"
            comparison.risk_explanation = "Редакционная правка или замена на синонимы"
        else:
            comparison.risk_level = "yellow"
            comparison.risk_explanation = "Значимое изменение текста, требующее проверки юристом"

        return comparison


risk_engine = RiskEngine()
