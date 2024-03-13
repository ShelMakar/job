from flask_restful import Resource
from flask_jwt_extended import create_access_token
from werkzeug.security import safe_str_cmp, generate_password_hash, check_password_hash
from http import HTTPStatus
from flask import request, jsonify
from app.models.user import User

class Register(Resource):
    def post(self):
        data = request.get_json()
        if User.query.filter_by(email=data['email']).first():
            return jsonify({"message": "A user with that email already exists."}), HTTPStatus.BAD_REQUEST
        new_user = User(
            email=data['email'],
            password=generate_password_hash(data['password'])
        )
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": "User created successfully."}), HTTPStatus.CREATED

class Login(Resource):
    def post(self):
        data = request.get_json()
        user = User.query.filter_by(email=data['email']).first()
        if user and check_password_hash(user.password, data['password']):
            access_token = create_access_token(identity=user.id)
            return jsonify(access_token=access_token), HTTPStatus.OK
        return jsonify({"message": "Invalid email or password."}), HTTPStatus.UNAUTHORIZED