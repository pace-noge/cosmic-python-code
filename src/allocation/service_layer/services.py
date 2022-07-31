from datetime import date
from typing import Optional

from allocation.service_layer import unit_of_work
from allocation.domain import model
from allocation.adapters.repository import AbstractRepository
from allocation.adapters import email
from allocation.domain.model import OrderLine
from . import message_bus


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
        product = uow.products.get(sku=line.sku)
        if product is None:
            raise InvalidSku(f"Invalid sku {line.sku}")
        batch_ref = product.allocate(line)
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


def add_batch(
        ref: str, sku: str, qty: int, eta: Optional[date],
        uow: unit_of_work.AbstractUnitOfWork,
) -> None:
    with uow:
        product = uow.products.get(sku=sku)
        if product is None:
            product = model.Product(sku, batches=[])
            uow.products.add(product)
        product.batches.append(model.Batch(ref, sku, qty, eta))
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
