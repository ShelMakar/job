from flask import Flask
from flask_restful import Api
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy
import config

app = Flask(__name__)
app.config.from_object(config)
api = Api(app)
jwt = JWTManager(app)
db = SQLAlchemy(app)

from app.api import auth, referral, user

api.add_resource(auth.Register, '/register')
api.add_resource(auth.Login, '/login')
api.add_resource(referral.ReferralCode, '/referral_code')
api.add_resource(referral.GetReferralCode, '/referral_code/<string:email>')
api.add_resource(referral.RegisterReferral, '/register/<string:referral_code>')
api.add_resource(user.GetReferrals, '/referrals/<int:user_id>')

if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)