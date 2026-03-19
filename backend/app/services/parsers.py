import uuid
import re
import docx
import pdfplumber
from typing import List, Optional
from ..models.block import DocumentBlock

class BaseParser:
    def parse(self, file_path: str) -> List[DocumentBlock]:
        raise NotImplementedError

class WordParser(BaseParser):
    def parse(self, file_path: str) -> List[DocumentBlock]:
        doc = docx.Document(file_path)
        blocks = []
        position = 0
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
                
            # Простая логика извлечения номера (напр. "1.1.", "Статья 5")
            number_match = re.match(r'^([\d\.]+|Статья\s+\d+|Пункт\s+[\d\.]+)', text)
            number = number_match.group(1) if number_match else None
            
            # Если параграф целиком состоит из номера, возможно это заголовок
            clean_text = text
            if number:
                clean_text = text[len(number):].strip()
            
            blocks.append(DocumentBlock(
                id=str(uuid.uuid4()),
                number=number,
                heading=None, # Пока не разделяем заголовки и текст
                raw_text=text,
                clean_text=clean_text if clean_text else text,
                position=position
            ))
            position += 1
            
        return blocks

class PDFParser(BaseParser):
    def parse(self, file_path: str) -> List[DocumentBlock]:
        blocks = []
        position = 0
        
        with pdfplumber.open(file_path) as pdf:
            full_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
            
            # Разделяем на блоки по двойному переносу строки или паттернам пунктов
            # Для MVP делим по строкам, начинающимся с цифр или спец. слов
            lines = full_text.split('\n')
            current_block_text = ""
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Если строка похожа на начало нового пункта
                if re.match(r'^([\d\.]+|Статья\s+\d+|Пункт\s+[\d\.]+)', line) and current_block_text:
                    # Сохраняем предыдущий блок
                    blocks.append(self._create_block(current_block_text, position))
                    position += 1
                    current_block_text = line
                else:
                    current_block_text += " " + line if current_block_text else line
            
            if current_block_text:
                blocks.append(self._create_block(current_block_text, position))
                
        return blocks

    def _create_block(self, text: str, position: int) -> DocumentBlock:
        number_match = re.match(r'^([\d\.]+|Статья\s+\d+|Пункт\s+[\d\.]+)', text)
        number = number_match.group(1) if number_match else None
        clean_text = text[len(number):].strip() if number else text
        
        return DocumentBlock(
            id=str(uuid.uuid4()),
            number=number,
            raw_text=text,
            clean_text=clean_text if clean_text else text,
            position=position
        )

def get_parser(filename: str) -> Optional[BaseParser]:
    if filename.endswith('.docx'):
        return WordParser()
    elif filename.endswith('.pdf'):
        return PDFParser()
    return None
