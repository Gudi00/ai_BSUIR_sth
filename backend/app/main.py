from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import shutil
import os
import uuid
from typing import List

from .services.parsers import get_parser
from .services.preprocess import preprocessor
from .services.alignment import aligner
from .services.risk import risk_engine
from .services.reports import generate_docx_report, generate_pdf_report
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
REPORTS_DIR = "data/reports"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/compare", response_model=List[ComparisonResult])
async def compare_documents(
    old_file: UploadFile = File(...),
    new_file: UploadFile = File(...)
):
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
            b.lemma_text = preprocessor.lemmatize(b.clean_text)
        for b in new_blocks:
            b.lemma_text = preprocessor.lemmatize(b.clean_text)
            
        alignment_results = aligner.align(old_blocks, new_blocks)
        
        final_results = []
        for res in alignment_results:
            # СТРОГАЯ ПРОВЕРКА: Если оба блока существуют и тексты идентичны (после очистки) - ИГНОРИРУЕМ
            if res.old_block and res.new_block:
                t1 = res.old_block.clean_text.strip()
                t2 = res.new_block.clean_text.strip()
                if t1 == t2:
                    continue
            
            # Дополнительная проверка на высокий скор (почти идентичны)
            if res.diff_type == "equal" or res.score > 99.8:
                continue
                
            analyzed = risk_engine.analyze(res)
            final_results.append(analyzed)
            
        return final_results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/export/docx")
async def export_docx(results: List[ComparisonResult]):
    try:
        file_id = str(uuid.uuid4())
        report_path = os.path.join(REPORTS_DIR, f"report_{file_id}.docx")
        generate_docx_report(results, report_path)
        return FileResponse(report_path, filename="Comparison_Report.docx")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/export/pdf")
async def export_pdf(results: List[ComparisonResult]):
    try:
        file_id = str(uuid.uuid4())
        report_path = os.path.join(REPORTS_DIR, f"report_{file_id}.pdf")
        generate_pdf_report(results, report_path)
        return FileResponse(report_path, filename="Comparison_Report.pdf")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
