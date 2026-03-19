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
        if comparison.diff_type in ["added", "deleted", "equal"]:
            return comparison

        old_text = comparison.old_block.clean_text.lower()
        new_text = comparison.new_block.clean_text.lower()

        # 1. Поиск изменений в числах
        old_numbers = set(re.findall(r'\d+', old_text))
        new_numbers = set(re.findall(r'\d+', new_text))
        
        if old_numbers != new_numbers:
            comparison.risk_level = "red"
            comparison.risk_explanation = f"Изменение числовых значений: {old_numbers} -> {new_numbers}"
            return comparison

        # 2. Появление или исчезновение частицы "не"
        old_has_negation = " не " in f" {old_text} "
        new_has_negation = " не " in f" {new_text} "
        
        if old_has_negation != new_has_negation:
            comparison.risk_level = "red"
            comparison.risk_explanation = "Появление или исчезновение отрицания ('не')"
            return comparison

        # 3. Изменение модальных слов
        old_modals = {w for w in self.MODAL_WORDS if f" {w} " in f" {old_text} "}
        new_modals = {w for w in self.MODAL_WORDS if f" {w} " in f" {new_text} "}
        
        if old_modals != new_modals:
            comparison.risk_level = "red"
            comparison.risk_explanation = f"Изменение модальности: {old_modals} -> {new_modals}"
            return comparison

        # 4. Если значительных триггеров нет, но текст изменен
        if comparison.score < 95:
            comparison.risk_level = "yellow"
            comparison.risk_explanation = "Значительное текстовое различие без явных триггеров риска"
        else:
            comparison.risk_level = "green"
            comparison.risk_explanation = "Незначительные правки или синонимы"

        return comparison

risk_engine = RiskEngine()
