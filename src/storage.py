import pickle
import os
from pathlib import Path
from typing import List, Optional
from src.models import ExamRecord

DATA_DIR = Path("data")


def save_exam(record: ExamRecord) -> None:
    """儲存考試記錄到 data/{exam_id}.pkl"""
    DATA_DIR.mkdir(exist_ok=True)
    path = DATA_DIR / f"{record.exam_id}.pkl"
    with open(path, "wb") as f:
        pickle.dump(record, f)


def load_exam(exam_id: str) -> Optional[ExamRecord]:
    """載入指定考試記錄，不存在回傳 None"""
    path = DATA_DIR / f"{exam_id}.pkl"
    if not path.exists():
        return None
    with open(path, "rb") as f:
        return pickle.load(f)


def list_exams() -> List[str]:
    """回傳所有已儲存的考試 ID 列表（依名稱排序）"""
    if not DATA_DIR.exists():
        return []
    return sorted([p.stem for p in DATA_DIR.glob("*.pkl")])


def delete_exam(exam_id: str) -> bool:
    """刪除指定考試記錄，成功回傳 True"""
    path = DATA_DIR / f"{exam_id}.pkl"
    if path.exists():
        path.unlink()
        return True
    return False
