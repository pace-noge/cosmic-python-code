from datetime import datetime

from flask import Flask, request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from allocation import config
from allocation.domain import model
from allocation.adapters import repository, orm, email
from allocation.service_layer import services, unit_of_work

orm.start_mappers()
get_session = sessionmaker(bind=create_engine(config.get_postgres_uri()))
app = Flask(__name__)


def is_valid_sku(sku, batches):
    return sku in {b.sku for b in batches}


@app.route("/allocate", methods=["POST"])
def allocate_endpoint():
    line = model.OrderLine(
        request.json["order_id"],
        request.json["sku"],
        request.json["qty"],
    )
    try:
        uow = unit_of_work.SqlAlchemyUnitOfWork()
        batch_ref = services.allocate(line, uow)
    except (model.OutOfStock, services.InvalidSku) as e:
        email.send_mail(
            "out of stock",
            "stock_admin@made.com",
            f"{line.order_id} - {line.sku}"
        )
        return {"message": str(e)}, 400
    return {"batch_ref": batch_ref}, 201


@app.route("/add_batch", methods=["POST"])
def add_batch():
    session = get_session()
    repo = repository.SqlAlchemyRepository(session)
    eta = request.json["eta"]
    if eta is not None:
        eta = datetime.fromisoformat(eta).date()
    services.add_batch(
        request.json["ref"],
        request.json["sku"],
        request.json["qty"],
        eta,
        unit_of_work.SqlAlchemyUnitOfWork()
    )
    return "OK", 201


if __name__ == "__main__":
    app.run(host="0.0.0.0.0", port=8005, debug=True)