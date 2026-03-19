from natasha import (
    Segmenter, MorphVocab, NewsEmbedding, 
    NewsMorphTagger, Doc
)
from typing import List
import re

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

preprocessor = TextPreprocessor()
