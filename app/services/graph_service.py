from adapters.persistence.kuzu.adapter import KuzuAdapter

class GraphService:
    def __init__(self):
        # Lazy initialization to prevent lock issues on import
        self._adapter = None

    @property
    def adapter(self):
        if self._adapter is None:
            self._adapter = KuzuAdapter()
        return self._adapter

    def query(self, cypher: str):
        # Adapter returns List[List[Any]] (rows of values)
        # Nerves logic expects an object with .has_next() and .get_next()
        # This breaks compatibility if we return list directly.
        # We should update Nerves OR return a compatibility wrapper.
        # Clean Architecture says Nerves should depend on Port, which returns List[Dict] or List[List].
        # Nerves currently does: result.has_next(), result.get_next()
        
        # Let's return a simple iterator wrapper to maintain compatibility for now,
        # OR update nerves.py (better).
        # Let's update nerves.py in next step.
        # For now, return the list, acting as iterator? 
        # No, list has no has_next().
        
        # Let's return a CursorMock
        return KuzuCursorWrapper(self.adapter.query(cypher))

class KuzuCursorWrapper:
    def __init__(self, data):
        self.data = data
        self.index = 0
        
    def has_next(self):
        return self.index < len(self.data)
        
    def get_next(self):
        if self.has_next():
            val = self.data[self.index]
            self.index += 1
            return val
        return None

graph_service = GraphService()
