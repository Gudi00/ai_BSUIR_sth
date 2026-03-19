from typing import List, Union
from ..models.block import ComparisonResult, CollapsedSection, DiffType, RiskLevel

class SmartCollapse:
    @staticmethod
    def collapse_long_added_tails(results: List[ComparisonResult], min_blocks: int = 3) -> List[Union[ComparisonResult, CollapsedSection]]:
        """
        Группирует длинные последовательности добавленных блоков без триггеров риска в CollapsedSection.
        """
        final_output = []
        i = 0
        n = len(results)
        
        while i < n:
            current_res = results[i]
            
            # Проверяем, является ли текущий блок кандидатом на коллапс:
            # 1. Это именно добавление (ADDED)
            # 2. У него нет триггеров юридического риска (Explainable AI layer)
            # 3. Он не является результатом слияния или разделения (уже покрыто DiffType)
            is_candidate = (
                current_res.diff_type == DiffType.ADDED and 
                not current_res.risk_triggers
            )
            
            if is_candidate:
                # Ищем конец диапазона
                j = i
                candidate_range = []
                
                while j < n:
                    next_res = results[j]
                    if (next_res.diff_type == DiffType.ADDED and not next_res.risk_triggers):
                        candidate_range.append(next_res)
                        j += 1
                    else:
                        break
                
                # Если диапазон достаточно длинный, схлопываем его
                if (j - i) >= min_blocks:
                    risk_dist = {RiskLevel.GREEN: 0, RiskLevel.YELLOW: 0, RiskLevel.RED: 0}
                    for item in candidate_range:
                        risk_dist[item.risk_level] += 1
                        
                    collapsed = CollapsedSection(
                        start_index=i,
                        end_index=j - 1,
                        block_count=len(candidate_range),
                        reason_code="ADDED_ONLY_WITHOUT_CONTRAST_TRIGGERS",
                        summary_text=f"Далее в новом документе: {len(candidate_range)} добавленных блоков (без контрастных изменений до следующей точки)",
                        risk_distribution=risk_dist,
                        items=candidate_range
                    )
                    final_output.append(collapsed)
                    i = j # Прыгаем вперед
                else:
                    # Слишком короткий диапазон, добавляем блоки как есть
                    final_output.append(results[i])
                    i += 1
            else:
                # Обычный блок (изменение или наличие риска) — не трогаем
                final_output.append(current_res)
                i += 1
                
        return final_output

ui_service = SmartCollapse()
