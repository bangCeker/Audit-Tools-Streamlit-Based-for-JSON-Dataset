# data/repo_db.py
from typing import Dict, Any, List, Optional


class DBRepo:
    def __init__(self, db_helper_module):
        # FIX typo: db_helper_modul -> db_helper_module
        self.db = db_helper_module

    def count(self, table: str, **filters) -> int:
        return int(self.db.count_dataset(table, **filters))

    def query(self, table: str, limit: int, offset: int, **filters) -> List[Dict[str, Any]]:
        return self.db.query_dataset(table, limit=limit, offset=offset, **filters)

    def get_by_id(self, table: str, rid: int) -> Optional[Dict[str, Any]]:
        return self.db.get_row_by_id(table, rid)

    def update(self, table: str, rid: int, **payload) -> None:
        self.db.update_dataset_row(table, rid, **payload)

    # alias biar code lama yang manggil update_row nggak error
    def update_row(self, table: str, rid: int, **payload) -> None:
        self.update(table, rid, **payload)

    def adjacent_id(self, table: str, rid: int, direction: str, **filters) -> Optional[int]:
        return self.db.get_adjacent_id(table, rid, direction, **filters)
