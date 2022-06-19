from domain import model
from adapters.repository import AbstractRepository


class InvalidSku(Exception):
    pass


def is_valid_sku(sku, batches):
    return sku in {b.sku for b in batches}


def allocate(line: model.OrderLine, repo: AbstractRepository, session) -> str:
    batches = repo.list()
    if not is_valid_sku(line.sku, batches):
        raise InvalidSku(f"Invalid sku {line.sku}")
    batch_ref = model.allocate(line, batches)
    session.commit()
    return batch_ref


def deallocate(line: model.OrderLine, repo: AbstractRepository, batch_ref: str, session) -> str:
    batch = repo.get(batch_ref)
    if not is_valid_sku(line.sku, [batch]):
        raise InvalidSku(f"Invalid slu {line.sku}")
    try:
        model.deallocate(line, batch)
        return True
    except Exception as e:
        return False
