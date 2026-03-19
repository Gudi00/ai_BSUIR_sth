import re
import torch
from typing import Optional, Tuple, List, Dict, Any
from sentence_transformers import util
from ..models.block import ComparisonResult, RiskLevel, RiskTrigger, DiffType
from .vector_store import vector_service
from .preprocess import preprocessor

class RiskEngine:
    # Словарь триггеров с категориями и весами (для расширяемости)
    TRIGGER_WORDS = {
        "обязан": "Modality/Obligation",
        "должен": "Modality/Obligation",
        "вправе": "Modality/Permission",
        "может": "Modality/Permission",
        "вправе": "Modality/Permission",
        "необходимо": "Modality/Requirement",
        "следует": "Modality/Requirement",
        "допускается": "Modality/Permission",
        "запрещается": "Modality/Prohibition",
        "не допускается": "Modality/Prohibition",
        "штраф": "Financial/Penalty",
        "неустойка": "Financial/Penalty",
        "пени": "Financial/Penalty",
        "срок": "Temporal/Deadline",
        "дней": "Temporal/Deadline",
        "календарных": "Temporal/Deadline",
        "рабочих": "Temporal/Deadline",
    }

    def _get_triggers(self, text: str) -> Dict[str, str]:
        """Находит все триггерные слова в лемматизированном тексте."""
        found = {}
        # Используем лемматизацию для точного поиска
        lemmas = preprocessor.lemmatize(text).lower().split()
        for word, category in self.TRIGGER_WORDS.items():
            # Триггер может состоять из нескольких слов (напр. "не допускается")
            if " " in word:
                if word in text.lower():
                    found[word] = category
            elif word in lemmas:
                found[word] = category
        return found

    def _get_semantic_similarity(self, text1: str, text2: str) -> float:
        """Вычисляет косинусное сходство между двумя текстами."""
        model = vector_service._get_model()
        emb1 = model.encode(text1, convert_to_tensor=True)
        emb2 = model.encode(text2, convert_to_tensor=True)
        return float(util.cos_sim(emb1, emb2)[0][0])

    def _classify_change_type_llm(self, old_text: str, new_text: str) -> Tuple[str, str]:
        """
        Имитация вызова LLM для классификации типа изменения и краткого объяснения.
        В реальном проекте здесь будет вызов OpenAI/Anthropic/Local LLM.
        """
        # TODO: Интегрировать реальный вызов LLM
        # Для хакатона: детерминированная логика или заглушка с "умным" видом
        
        # Пример логики "псевдо-LLM"
        if not old_text: return "Новое правило", "Добавлен новый пункт в документ."
        
        diff_len = len(new_text) - len(old_text)
        if diff_len > 50:
            return "Расширение", "Добавлены уточняющие детали и дополнительные условия."
        elif diff_len < -30:
            return "Ограничение", "Формулировка стала более лаконичной, возможно сокращение объема прав или обязанностей."
        else:
            return "Уточнение", "Изменены формулировки для устранения неоднозначности."

    def analyze(self, comparison: ComparisonResult) -> ComparisonResult:
        if comparison.diff_type == DiffType.EQUAL:
            comparison.risk_level = RiskLevel.GREEN
            return comparison

        # Если это добавление или удаление без соответствия
        if comparison.diff_type in [DiffType.ADDED, DiffType.DELETED]:
            text = comparison.new_block.clean_text if comparison.new_block else comparison.old_block.clean_text
            triggers = self._get_triggers(text)
            
            for word, cat in triggers.items():
                comparison.risk_triggers.append(RiskTrigger(
                    category=cat,
                    fragment=word,
                    explanation=f"Обнаружен триггер '{word}' в {comparison.diff_type.value} блоке."
                ))
            
            # Если есть триггеры в новом/удаленном блоке - это Red
            comparison.risk_level = RiskLevel.RED if triggers else RiskLevel.YELLOW
            comparison.change_summary, _ = self._classify_change_type_llm(
                comparison.old_block.clean_text if comparison.old_block else "",
                comparison.new_block.clean_text if comparison.new_block else ""
            )
            return comparison

        # --- СЕМАНТИЧЕСКИЙ АНАЛИЗ (MODIFIED) ---
        old_text = comparison.old_block.clean_text
        new_text = comparison.new_block.clean_text
        
        # 1. Similarity
        similarity = self._get_semantic_similarity(old_text, new_text)
        comparison.score = similarity
        
        # 2. Trigger Analysis
        old_triggers = self._get_triggers(old_text)
        new_triggers = self._get_triggers(new_text)
        
        # Сравниваем изменения в триггерах
        added_triggers = set(new_triggers.keys()) - set(old_triggers.keys())
        removed_triggers = set(old_triggers.keys()) - set(new_triggers.keys())
        
        for word in added_triggers:
            comparison.risk_triggers.append(RiskTrigger(
                category=new_triggers[word],
                fragment=word,
                explanation=f"Добавлен триггер: '{word}'"
            ))
            
        for word in removed_triggers:
            comparison.risk_triggers.append(RiskTrigger(
                category=old_triggers[word],
                fragment=word,
                explanation=f"Исчез триггер: '{word}'"
            ))

        # 3. Decision Logic (Deterministic)
        # 🔴 RED: Изменились триггеры ИЛИ сходство < 0.7
        if added_triggers or removed_triggers or similarity < 0.7:
            comparison.risk_level = RiskLevel.RED
            comparison.alignment_reason = "Критическое изменение смысла или модальности"
        # 🟡 YELLOW: Сходство 0.7 - 0.9
        elif similarity < 0.92:
            comparison.risk_level = RiskLevel.YELLOW
            comparison.alignment_reason = "Значительное перефразирование"
        # 🟢 GREEN: Сходство > 0.92
        else:
            comparison.risk_level = RiskLevel.GREEN
            comparison.alignment_reason = "Редакционная правка / Синонимы"

        # 4. LLM Explainability
        change_type, llm_explanation = self._classify_change_type_llm(old_text, new_text)
        comparison.change_summary = f"{change_type}: {llm_explanation}"

        # 5. RAG Legal Context (Проверка конфликтов с иерархией)
        best_matches = vector_service.get_best_matches_per_level(
            new_text, 
            comparison.new_block.hierarchy_level,
            threshold=0.6
        )
        comparison.legal_context = [{"level": l, **m} for l, m in best_matches.items()]

        return comparison

risk_engine = RiskEngine()
