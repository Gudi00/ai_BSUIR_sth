from rapidfuzz import fuzz
from typing import List, Tuple, Optional
from ..models.block import DocumentBlock, ComparisonResult

class Aligner:
    def __init__(self, threshold: float = 60.0):
        self.threshold = threshold

    def align(self, old_blocks: List[DocumentBlock], new_blocks: List[DocumentBlock]) -> List[ComparisonResult]:
        results = []
        matched_new_indices = set()
        
        for old_block in old_blocks:
            best_match = None
            best_score = -1.0
            best_idx = -1
            
            # Ищем лучшего кандидата в новых блоках
            for i, new_block in enumerate(new_blocks):
                # Пропускаем уже идеально сопоставленные (можно добавить более сложную логику для 1_to_many)
                # if i in matched_new_indices: continue 
                
                score = self._calculate_score(old_block, new_block)
                
                if score > best_score:
                    best_score = score
                    best_idx = i
                    best_match = new_block
            
            if best_score >= self.threshold:
                matched_new_indices.add(best_idx)
                results.append(ComparisonResult(
                    old_block=old_block,
                    new_block=best_match,
                    risk_level="green" if best_score > 95 else "yellow", # Упрощенно
                    risk_explanation=None,
                    diff_type="equal" if best_score > 99 else "changed",
                    score=best_score
                ))
            else:
                # Блок удален
                results.append(ComparisonResult(
                    old_block=old_block,
                    new_block=None,
                    risk_level="red",
                    risk_explanation="Блок удален из новой редакции",
                    diff_type="deleted",
                    score=0.0
                ))
                
        # Добавляем новые блоки, которые не были сопоставлены (Added)
        for i, new_block in enumerate(new_blocks):
            if i not in matched_new_indices:
                results.append(ComparisonResult(
                    old_block=None,
                    new_block=new_block,
                    risk_level="red",
                    risk_explanation="Новый блок, отсутствующий в старой редакции",
                    diff_type="added",
                    score=0.0
                ))
                
        return results

    def _calculate_score(self, old: DocumentBlock, new: DocumentBlock) -> float:
        # 1. Скор за номер (высокий приоритет)
        number_score = 0.0
        if old.number and new.number:
            if old.number == new.number:
                number_score = 100.0
            elif old.number in new.number or new.number in old.number:
                number_score = 50.0
                
        # 2. Лексический скор (Fuzzy matching)
        # Сравниваем чистый текст
        lex_score = fuzz.ratio(old.clean_text.lower(), new.clean_text.lower())
        
        # 3. Позиционный скор (штраф за сильное смещение)
        # Для MVP проигнорируем, но в будущем полезно
        
        # Итоговый скор: взвешенная сумма
        # Если номера совпадают — это сильный сигнал
        if number_score == 100:
            return 0.4 * number_score + 0.6 * lex_score
        else:
            return lex_score

aligner = Aligner()
