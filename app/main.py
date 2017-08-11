import json

from flask import Flask, request, jsonify

from models import db, Coupon
from error import Error

with open('produce-permission.json', 'r') as produce_permission_json:
    produce_permission = json.load(produce_permission_json)
app = Flask(__name__)
app.config.from_pyfile('config.py')
db.init_app(app)


@app.route('/generate', methods=['POST'])
def generate():
    token = request.form.get('token')
    coin = request.form.get('coin')
    description = request.form.get('description')

    if token not in produce_permission.keys():
        raise Error("invalid token")

    if coin is None or description is None:
        raise Error("coin and description required")

    coupon = Coupon(coin=coin, description=description, producer=produce_permission[token])

    try:
        coupon.save()
    except:
        raise Error("invalid value")

    return jsonify({'status': 'OK', 'coupon': str(coupon.id)})


@app.errorhandler(Error)
def handle_error(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response
