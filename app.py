from flask import Flask
from flask_restful import Api, Resource, reqparse, abort, fields, marshal_with
from flask_sqlalchemy import SQLAlchemy
import datetime

app = Flask(__name__)
api = Api(app)
app.config[
    "SQLALCHEMY_DATABASE_URI"
] = "postgresql://username:password@localhost/dbname"
db = SQLAlchemy(app)


# All of the table models
class UserModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    sid = db.Column(db.String(80))
    created_at = db.Column(db.DateTime)
    order_lines = db.relationship("OrderLineModel", backref="user", lazy=True)


class CartModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime)
    purchased_at = db.Column(db.DateTime, nullable=True)
    active_cart = db.relationship("ActiveCartModel", backref="cart", uselist=False)
    order_lines = db.relationship("OrderLineModel", backref="cart", lazy=True)


class ActiveCartModel(db.Model):
    cart_id = db.Column(db.Integer, db.ForeignKey("cart.id"), primary_key=True)
    modified_at = db.Column(db.DateTime)


class OrderLineModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
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
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey("cart.id"))
    subtotal = db.Column(db.Numeric)
    fee = db.Column(db.Numeric)
    total = db.Column(db.Numeric)
    created_at = db.Column(db.DateTime)


class UserReceiptModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    receipt_id = db.Column(db.Integer, db.ForeignKey("receipt.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    amount_owed = db.Column(db.Numeric)
    is_paid = db.Column(db.Boolean)
    created_at = db.Column(db.DateTime)
    paid_at = db.Column(db.DateTime, nullable=True)


users = {
    0: {"name": "Alex", "sid": "12345", "createdAt": "2023-12-20T10:10:38.732464"},
    1: {"name": "Omar", "sid": "23456", "createdAt": "2023-12-20T10:10:40.732464"},
}

user_post_args = reqparse.RequestParser()
user_post_args.add_argument("name", type=str, help="Name is required.", required=True)
user_post_args.add_argument("sid", type=str, help="Sid is required.", required=True)

cart_post_args = reqparse.RequestParser()
cart_post_args.add_argument(
    "userId", type=int, help="UserId is required.", required=True
)
cart_post_args.add_argument(
    "product_upn", type=int, help="ProductUpn is required.", required=True
)
cart_post_args.add_argument(
    "product_description",
    type=str,
    help="ProductDescription is required.",
    required=True,
)
cart_post_args.add_argument(
    "product_price", type=float, help="ProductPrice is required.", required=True
)


# template fields
user_fields = {
    "id": fields.Integer,
    "name": fields.String,
    "sid": fields.String,
    "createdAt": fields.DateTime,
}

cart_fields = {
    "id": fields.Integer,
    "createdAt": fields.DateTime,
    "purchasedAt": fields.DateTime,
}

active_cart_fields = {"cartId": fields.Integer, "modifiedAt": fields.DateTime}

order_line_fields = {
    "id": fields.Integer,
    "cartId": fields.Integer,
    "userId": fields.Integer,
    "productUpn": fields.Integer,
    "productDescription": fields.String,
    "productPrice": fields.Float,
    "productQuantity": fields.Integer,
    "createdAt": fields.DateTime,
    "modifiedAt": fields.DateTime,
    "removedAt": fields.DateTime,
}

receipt_fields = {
    "id": fields.Integer,
    "cartId": fields.Integer,
    "subtotal": fields.Float,
    "fee": fields.Float,
    "total": fields.Float,
    "createdAt": fields.DateTime,
}

user_receipt_fields = {
    "id": fields.Integer,
    "receiptId": fields.Integer,
    "userId": fields.Integer,
    "amountOwed": fields.Float,
    "isPaid": fields.Boolean,
    "createdAt": fields.DateTime,
    "paidAt": fields.DateTime,
}


class User(Resource):
    @marshal_with(user_fields)
    def get(self):
        users = UserModel.query.all()
        return users, 200

    @marshal_with(user_fields)
    def post(self):
        args = user_post_args.parse_args()
        user = UserModel.query.get(args["name"])
        if user:
            abort(409, message="User with name already exists")
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

        args = cart_post_args.parse_args()
        order_line = OrderLineModel.query.filter_by(
            cart_id=active_cart.cart_id,
            user_id=args["userId"],
            product_upn=args["product_upn"],
        ).first()

        # if order_line exists, increment quantity
        if order_line:
            order_line.product_quantity += 1
            order_line.modified_at = datetime.datetime.now()
        else:
            order_line = OrderLineModel(
                cart_id=active_cart.cart_id,
                user_id=args["userId"],
                product_upn=args["product_upn"],
                product_description=args["product_description"],
                product_price=args["product_price"],
                product_quantity=1,
                created_at=datetime.datetime.now(),
            )
            db.session.add(order_line)
        db.session.commit()
        return order_line, 201


api.add_resource(User, "/user")
api.add_resource(UserId, "/user/<int:id>")
api.add_resource(Cart, "/cart")
# api.add_resource(CartPurchase, '/cart/')
# api.add_resource(Receipt, '/receipt')

if __name__ == "__main__":
    app.run(debug=True)
