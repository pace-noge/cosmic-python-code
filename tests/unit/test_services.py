from datetime import date, timedelta

import pytest

from allocation.service_layer import unit_of_work
from src.allocation.domain import model
from src.allocation.adapters import repository
from src.allocation.service_layer import services

today = date.today()
tomorrow = today + timedelta(days=1)
later = tomorrow + timedelta(days=1)


class FakeRepository(repository.AbstractRepository):
    def __init__(self, batches):
        self._batches = batches

    def add(self, batch):
        if isinstance(self._batches, list):
            self._batches.append(batch)
        elif isinstance(self._batches, set):
            self._batches.add(batch)

    def get(self, reference):
        return next(b for b in self._batches if b.reference == reference)

    def list(self):
        return list(self._batches)

    @staticmethod
    def for_batch(ref, sku, qty, eta=None):
        return FakeRepository([
            model.Batch(ref, sku, qty, eta),
        ])


class FakeSession:
    committed = False

    def commit(self):
        self.committed = True


class FakeUnitOfWork(unit_of_work.AbstractUnitOfWork):
    def __init__(self):
        self.batches = FakeRepository([])
        self.committed = False

    def commit(self):
        self.committed = True

    def rollback(self):
        pass


def test_add_batch():
    uow = FakeUnitOfWork()
    services.add_batch("b1", "CRUNCHY-ARMCHAIR", 100, None, uow)
    assert uow.batches.get("b1") is not None
    assert uow.committed


def test_allocate_returns_allocation():
    uow = FakeUnitOfWork()
    services.add_batch("batch1", "COMPLICATED-LAMP", 100, None, uow)
    result = services.allocate("o1", "COMPLICATED-LAMP", 10, uow)
    assert result == "batch1"


def test_allocate_errors_for_invalid_sku():
    uow = FakeUnitOfWork()
    services.add_batch("batch1", "AREAL-SKU", 100, None, uow)
    with pytest.raises(services.InvalidSku, match="Invalid sku NOT-EXISTS"):
        services.allocate("o1", "NOT-EXISTS", 10, uow)
