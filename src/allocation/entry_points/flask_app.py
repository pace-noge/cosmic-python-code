from datetime import datetime

from flask import Flask, request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from allocation import config
from allocation.domain import model, events
from allocation.adapters import repository, orm, email
from allocation.service_layer import handlers, unit_of_work, message_bus
from allocation.service_layer.handlers import InvalidSku

orm.start_mappers()
get_session = sessionmaker(bind=create_engine(config.get_postgres_uri()))
app = Flask(__name__)


def is_valid_sku(sku, batches):
    return sku in {b.sku for b in batches}


@app.route("/add-batch", methods=["POST"])
def add_batch():
    eta = request.json["eta"]
    if eta is not None:
        eta = datetime.fromisoformat(eta).date()
    event = events.BatchCreated(
        request.json["ref"], request.json["sku"], request.json["qty"], eta
    )
    message_bus.handle(event, unit_of_work.SqlAlchemyUnitOfWork())
    return "OK", 201


@app.route("/allocate", methods=["POST"])
def allocate_endpoint():
    try:
        event = events.AllocationRequired(
            request.json["order_id"],
            request.json["sku"],
            request.json["qty"]
        )
        results = message_bus.handle(event, unit_of_work.SqlAlchemyUnitOfWork())
        batch_ref = results.pop(0)
    except InvalidSku as e:
        return {"message": str(e)}, 400
    return {"batch_ref": batch_ref}, 201


if __name__ == "__main__":
    app.run(host="0.0.0.0.0", port=8005, debug=True)