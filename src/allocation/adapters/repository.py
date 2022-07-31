from typing import Set, Protocol
from allocation.domain import model


class AbstractRepository(Protocol):
    def add(self, product: model.Product):
        ...

    def get(self, sku) -> model.Product:
        ...


class TrackingRepository:
    seen: set[model.Product]

    def __init__(self, repo: AbstractRepository):
        self._repo = repo

    def add(self, product: model.Product):
        self._repo.add(product)
        self.seen.add(product)

    def get(self, sku) -> model.Product:
        product = self._repo.get(sku)
        if product:
            self.seen.add(product)
        return product


class SqlAlchemyRepository:
    def __init__(self, session):
        super().__init__()
        self.session = session

    def add(self, product):
        self.session.add(product)

    def get(self, sku):
        return self.session.query(model.Product).filter_by(sku=sku).first()

    def list(self):
        return self.session.query(model.Product).all()

