from datetime import date
from typing import Optional

from allocation.service_layer import unit_of_work
from src.allocation.domain import model
from src.allocation.adapters.repository import AbstractRepository
from src.allocation.domain.model import OrderLine


class InvalidSku(Exception):
    pass


def is_valid_sku(sku, batches):
    return sku in {b.sku for b in batches}


def allocate(
        order_id: str, sku: str, qty: int,
        uow: unit_of_work.AbstractUnitOfWork,
) -> str:
    line = OrderLine(order_id, sku, qty)
    with uow:
        batches = uow.batches.list()
        if not is_valid_sku(line.sku, batches):
            raise InvalidSku(f"Invalid sku {line.sku}")
        batch_ref = model.allocate(line, batches)
        uow.commit()
    return batch_ref


def reallocate(
        line: OrderLine,
        uow: unit_of_work.AbstractUnitOfWork
) -> str:
    with uow:
        batch = uow.batches.get(sku=line.sku)
        if batch is None:
            raise InvalidSku(f"Invalid sku {line.sku}")
        batch.deallocate(line)
        allocate(line)
        uow.commit()


def add_batch(
        ref: str, sku: str, qty: int, eta: Optional[date],
        uow: unit_of_work.AbstractUnitOfWork,
) -> None:
    with uow:
        uow.batches.add(model.Batch(ref, sku, qty, eta))
        uow.commit()


def deallocate(line: model.OrderLine, repo: AbstractRepository, batch_ref: str, session) -> str:
    batch = repo.get(batch_ref)
    if not is_valid_sku(line.sku, [batch]):
        raise InvalidSku(f"Invalid slu {line.sku}")
    try:
        model.deallocate(line, batch)
        return True
    except Exception as e:
        return False

