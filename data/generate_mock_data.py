from docx import Document
import os

def create_mock_docs():
    os.makedirs('data/samples', exist_ok=True)
    
    # 1. СТАРАЯ РЕДАКЦИЯ
    doc_old = Document()
    doc_old.add_heading('Приказ о порядке выплат (Старая редакция)', 0)
    doc_old.add_paragraph('1.1. Выплата заработной платы производится один раз в месяц.')
    doc_old.save('data/samples/old_doc_rag.docx')
    
    # 2. НОВАЯ РЕДАКЦИЯ
    doc_new = Document()
    doc_new.add_heading('Приказ о порядке выплат (Новая редакция)', 0)
    # Этот пункт будет семантически близок к ТК Ст. 73, но противоречить ему
    doc_new.add_paragraph('1.1. Выплата заработной платы производится только один раз в месяц (30 числа).')
    doc_new.save('data/samples/new_doc_rag.docx')
    
    print("Примеры для RAG-теста созданы в data/samples/old_doc_rag.docx и new_doc_rag.docx")

if __name__ == "__main__":
    create_mock_docs()
