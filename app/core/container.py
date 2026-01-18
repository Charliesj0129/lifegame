from application.services.user_service import UserService
from application.services.brain_service import BrainService
from application.services.graph_service import GraphService
from adapters.persistence.kuzu.adapter import get_kuzu_adapter


class Container:
    def __init__(self):
        # Lazy Singletons
        self._user_service = None
        self._user_service = None
        self._brain_service = None
        self._graph_service = None

    @property
    def user_service(self) -> UserService:
        if not self._user_service:
            self._user_service = UserService()
        return self._user_service

    @property
    def brain_service(self) -> BrainService:
        if not self._brain_service:
            self._brain_service = BrainService()
        return self._brain_service

    @property
    def graph_service(self) -> GraphService:
        if not self._graph_service:
            # Inject KuzuAdapter (Infrastructure) into GraphService (Application)
            self._graph_service = GraphService(self.kuzu_adapter)
        return self._graph_service

    @property
    def kuzu_adapter(self):
        return get_kuzu_adapter()


# Global Container Instance
container = Container()
