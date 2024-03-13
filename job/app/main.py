from http import HTTPStatus
import requests
from flask import Flask, request, jsonify
from flask_restful import Resource, Api
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from flask_sqlalchemy import SQLAlchemy
from datetime import timedelta, datetime
from werkzeug.security import generate_password_hash, check_password_hash
from gevent.pywsgi import WSGIServer
from flask_marshmallow import Marshmallow
from marshmallow_sqlalchemy import SQLAlchemySchema
from flask_caching import Cache
from flask_swagger_ui import get_swaggerui_blueprint

app = Flask(__name__)
api = Api(app)
jwt = JWTManager(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mydatabase.db'
app.config['JWT_SECRET_KEY'] = 'super-secret'
app.config['CACHE_TYPE'] = 'simple'
app.config['CACHE_DEFAULT_TIMEOUT'] = 300
cache = Cache(app)
db = SQLAlchemy(app)
ma = Marshmallow(app)

SWAGGER_URL = '/swagger'
API_URL = '/static/swagger.json'
swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "Referral System API"
    }
)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    referral_code = db.Column(db.String(20))
    referral_code_expiry = db.Column(db.DateTime)

    def __init__(self, email, password, referral_code, referral_code_expiry):
        self.email = email
        self.password = password
        self.referral_code = referral_code
        self.referral_code_expiry = referral_code_expiry

class Referral(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    referrer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class UserSchema(SQLAlchemySchema):
    class Meta:
        model = User
        load_instance = True

user_schema = UserSchema()
users_schema = UserSchema(many=True)

def enrich_user_data(email):
    clearbit_url = f'https://person.clearbit.com/v1/people/email/{email}?fields=name'
    clearbit_response = requests.get(clearbit_url)
    if clearbit_response.status_code == 200:
        return clearbit_response.json().get('name', {})
    return {}

def verify_email(email):
    emailhunter_url = f'https://api.emailhunter.co/v2/email-verifier?email={email}'
    emailhunter_response = requests.get(emailhunter_url)
    if emailhunter_response.status_code == 200:
        return emailhunter_response.json().get('data', {}).get('status') == 'deliverable'
    return False

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not verify_email(data['email']):
        return jsonify({"message": "Неверный адрес электронной почты."}), HTTPStatus.BAD_REQUEST
    if User.query.filter_by(email=data['email']).first():
        return jsonify({"message": "Пользователь с таким адресом электронной почты уже существует."}), HTTPStatus.BAD_REQUEST
    referral_code = data.get('referral_code')
    referral_code_expiry = data.get('referral_code_expiry')
    new_user = User(
        email=data['email'],
        password=generate_password_hash(data['password']),
        referral_code=referral_code,
        referral_code_expiry=referral_code_expiry
    )
    db.session.add(new_user)
    db.session.commit()

    enriched_data = enrich_user_data(data['email'])

    if referral_code:
        referrer = User.query.filter_by(referral_code=referral_code).first()
        if referrer:
            new_referral = Referral(user_id=new_user.id, referrer_id=referrer.id)
            db.session.add(new_referral)
            db.session.commit()

    return jsonify({"message": "Пользователь успешно создан.", **enriched_data}), HTTPStatus.CREATED

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()
    if user and check_password_hash(user.password, data['password']):
        access_token = create_access_token(identity=user.id)
        return jsonify(access_token=access_token), HTTPStatus.OK
    return jsonify({"message": "Неверный адрес электронной почты или пароль."}), HTTPStatus.UNAUTHORIZED

def generate_referral_code(request):
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    code = request.json['code']
    expiry = request.json['expiry']
    user.referral_code = code
    user.code_expiry = expiry
    db.session.commit()
    cache.set(user.referral_code, user_id, timeout=expiry)
    return user_schema.jsonify(user)

class ReferralCode(Resource):
    @jwt_required
    def post(self):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if user.referral_code:
            return jsonify({"message": "У вас уже есть активный реферальный код."}), HTTPStatus.BAD_REQUEST
        expiry = datetime.utcnow() + timedelta(days=30)
        user.referral_code = generate_referral_code(request)
        user.referral_code_expiry = expiry
        db.session.commit()
        return jsonify({"message": "Реферальный код успешно создан.", "referral_code": user.referral_code, "expiry": user.referral_code_expiry}), HTTPStatus.CREATED

    @jwt_required
    def delete(self):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user.referral_code:
            return jsonify({"message": "У вас нет активного реферального кода."}), HTTPStatus.BAD_REQUEST
        user.referral_code = None
        user.referral_code_expiry = None
        db.session.commit()
        cache.delete(user.referral_code)
        return jsonify({"message": "Реферальный код успешно удален."}), HTTPStatus.OK

class GetReferralCode(Resource):
    def get(self, email):
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({"message": "Пользователь не найден."}), HTTPStatus.NOT_FOUND
        if not user.referral_code:
            return jsonify({"message": "У пользователя нет активного реферального кода."}), HTTPStatus.BAD_REQUEST
        return jsonify({"referral_code": user.referral_code, "expiry": user.referral_code_expiry}), HTTPStatus.OK

class RegisterReferral(Resource):
    def post(self, referral_code):
        referrer = User.query.filter_by(referral_code=referral_code).first()
        if not referrer:
            return jsonify({"message": "Неверный реферальный код."}), HTTPStatus.BAD_REQUEST
        data = request.get_json()
        if User.query.filter_by(email=data['email']).first():
            return jsonify({"message": "Пользователь с данной почтой уже существует."}), HTTPStatus.BAD_REQUEST
        new_user = User(
            email=data['email'],
            password=generate_password_hash(data['password'])
        )
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": "Пользователь создан успешно."}), HTTPStatus.CREATED

class GetReferrals(Resource):
    @jwt_required
    def get(self, user_id):
        user = User.query.get(user_id)
        if not user:
            return jsonify({"message": "Пользователь не найден."}), HTTPStatus.NOT_FOUND
        referrals = Referral.query.filter_by(referrer_id=user_id).all()
        referral_list = []
        for referral in referrals:
            referral_list.append({
                "id": referral.user_id,
                "email": referral.user.email,
                "date_created": referral.date_created
            })
        return jsonify(referral_list), HTTPStatus.OK

api.add_resource(ReferralCode, '/referral_code')
api.add_resource(GetReferralCode, '/referral_code/<string:email>')
api.add_resource(RegisterReferral, '/register/<string:referral_code>')
api.add_resource(GetReferrals, '/referrals/<int:user_id>')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    http_server = WSGIServer(('0.0.0.0', 5000), app)
    http_server.serve_forever()
