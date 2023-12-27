from flask import Flask
from flask_restful import Api, Resource, reqparse, abort
import datetime

app = Flask(__name__)
api = Api(app)

users = {
    0: {"name": "Alex", "sid": "12345", "createdAt": "2023-12-20T10:10:38.732464"},
    1: {"name": "Omar", "sid": "23456", "createdAt": "2023-12-20T10:10:40.732464"}
}

task_post_args = reqparse.RequestParser()
task_post_args.add_argument("name", type=str, help="Name is required.", required=True)
task_post_args.add_argument("sid", type=str, help="Sid is required.", required=True)

class User(Resource):
    def get(self):
        return list(users.values())

    def post(self):
        args = task_post_args.parse_args()
        users[len(users)] = {"name": args["name"], "sid": args["sid"], "createdAt": datetime.datetime.now().isoformat()}
        return users[len(users)-1]


class UserId(Resource):
    def get(self, id):
        if(id not in users):
            abort(404, message="UserID not found")
        return users[id]    

class Cart(Resource):
    def get(self):
        pass


api.add_resource(User, '/user')
api.add_resource(UserId, '/user/<int:id>')
api.add_resource(Cart, '/cart')
# api.add_resource(CartPurchase, '/cart/')
# api.add_resource(Receipt, '/receipt')

if __name__ == '__main__':
    app.run(debug=True)
