from natasha import (
    Segmenter, MorphVocab, NewsEmbedding, 
    NewsMorphTagger, Doc
)
from typing import List
import re
import difflib

class TextPreprocessor:
    def __init__(self):
        self.segmenter = Segmenter()
        self.morph_vocab = MorphVocab()
        self.emb = NewsEmbedding()
        self.morph_tagger = NewsMorphTagger(self.emb)
        
    def clean(self, text: str) -> str:
        # Убираем лишние пробелы и переносы
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def lemmatize(self, text: str) -> str:
        doc = Doc(text)
        doc.segment(self.segmenter)
        doc.tag_morph(self.morph_tagger)
        
        lemmas = []
        for token in doc.tokens:
            token.lemmatize(self.morph_vocab)
            lemmas.append(token.lemma)
            
        return " ".join(lemmas)

    def extract_entities(self, text: str) -> List[dict]:
        # Для MVP пока просто возвращаем пустой список, 
        # позже добавим NER для извлечения дат и сумм.
        return []

    def generate_word_diff(self, old_text: str, new_text: str) -> tuple[str, str]:
        """Генерирует word-level diff. Возвращает (highlighted_old, highlighted_new)"""
        # Если одного из текстов нет - возвращаем как есть
        if not old_text: return ("", f"**{new_text}**")
        if not new_text: return (f"~~{old_text}~~", "")
        
        # Разделяем по словам (сохраняя пунктуацию)
        old_words = re.findall(r'\w+|[^\w\s]', old_text, re.UNICODE)
        new_words = re.findall(r'\w+|[^\w\s]', new_text, re.UNICODE)
        
        matcher = difflib.SequenceMatcher(None, old_words, new_words)
        highlighted_old = []
        highlighted_new = []
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                highlighted_old.append(" ".join(old_words[i1:i2]))
                highlighted_new.append(" ".join(new_words[j1:j2]))
            elif tag == 'replace':
                highlighted_old.append(f"~~{' '.join(old_words[i1:i2])}~~")
                highlighted_new.append(f"**{' '.join(new_words[j1:j2])}**")
            elif tag == 'delete':
                highlighted_old.append(f"~~{' '.join(old_words[i1:i2])}~~")
            elif tag == 'insert':
                highlighted_new.append(f"**{' '.join(new_words[j1:j2])}**")
                
        # Исправляем пробелы перед знаками препинания (упрощенно)
        def cleanup(text_list):
            res = " ".join(text_list)
            res = re.sub(r'\s+([.,!?:;])', r'\1', res)
            return res

        return (cleanup(highlighted_old), cleanup(highlighted_new))

preprocessor = TextPreprocessor()
