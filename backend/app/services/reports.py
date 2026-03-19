from docx import Document
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml
from fpdf import FPDF
import logging
import os
from typing import List
from ..models.block import ComparisonResult

logger = logging.getLogger("uvicorn.error")

def set_cell_background(cell, fill_color: str):
    try:
        shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_color}"/>')
        cell._tc.get_or_add_tcPr().append(shading_elm)
    except Exception as e:
        logger.error(f"DOCX Style Error: {e}")

def generate_docx_report(results: List[ComparisonResult], output_path: str):
    try:
        doc = Document()
        doc.add_heading('Отчет о сравнении документов', 0)
        
        table = doc.add_table(rows=1, cols=2)
        table.style = 'Table Grid'
        
        # Заголовки
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'СТАРАЯ РЕДАКЦИЯ'
        hdr_cells[1].text = 'НОВАЯ РЕДАКЦИЯ / АНАЛИЗ'
        
        COLORS = {"green": "C6EFCE", "yellow": "FFEB9C", "red": "FFC7CE"}

        for res in results:
            row_cells = table.add_row().cells
            
            # Старый текст
            old_val = f"{res.old_block.number + ' ' if res.old_block and res.old_block.number else ''}{res.old_block.clean_text if res.old_block else '(Блок отсутствовал)'}"
            row_cells[0].text = old_val
            
            # Новый текст
            new_val = f"{res.new_block.number + ' ' if res.new_block and res.new_block.number else ''}{res.new_block.clean_text if res.new_block else '(Блок удален)'}"
            if res.risk_explanation:
                new_val += f"\n\n[АНАЛИЗ: {res.risk_explanation}]"
            row_cells[1].text = new_val
            
            if res.risk_level in COLORS:
                set_cell_background(row_cells[1], COLORS[res.risk_level])

        doc.save(output_path)
    except Exception as e:
        logger.error(f"CRITICAL DOCX ERROR: {e}")
        raise e

def generate_pdf_report(results: List[ComparisonResult], output_path: str):
    try:
        pdf = FPDF()
        pdf.add_page()
        
        # Стандартный шрифт для латиницы (fallback)
        pdf.set_font('Helvetica', 'B', 14)
        pdf.cell(0, 10, 'Legal Document Comparison Report', ln=True, align='C')
        pdf.set_font('Helvetica', '', 10)
        
        # Цвета
        COLORS_RGB = {
            "green": (198, 239, 206),
            "yellow": (255, 235, 156),
            "red": (255, 199, 206)
        }

        for res in results:
            old_t = f"{res.old_block.number + ' ' if res.old_block and res.old_block.number else ''}{res.old_block.clean_text if res.old_block else 'None'}"
            new_t = f"{res.new_block.number + ' ' if res.new_block and res.new_block.number else ''}{res.new_block.clean_text if res.new_block else 'None'}"
            
            # Для PDF в MVP используем latin-only (Helvetica) или попробуем latin-1 кодировку
            # Кириллица в PDF сложна без внешних .ttf файлов.
            # Если вам нужна кириллица в PDF, пожалуйста, установите шрифты DejaVuSans в систему!
            
            y_before = pdf.get_y()
            pdf.multi_cell(95, 5, old_t.encode('latin-1', 'replace').decode('latin-1'), border=1)
            y_after_old = pdf.get_y()
            
            pdf.set_xy(105, y_before)
            
            if res.risk_level in COLORS_RGB:
                pdf.set_fill_color(*COLORS_RGB[res.risk_level])
                pdf.multi_cell(95, 5, new_t.encode('latin-1', 'replace').decode('latin-1'), border=1, fill=True)
            else:
                pdf.multi_cell(95, 5, new_t.encode('latin-1', 'replace').decode('latin-1'), border=1)
            
            pdf.set_y(max(y_after_old, pdf.get_y()) + 5)

        pdf.output(output_path)
    except Exception as e:
        logger.error(f"CRITICAL PDF ERROR: {e}")
        raise e
