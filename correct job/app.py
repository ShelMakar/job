from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret'  # секретный ключ для JWT
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///referral_system.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

jwt = JWTManager(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Модели

# Модель пользователя
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

# Модель реферального кода
class ReferralCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    expiry_date = db.Column(db.DateTime, nullable=False)

# Модель реферала
class Referral(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    referrer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    referred_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    referrer = db.relationship('User', foreign_keys=[referrer_id], backref='referrals_given')
    referred = db.relationship('User', foreign_keys=[referred_id], backref='referrals_received')

# Создание всех таблиц в базе данных
with app.app_context():
    db.create_all()

# Эндпоинты

# Регистрация нового пользователя
@app.route('/register', methods=['POST'])
async def register():
    data = await request.get_json()
    new_user = User(email=data['email'], password=data['password'])
    db.session.add(new_user)
    await db.session.commit()
    return jsonify({'message': 'Пользователь успешно создан'}), 201

# Аутентификация пользователя и выдача JWT токена
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()
    if user and user.password == data['password']:
        access_token = create_access_token(identity=user.id)
        return jsonify(access_token=access_token), 200
    return jsonify({'message': 'Неверные учетные данные'}), 401

# Создание реферального кода
@app.route('/referral-code', methods=['POST'])
@jwt_required()
def create_referral_code():
    current_user_id = get_jwt_identity()
    # Проверяем, существует ли уже активный код у пользователя, и удаляем его при необходимости
    existing_referral_code = ReferralCode.query.filter_by(user_id=current_user_id).first()
    if existing_referral_code:
        db.session.delete(existing_referral_code)
        db.session.commit()
    data = request.get_json()
    expiry_date = datetime.strptime(data['expiry_date'], '%Y-%m-%d')
    new_referral_code = ReferralCode(code=data['code'], user_id=current_user_id, expiry_date=expiry_date)
    db.session.add(new_referral_code)
    db.session.commit()
    return jsonify({'message': 'Реферральный код успешно создан'}), 201

# Удаление реферального кода
@app.route('/delete-referral-code', methods=['DELETE'])
@jwt_required()
def delete_referral_code():
    current_user_id = get_jwt_identity()
    referral_code = ReferralCode.query.filter_by(user_id=current_user_id).first()
    if referral_code:
        db.session.delete(referral_code)
        db.session.commit()
        return jsonify({'message': 'Реферральный код успешно удален'}), 200
    return jsonify({'message': 'У пользователя не найден реферральный код'}), 404

# Получение реферального кода по email адресу реферера
@app.route('/get-referral-code', methods=['GET'])
def get_referral_code():
    referrer_email = request.args.get('referrer_email')
    referrer = User.query.filter_by(email=referrer_email).first()
    if referrer:
        referral_code = ReferralCode.query.filter_by(user_id=referrer.id).first()
        if referral_code:
            return jsonify({'referral_code': referral_code.code}), 200
    return jsonify({'message': 'Реферральный код не найден'}), 404

# Регистрация по реферальному коду
@app.route('/register-by-referral-code', methods=['POST'])
def register_by_referral_code():
    data = request.get_json()
    referral_code = data['referral_code']
    referral_code_obj = ReferralCode.query.filter_by(code=referral_code).first()
    if referral_code_obj:
        # Создаем нового пользователя
        new_user = User(email=data['email'], password=data['password'])
        db.session.add(new_user)
        db.session.commit()
        # Связываем пользователя с реферером
        new_referral = Referral(referrer_id=referral_code_obj.user_id, referred_id=new_user.id)
        db.session.add(new_referral)
        db.session.commit()
        return jsonify({'message': 'Пользователь успешно зарегистрировался с помощью реферального кода'}), 201
    return jsonify({'message': 'Некорректный реферральный код'}), 400

# Получение информации о рефералах по id реферера
@app.route('/referrals/<referrer_id>', methods=['GET'])
@jwt_required()
def get_referrals(referrer_id):
    current_user_id = get_jwt_identity()
    if current_user_id == referrer_id:
        referrals = Referral.query.filter_by(referrer_id=referrer_id).all()
        referral_ids = [referral.referred_id for referral in referrals]
        return jsonify({'referrals': referral_ids}), 200
    return jsonify({'message': 'Пользователь неавторизован'}), 401

if __name__ == '__main__':
    app.run(debug=True)
