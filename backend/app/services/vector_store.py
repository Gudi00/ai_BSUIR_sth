from sentence_transformers import SentenceTransformer, util
import torch
import os
import glob
import json
import pickle
import hashlib
from typing import List, Dict, Any, Optional
from .parsers import get_parser
import logging

logger = logging.getLogger("uvicorn.error")

class VectorSearchService:
    def __init__(self, base_dir: str = "data/NTPA"):
        # Мы не загружаем модель и не индексируем файлы сразу в __init__, 
        # чтобы не блокировать запуск основного API сервера.
        self.base_dir = base_dir
        self.cache_dir = os.path.join(self.base_dir, ".cache")
        self.metadata_path = os.path.join(self.base_dir, "metadata.json")
        self.model = None # Загрузим позже при необходимости
        
        os.makedirs(self.cache_dir, exist_ok=True)
        self.disabled_files = self._load_metadata()
        
        self.kb_vectors = []
        self.kb_metadata = []
        
        for i in range(1, 11):
            os.makedirs(os.path.join(self.base_dir, str(i)), exist_ok=True)

    def _get_model(self):
        if self.model is None:
            logger.info("Loading NLP model (rubert-tiny2)...")
            self.model = SentenceTransformer('cointegrated/rubert-tiny2')
        return self.model

    def _load_metadata(self) -> List[str]:
        if os.path.exists(self.metadata_path):
            try:
                with open(self.metadata_path, 'r', encoding='utf-8') as f:
                    return json.load(f).get("disabled", [])
            except:
                return []
        return []

    def _save_metadata(self):
        with open(self.metadata_path, 'w', encoding='utf-8') as f:
            json.dump({"disabled": self.disabled_files}, f, ensure_ascii=False)

    def _get_file_hash(self, file_path: str) -> str:
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            hasher.update(f.read())
        return hasher.hexdigest()

    def toggle_file(self, filename: str):
        if filename in self.disabled_files:
            self.disabled_files.remove(filename)
        else:
            self.disabled_files.append(filename)
        self._save_metadata()

    def reindex_all(self):
        """Полная переиндексация базы знаний."""
        model = self._get_model()
        all_vectors = []
        all_metadata = []
        
        logger.info("Reindexing NTPA hierarchy...")
        
        for level in range(1, 11):
            level_path = os.path.join(self.base_dir, str(level))
            files = glob.glob(os.path.join(level_path, "*.docx")) + glob.glob(os.path.join(level_path, "*.pdf"))
            
            for file_path in files:
                filename = os.path.basename(file_path)
                if filename in self.disabled_files: continue
                
                # Генерируем уникальный короткий ID для кэша на основе имени и контента
                file_hash = self._get_file_hash(file_path)
                name_hash = hashlib.md5(filename.encode()).hexdigest()
                cache_path = os.path.join(self.cache_dir, f"{name_hash}_{file_hash}.pkl")
                
                if os.path.exists(cache_path):
                    try:
                        with open(cache_path, 'rb') as f:
                            cached = pickle.load(f)
                            all_vectors.extend(cached['vectors'])
                            all_metadata.extend(cached['metadata'])
                        continue
                    except:
                        pass # Если кэш битый, переиндексируем

                try:
                    parser = get_parser(filename)
                    if not parser: continue
                    blocks = parser.parse(file_path)
                    
                    file_vectors = []
                    file_metadata = []
                    for block in blocks:
                        text = f"{block.number + ' ' if block.number else ''}{block.clean_text}"
                        vector = model.encode(text, convert_to_tensor=True)
                        file_vectors.append(vector)
                        file_metadata.append({
                            "level": level, "doc": filename, "art": block.number or "Пункт", "text": block.clean_text
                        })
                    
                    with open(cache_path, 'wb') as f:
                        pickle.dump({'vectors': file_vectors, 'metadata': file_metadata}, f)
                        
                    all_vectors.extend(file_vectors)
                    all_metadata.extend(file_metadata)
                except Exception as e:
                    logger.error(f"Error indexing {filename}: {e}")

        self.kb_metadata = all_metadata
        self.kb_vectors = torch.stack(all_vectors) if all_vectors else []
        logger.info("Indexing complete.")

    def get_best_matches_per_level(self, text: str, current_level: int, threshold: float = 0.5) -> Dict[int, Dict[str, Any]]:
        # Если база еще не загружена в память - индексируем (ленивая загрузка)
        if not self.kb_metadata and not self.kb_vectors:
            self.reindex_all()
            
        if not isinstance(self.kb_vectors, torch.Tensor): return {}
        
        model = self._get_model()
        query_vector = model.encode(text, convert_to_tensor=True)
        cos_scores = util.cos_sim(query_vector, self.kb_vectors)[0]
        
        best_per_level = {}
        for i, score in enumerate(cos_scores):
            score_val = float(score)
            meta = self.kb_metadata[i]
            level = meta["level"]
            if level < current_level and score_val > threshold:
                if level not in best_per_level or score_val > best_per_level[level]["similarity"]:
                    best_per_level[level] = {
                        "law": meta["doc"], "article": meta["art"], "text": meta["text"], "similarity": score_val
                    }
        return best_per_level

vector_service = VectorSearchService()
