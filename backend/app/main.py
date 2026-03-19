from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import shutil
import os
import uuid
import glob
from typing import List, Dict, Any

from .services.parsers import get_parser
from .services.preprocess import preprocessor
from .services.alignment import aligner
from .services.risk import risk_engine
from .services.reports import generate_docx_report, generate_pdf_report
from .services.vector_store import vector_service
from .models.block import ComparisonResult

app = FastAPI(title="LegalDocComparer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "data/uploads"
NTPA_DIR = "data/NTPA"
os.makedirs(UPLOAD_DIR, exist_ok=True)
for i in range(1, 11):
    os.makedirs(os.path.join(NTPA_DIR, str(i)), exist_ok=True)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

# --- Управление Иерархией (NTPA) ---

@app.get("/hierarchy")
async def get_hierarchy():
    """Список всех файлов по уровням из папок в реальном времени."""
    structure = {}
    disabled = vector_service.disabled_files
    for level in range(1, 11):
        level_path = os.path.join(NTPA_DIR, str(level))
        os.makedirs(level_path, exist_ok=True)
        files = []
        # Прямое сканирование директории
        for fname in os.listdir(level_path):
            f_path = os.path.join(level_path, fname)
            if fname.startswith(".") or os.path.isdir(f_path):
                continue
            files.append({
                "name": fname,
                "enabled": fname not in disabled
            })
        structure[level] = files
    return structure

@app.post("/hierarchy/toggle")
async def toggle_hierarchy_file(filename: str = Body(..., embed=True)):
    vector_service.toggle_file(filename)
    return {"status": "success", "disabled_list": vector_service.disabled_files}

@app.post("/hierarchy/{level}/upload")
async def upload_to_hierarchy(level: int, file: UploadFile = File(...)):
    if not (1 <= level <= 10):
        raise HTTPException(status_code=400, detail="Level must be between 1 and 10")
    
    file_path = os.path.join(NTPA_DIR, str(level), file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"status": "success", "filename": file.filename}

@app.delete("/hierarchy/{level}/{filename}")
async def delete_from_hierarchy(level: int, filename: str):
    file_path = os.path.join(NTPA_DIR, str(level), filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="File not found")

@app.post("/hierarchy/reindex")
async def reindex_hierarchy():
    """Запуск переиндексации векторной базы."""
    try:
        vector_service.reindex_all()
        return {"status": "success", "indexed_blocks": len(vector_service.kb_metadata)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Сравнение документов ---

from .services.ui_logic import ui_service
from .models.block import ComparisonResult, ComparisonResponse, RiskLevel

# ... (Existing imports ...)

@app.post("/compare", response_model=ComparisonResponse)
async def compare_documents(
    old_file: UploadFile = File(...),
    new_file: UploadFile = File(...)
):
    # ... (Keep parsing and alignment logic unchanged ...)
    old_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{old_file.filename}")
    new_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{new_file.filename}")
    
    with open(old_path, "wb") as buffer:
        shutil.copyfileobj(old_file.file, buffer)
    with open(new_path, "wb") as buffer:
        shutil.copyfileobj(new_file.file, buffer)

    try:
        old_parser = get_parser(old_file.filename)
        new_parser = get_parser(new_file.filename)
        
        if not old_parser or not new_parser:
            raise HTTPException(status_code=400, detail="Unsupported file format")
            
        old_blocks = old_parser.parse(old_path)
        new_blocks = new_parser.parse(new_path)
        
        for b in old_blocks:
            b.lemma_text = preprocessor.lemmatize(b.clean_text) if b.clean_text else ""
            b.hierarchy_level = 10
            
        for b in new_blocks:
            b.lemma_text = preprocessor.lemmatize(b.clean_text) if b.clean_text else ""
            b.hierarchy_level = 10
            
        alignment_results = aligner.align(old_blocks, new_blocks)
        
        raw_final_results = []
        for res in alignment_results:
            if res.diff_type in ["added", "deleted"]:
                raw_final_results.append(risk_engine.analyze(res))
                continue
                
            if res.old_block and res.new_block:
                if res.old_block.clean_text.strip() == res.new_block.clean_text.strip():
                    continue
            
            raw_final_results.append(risk_engine.analyze(res))
            
        # 1. Считаем статистику по "сырым" результатам
        summary = {
            "total_blocks": len(new_blocks),
            "matched": sum(1 for r in raw_final_results if r.old_block and r.new_block),
            "changed": sum(1 for r in raw_final_results if r.diff_type == "changed"),
            "added": sum(1 for r in raw_final_results if r.diff_type == "added"),
            "deleted": sum(1 for r in raw_final_results if r.diff_type == "deleted"),
            "risk_distribution": {
                "red": sum(1 for r in raw_final_results if r.risk_level == RiskLevel.RED),
                "yellow": sum(1 for r in raw_final_results if r.risk_level == RiskLevel.YELLOW),
                "green": sum(1 for r in raw_final_results if r.risk_level == RiskLevel.GREEN),
            }
        }
        
        # 2. Применяем Smart Collapse (только для UI)
        collapsed_results = ui_service.collapse_long_added_tails(raw_final_results, min_blocks=3)
        
        return {
            "summary": summary,
            "results": collapsed_results
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# (Эндпоинты DOCX/PDF как раньше...)
@app.post("/export/docx")
async def export_docx(results: List[ComparisonResult]):
    file_id = str(uuid.uuid4()); path = os.path.join("data/reports", f"report_{file_id}.docx")
    generate_docx_report(results, path); return FileResponse(path, filename="Report.docx")

@app.post("/export/pdf")
async def export_pdf(results: List[ComparisonResult]):
    file_id = str(uuid.uuid4()); path = os.path.join("data/reports", f"report_{file_id}.pdf")
    generate_pdf_report(results, path); return FileResponse(path, filename="Report.pdf")
