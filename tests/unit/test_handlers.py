from datetime import date
from unittest import mock
import pytest
from allocation.adapters import repository
from allocation.service_layer import handlers, unit_of_work, message_bus
from allocation.domain import events


class FakeRepository(repository.AbstractRepository):
    def __init__(self, products):
        super().__init__()
        self._products = set(products)

    def _add(self, product):
        self._products.add(product)

    def _get(self, sku):
        return next((p for p in self._products if p.sku == sku), None)

    def _get_by_batch_ref(self, batch_ref):
        return next(
            (p for p in self._products for b in p.batches if b.reference == batch_ref),
            None
        )


class FakeUnitOfWork(unit_of_work.AbstractUnitOfWork):
    def __init__(self):
        self.products = FakeRepository([])
        self.committed = False

    def _commit(self):
        self.committed = True

    def rollback(self):
        pass


class TestAddBatch:
    def test_for_new_product(self):
        uow = FakeUnitOfWork()
        message_bus.handle(
            events.BatchCreated("b1", "CRUNCHY-ARMCHAIR", 100, None), uow
        )
        assert uow.products.get("CRUNCHY-ARMCHAIR") is not None
        assert uow.committed

    def test_for_existing_product(self):
        uow = FakeUnitOfWork()
        message_bus.handle(events.BatchCreated("b1", "GARISH-RUG", 100, None), uow)
        message_bus.handle(events.BatchCreated("b2", "GARISH-RUG", 99, None), uow)
        assert "b2" in [b.reference for b in uow.products.get("GARISH-RUG").batches]


class TestAllocate:
    def test_allocate_returns_allocation(self):
        uow = FakeUnitOfWork()
        message_bus.handle(events.BatchCreated("batch1", "COMPLICATED-LAMP", 100, None), uow)
        results = message_bus.handle(events.AllocationRequired("o1", "COMPLICATED-LAMP", 10), uow)
        assert results.pop(0) == "batch1"

    def test_errors_for_invalid_sku(self):
        uow = FakeUnitOfWork()
        message_bus.handle(events.BatchCreated("b1", "AREALSKU", 100, None), uow)
        with pytest.raises(handlers.InvalidSku, match="Invalid sku NONEXISTENTSKU"):
            message_bus.handle(
                events.AllocationRequired("o1", "NONEXISTENTSKU", 10), uow
            )

    def test_commits(self):
        uow = FakeUnitOfWork()
        message_bus.handle(events.BatchCreated("b1", "OMINOUS-MIRROR", 100, None), uow)
        message_bus.handle(events.AllocationRequired("o1", "OMINOUS-MIRROR", 10), uow)
        assert uow.committed

    def test_sends_email_on_out_of_stock_error(self):
        uow = FakeUnitOfWork()
        message_bus.handle(events.BatchCreated("b1", "POPULAR-CURTAINS", 9, None), uow)
        with mock.patch("allocation.adapters.email.send") as mock_send_mail:
            message_bus.handle(
                events.AllocationRequired("o1", "POPULAR-CURTAINS", 10), uow
            )
            assert mock_send_mail.call_args == mock.call(
                "stock@made.com",
                f"Out of stock for POPULAR-CURTAINS",
            )


class TestChangeBatchQuantity:
    def test_change_available_quantity(self):
        uow = FakeUnitOfWork()
        message_bus.handle(
            events.BatchCreated("batch1", "ADORABLE-SETTEE", 100, None), uow
        )
        [batch] = uow.products.get(sku="ADORABLE-SETTEE").batches
        assert batch.available_quantity == 100

        message_bus.handle(events.BatchQuantityChanged("batch1", 50), uow)
        assert batch.available_quantity == 50

    def test_reallocates_if_necessary(self):
        uow = FakeUnitOfWork()
        event_history = [
            events.BatchCreated("batch1", "INDIFFERENT-TABLE", 50, None),
            events.BatchCreated("batch2", "INDIFFERENT-TABLE", 50, date.today()),
            events.AllocationRequired("order1", "INDIFFERENT-TABLE", 20),
            events.AllocationRequired("order2", "INDIFFERENT-TABLE", 20),
        ]
        for e in event_history:
            message_bus.handle(e, uow)
        [batch1, batch2] = uow.products.get(sku="INDIFFERENT-TABLE").batches
        assert batch1.available_quantity == 10
        assert batch2.available_quantity == 50

        message_bus.handle(events.BatchQuantityChanged("batch1", 25), uow)

        # order1 or order2 will be deallocated, so we'll have 25 - 20
        assert batch1.available_quantity == 5
        # and 20 will be reallocated to the next batch
        assert batch2.available_quantity == 30
