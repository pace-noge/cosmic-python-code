import pytest
from allocation.domain import model
from allocation.service_layer import unit_of_work, services
from tests.unit.test_services import FakeRepository


def insert_batch(session, ref, sku, qty, eta):
    session.execute(
        "INSERT INTO batches (reference, sku, _purchased_quantity, eta)"
        " VALUES (:ref, :sku, :qty, :eta)",
        dict(ref=ref, sku=sku, qty=qty, eta=eta)
    )


def get_allocated_batch_ref(session, order_id, sku):
    [[orderline_id]] = session.execute(
        "SELECT id FROM order_lines WHERE order_id=:order_id AND sku=:sku",
        dict(order_id=order_id, sku=sku),
    )
    [[batch_ref]] = session.execute(
        "SELECT b.reference FROM allocations JOIN batches AS b on batch_id = b.id"
        " WHERE orderline_id=:orderline_id",
        dict(orderline_id=orderline_id)
    )
    return batch_ref


def test_uow_can_retrieve_a_batch_and_allocate_to_it(session_factory):
    session = session_factory()
    insert_batch(session, "batch1", "HIPSTER-WORKBENCH", 100, None)
    session.commit()

    uow = unit_of_work.SqlAlchemyUnitOfWork(session_factory)
    with uow:
        batch = uow.batches.get(reference="batch1")
        line = model.OrderLine("o1", "HIPSTER-WORKBENCH", 10)
        batch.allocate(line)
        uow.commit()

    batch_ref = get_allocated_batch_ref(session, "o1", "HIPSTER-WORKBENCH")
    assert batch_ref == "batch1"


def test_rolls_back_uncommitted_work_by_default(session_factory):
    uow = unit_of_work.SqlAlchemyUnitOfWork(session_factory)
    with uow:
        insert_batch(uow.session, "batch1", "MEDIUM-PLINTH", 100, None)

    new_session = session_factory()
    rows = list(new_session.execute('SELECT * FROM "batches"'))
    assert rows == []


def test_roll_back_on_error(sesion_factory):
    class MyException(Exception):
        pass

    uow = unit_of_work.SqlAlchemyUnitOfWork(sesion_factory)
    with pytest.raises(MyException):
        with uow:
            insert_batch(uow.session, "batch1", "LARGE-FORK", 100, None)
            raise MyException()

    new_session = sesion_factory()
    rows = list(new_session.execute('SELECT * FROM "batches"'))
    assert rows == []

