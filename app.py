import math
from decimal import Decimal
from flask import Flask
from flask_restful import Api, Resource, reqparse, abort, fields, marshal_with
from flask_sqlalchemy import SQLAlchemy
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
api = Api(app)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URI")
db = SQLAlchemy(app)


# All of the table models
class UserModel(db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(80))
    sid = db.Column(db.String(80))
    created_at = db.Column(db.DateTime)
    order_lines = db.relationship("OrderLineModel", backref="user", lazy=True)


class CartModel(db.Model):
    __tablename__ = "cart"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    total = db.Column(db.Numeric, default=Decimal("0.00"))
    created_at = db.Column(db.DateTime)
    purchased_at = db.Column(db.DateTime, nullable=True)
    order_lines = db.relationship("OrderLineModel", backref="cart", lazy=True)


class ActiveCartModel(db.Model):
    __tablename__ = "active_cart"
    cart_id = db.Column(
        db.Integer, db.ForeignKey("cart.id"), primary_key=True, autoincrement=True
    )
    modified_at = db.Column(db.DateTime)
    cart = db.relationship("CartModel", backref="active_cart")


class OrderLineModel(db.Model):
    __tablename__ = "order_line"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cart_id = db.Column(db.Integer, db.ForeignKey("cart.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    product_upn = db.Column(db.BigInteger)
    product_description = db.Column(db.String(80))
    product_price = db.Column(db.Numeric)
    product_quantity = db.Column(db.SmallInteger)
    created_at = db.Column(db.DateTime)
    modified_at = db.Column(db.DateTime)
    removed_at = db.Column(db.DateTime, nullable=True)


class ReceiptModel(db.Model):
    __tablename__ = "receipt"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cart_id = db.Column(db.Integer, db.ForeignKey("cart.id"))
    subtotal = db.Column(db.Numeric)
    fee = db.Column(db.Numeric)
    total = db.Column(db.Numeric)
    created_at = db.Column(db.DateTime)


class UserReceiptModel(db.Model):
    __tablename__ = "user_receipt"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    receipt_id = db.Column(db.Integer, db.ForeignKey("receipt.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    amount_owed = db.Column(db.Numeric)
    is_paid = db.Column(db.Boolean)
    created_at = db.Column(db.DateTime)
    paid_at = db.Column(db.DateTime, nullable=True)


user_post_args = reqparse.RequestParser()
user_post_args.add_argument("name", type=str, help="Name is required.", required=True)
user_post_args.add_argument("sid", type=str, help="Sid is required.", required=True)

cart_args = reqparse.RequestParser()
cart_args.add_argument("user_id", type=int, help="UserId is required.", required=True)
cart_args.add_argument(
    "product_upn", type=int, help="ProductUpn is required.", required=True
)
cart_args.add_argument(
    "product_description",
    type=str,
    help="ProductDescription is required.",
    required=True,
)
cart_args.add_argument(
    "product_price", type=float, help="ProductPrice is required.", required=True
)

cart_delete_args = reqparse.RequestParser()
cart_delete_args.add_argument(
    "user_id", type=int, help="UserId is required.", required=True
)
cart_delete_args.add_argument(
    "product_upn", type=int, help="ProductUpn is required.", required=True
)

receipt_pay_args = reqparse.RequestParser()
receipt_pay_args.add_argument(
    "user_id", type=int, help="UserId is required.", required=True
)
receipt_pay_args.add_argument(
    "receipt_id", type=int, help="ReceiptId is required.", required=True
)

# template fields
user_fields = {
    "id": fields.Integer,
    "name": fields.String,
    "sid": fields.String,
    "created_at": fields.DateTime,
}
cart_fields = {
    "id": fields.Integer,
    "total": fields.Float,
    "created_at": fields.DateTime,
    "purchased_at": fields.DateTime,
}
active_cart_fields = {"cartId": fields.Integer, "modifiedAt": fields.DateTime}
order_line_fields = {
    "id": fields.Integer,
    "cart_id": fields.Integer,
    "user_id": fields.Integer,
    "product_upn": fields.Integer,
    "product_description": fields.String,
    "product_price": fields.Float,
    "product_quantity": fields.Integer,
    "created_at": fields.DateTime,
    "modified_at": fields.DateTime,
    "removed_at": fields.DateTime,
}
receipt_fields = {
    "id": fields.Integer,
    "cart_id": fields.Integer,
    "subtotal": fields.Float,
    "fee": fields.Float,
    "total": fields.Float,
    "created_at": fields.DateTime,
}
user_receipt_fields = {
    "id": fields.Integer,
    "receipt_id": fields.Integer,
    "user_id": fields.Integer,
    "amount_owed": fields.Float,
    "is_paid": fields.Boolean,
    "created_at": fields.DateTime,
    "paid_at": fields.DateTime,
}

# !remove when deploying, resets db
# with app.app_context():
#     db.drop_all()
#     db.create_all()


class User(Resource):
    @marshal_with(user_fields)
    def get(self):
        users = UserModel.query.all()
        return users, 200

    @marshal_with(user_fields)
    def post(self):
        args = user_post_args.parse_args()
        user = UserModel.query.filter_by(name=args["name"]).first()
        if user:
            abort(409, message="Name already exists")
        user = UserModel(
            name=args["name"], sid=args["sid"], created_at=datetime.datetime.now()
        )
        db.session.add(user)
        db.session.commit()
        return user, 201


class UserId(Resource):
    @marshal_with(user_fields)
    def get(self, id):
        user = UserModel.query.get(id)
        if user is None:
            abort(404, message="UserID not found")
        return user, 200


class Cart(Resource):
    @marshal_with(order_line_fields)
    def get(self):
        active_cart = ActiveCartModel.query.first()
        # there should always be an active cart
        if active_cart is None:
            abort(404, message="No active cart")
        order_lines = OrderLineModel.query.filter_by(cart_id=active_cart.cart_id).all()
        return order_lines, 200

    # !remove id and cart_id from response
    @marshal_with(order_line_fields)
    def post(self):
        active_cart = ActiveCartModel.query.first()
        # if no active cart, create one
        if active_cart is None:
            cart = CartModel(created_at=datetime.datetime.now())
            db.session.add(cart)
            db.session.commit()

            active_cart = ActiveCartModel(
                cart_id=cart.id, modified_at=datetime.datetime.now()
            )
            db.session.add(active_cart)
            db.session.commit()

        args = cart_args.parse_args()
        if UserModel.query.get(args["user_id"]) is None:
            abort(404, message="User not found")
        order_line = OrderLineModel.query.filter_by(
            cart_id=active_cart.cart_id,
            user_id=args["user_id"],
            product_upn=args["product_upn"],
        ).first()

        # if order_line exists, increment quantity
        if order_line:
            order_line.product_quantity += 1
            order_line.modified_at = datetime.datetime.now()
        else:
            order_line = OrderLineModel(
                cart_id=active_cart.cart_id,
                user_id=args["user_id"],
                product_upn=args["product_upn"],
                product_description=args["product_description"],
                product_price=args["product_price"],
                product_quantity=1,
                created_at=datetime.datetime.now(),
            )
            db.session.add(order_line)
        active_cart.cart.total += order_line.product_price
        db.session.commit()
        return order_line, 201

    @marshal_with(order_line_fields)
    def delete(self):
        active_cart = ActiveCartModel.query.first()
        if active_cart is None:
            abort(404, message="No active cart")
        args = cart_delete_args.parse_args()
        order_line = OrderLineModel.query.filter_by(
            cart_id=active_cart.cart_id,
            user_id=args["user_id"],
            product_upn=args["product_upn"],
        ).first()

        # if order_line exists, decrement quantity
        if order_line is None:
            abort(404, message="Product not found")
        if order_line.product_quantity == 1:
            db.session.delete(order_line)
        else:
            order_line.product_quantity -= 1
            order_line.modified_at = datetime.datetime.now()
        db.session.commit()

        remaining_order_lines = OrderLineModel.query.filter_by(
            cart_id=active_cart.cart_id
        ).all()
        return remaining_order_lines, 200


class CartTotal(Resource):
    def get(self):
        active_cart = ActiveCartModel.query.first()
        if active_cart is None:
            abort(404, message="No active cart")
        return {"total": str(active_cart.cart.total)}, 200


class CartPurchase(Resource):
    @marshal_with(receipt_fields)
    def post(self):
        active_cart = ActiveCartModel.query.first()
        if active_cart is None:
            abort(404, message="No active cart")

        # calculate subtotal, fee, total
        subtotal = Decimal("0.00")
        user_subtotals = {}
        for order_line in active_cart.cart.order_lines:
            line_total = (
                Decimal(str(order_line.product_price)) * order_line.product_quantity
            )
            subtotal += line_total
            if order_line.user_id in user_subtotals:
                user_subtotals[order_line.user_id] += line_total
            else:
                user_subtotals[order_line.user_id] = line_total

        # sanity check, should never happen
        if subtotal != active_cart.cart.total:
            abort(500, message="Subtotal does not match cart total")

        fee = Decimal("6.95")
        total = subtotal + fee

        fee_per_user = fee / Decimal(str(len(user_subtotals)))
        for user_id, user_subtotal in user_subtotals.items():
            user_subtotals[user_id] += fee_per_user.quantize(Decimal("0.00"))

        # add cart to receipts
        receipt = ReceiptModel(
            cart_id=active_cart.cart_id,
            subtotal=subtotal,
            fee=fee,
            total=total,
            created_at=datetime.datetime.now(),
        )
        db.session.add(receipt)

        # add user_receipts
        for user_id, user_subtotal in user_subtotals.items():
            user_receipt = UserReceiptModel(
                user_id=user_id,
                receipt_id=receipt.id,
                amount_owed=user_subtotal,
                is_paid=False,
                created_at=datetime.datetime.now(),
            )
            db.session.add(user_receipt)

        # remove cart from active_cart
        db.session.delete(active_cart)
        db.session.commit()
        return receipt, 201


class CardId(Resource):
    @marshal_with(order_line_fields)
    def get(self, id):
        cart = CartModel.query.get(id)
        if cart is None:
            abort(404, message="CartId not found")
        order_lines = OrderLineModel.query.filter_by(cart_id=cart.id).all()
        return order_lines, 200


class Receipt(Resource):
    @marshal_with(receipt_fields)
    def get(self):
        receipts = ReceiptModel.query.all()
        return receipts, 200


class ReceiptId(Resource):
    @marshal_with(user_receipt_fields)
    def get(self, user_id):
        receipt = UserReceiptModel.query.filter_by(user_id=user_id).all()
        if receipt is None:
            abort(404, message="User has no receipts")
        return receipt, 200


class ReceiptPay(Resource):
    @marshal_with(user_receipt_fields)
    def post(self):
        args = receipt_pay_args.parse_args()
        user_receipt = UserReceiptModel.query.filter_by(
            user_id=args["user_id"], receipt_id=args["receipt_id"]
        ).first()
        if user_receipt is None:
            abort(404, message="User receipt not found")
        user_receipt.is_paid = True
        user_receipt.paid_at = datetime.datetime.now()
        db.session.commit()
        return user_receipt, 200


api.add_resource(User, "/user")
api.add_resource(UserId, "/user/<int:id>")
api.add_resource(Cart, "/cart")
api.add_resource(CartPurchase, "/cart/purchase")
api.add_resource(CardId, "/cart/<int:id>")
api.add_resource(Receipt, "/receipt")
api.add_resource(ReceiptId, "/receipt/<int:user_id>")
api.add_resource(ReceiptPay, "/receipt/pay")

# change debug to False when deploying
if __name__ == "__main__":
    app.run(port=8000, debug=True)
