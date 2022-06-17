from datetime import date, timedelta

import pytest

from model import Batch, OrderLine


def make_batch_and_line(sku, batch_qty, line_qty):
    return (
        Batch("batch-001", sku, batch_qty, eta=date.today()),
        OrderLine("order-123", sku, line_qty)
    )


def test_allocating_to_a_batch_reduces_the_available_quantity():
    batch, line = make_batch_and_line("SMALL-TABLE", 20, 2)
    assert batch.can_allocate(line)
    batch.allocate(line)
    assert batch.available_quantity == 18


def test_can_allocate_if_available_greater_than_required():
    batch, line = make_batch_and_line("SMALL-TABLE", 20, 2)
    batch.allocate(line)
    assert batch.allocated_quantity == 2


def test_cannot_allocate_if_available_smaller_than_required():
    batch, line = make_batch_and_line("SMALL-TABLE", 5, 6)
    assert batch.can_allocate(line) is False
    batch.allocate(line)
    assert batch.allocated_quantity == 0


def test_can_allocate_if_available_equal_to_required():
    batch, line = make_batch_and_line("SMALL-TABLE", 5, 5)
    assert batch.can_allocate(line)
    batch.allocate(line)
    assert batch.allocated_quantity == 5


def test_cannot_allocate_if_skus_do_not_match():
    batch = Batch("batch-002", "COMFORT-CHAIR", qty=100, eta=None)
    line = OrderLine("order-oo2", "UNCOMFORTABLE-CHAIR", 10)
    assert batch.can_allocate(line) is False


def test_can_deallocate_allocated_lines():
    batch, unalllocated_line = make_batch_and_line("DECORATIVE-TRINKET", 20, 2)
    batch.allocate(unalllocated_line)
    assert batch.available_quantity == 18

    invalid_line = OrderLine("order-003", "INVALID-SKU", 2)
    assert batch.can_allocate(invalid_line) is False
    batch.deallocate(invalid_line)
    assert  batch.available_quantity == 18

    batch.deallocate(unalllocated_line)
    assert batch.available_quantity == 20
