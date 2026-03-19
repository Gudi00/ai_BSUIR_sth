from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import uuid
from typing import List

from .services.parsers import get_parser
from .services.preprocess import preprocessor
from .services.alignment import aligner
from .services.risk import risk_engine
from .models.block import ComparisonResult

app = FastAPI(title="LegalDocComparer API")

# Настройка CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # В продакшене ограничить
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/compare", response_model=List[ComparisonResult])
async def compare_documents(
    old_file: UploadFile = File(...),
    new_file: UploadFile = File(...)
):
    # 1. Сохраняем временные файлы
    old_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{old_file.filename}")
    new_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{new_file.filename}")
    
    with open(old_path, "wb") as buffer:
        shutil.copyfileobj(old_file.file, buffer)
    with open(new_path, "wb") as buffer:
        shutil.copyfileobj(new_file.file, buffer)

    try:
        # 2. Парсинг
        old_parser = get_parser(old_file.filename)
        new_parser = get_parser(new_file.filename)
        
        if not old_parser or not new_parser:
            raise HTTPException(status_code=400, detail="Unsupported file format")
            
        old_blocks = old_parser.parse(old_path)
        new_blocks = new_parser.parse(new_path)
        
        # 3. Предобработка (лемматизация)
        for b in old_blocks:
            b.lemma_text = preprocessor.lemmatize(b.clean_text)
        for b in new_blocks:
            b.lemma_text = preprocessor.lemmatize(b.clean_text)
            
        # 4. Сопоставление (Alignment)
        alignment_results = aligner.align(old_blocks, new_blocks)
        
        # 5. Анализ рисков
        final_results = []
        for res in alignment_results:
            analyzed = risk_engine.analyze(res)
            final_results.append(analyzed)
            
        return final_results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Удаляем временные файлы (можно добавить очистку по расписанию)
        # if os.path.exists(old_path): os.remove(old_path)
        # if os.path.exists(new_path): os.remove(new_path)
        pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
