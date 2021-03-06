from datetime import datetime
from datetime import timedelta as td
from loan_app import db,login_manager, app, admin
from flask_login import UserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask_admin.contrib.sqla import ModelView
from flask_admin import BaseView, expose
#from flask_login import login_user, current_user, logout_user, login_required


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

transactions = db.Table('transactions',db.Column('id',db.Integer, primary_key=True),
db.Column('user_id',db.Integer,db.ForeignKey('user.id')),
db.Column('loan_id',db.Integer,db.ForeignKey('loan.id')))



class User(db.Model,UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    confirmed = db.Column(db.Boolean, default=False)
    occupation = db.Column(db.String(200))
    phone_number = db.Column(db.Integer)
    account_number = db.Column(db.String(10))
    bvn = db.Column(db.String(11))
    bank = db.Column(db.String(120))
    address = db.Column(db.String(250))
    next_name = db.Column(db.String(120))
    next_address = db.Column(db.String(250))
    reasons = db.Column(db.Text)
    payment_index = db.Column(db.Float,default=0)
    approved = db.Column(db.Boolean, default=False)
    details_verified = db.Column(db.Boolean, default=False)
    historys = db.relationship('History', backref='loanee')

    def get_reset_token(self,expire=1800):
        s = Serializer(app.config['SECRET_KEY'],expire)
        return s.dumps({'user_id':self.id}).decode('utf-8')

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return f"User('{self.username}','{self.email}','{self.image_file}')"

    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id}).decode('utf-8')

    def confirm(self,token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            data = s.loads(token.encode('utf-8'))
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True



    def __repr__(self):
        return f"User('{self.username}','{self.email}','{self.image_file}')"

class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Integer, nullable=False)
    duration = db.Column(db.Integer, nullable=False)
    rate = db.Column(db.Float, nullable=False)
    interest = db.Column(db.Float, nullable=False)
    date_of_payment = db.Column(db.DateTime,default=datetime.utcnow)
    users = db.relationship('User',
            secondary=transactions,
            backref=db.backref('loans', lazy='dynamic'),
            lazy='dynamic')


    def __repr__(self):
        return f"Loan('{self.amount}','{self.duration}')"


'''class UserView(ModelView):
    column_exclude_list = ['password','occupation','account_number','bvn',
    'bank','address','next_name','next_address','reasons']

class TransView(BaseView):
    @expose('/')
    def trans(self):
        return self.render('admin/trans.html')









admin.add_view(UserView(User, db.session))
admin.add_view(UserView(Loan, db.session))
admin.add_view(TransView(name='Transactions', endpoint='transaction'))'''
class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trans_date = db.Column(db.DateTime, default=datetime.utcnow)
    loan = db.Column(db.Integer, default=0)
    payment = db.Column(db.Integer, default=0)
    receipt = db.Column(db.Integer,default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


    def __repr__(self):
        return f"Loan('{self.loan}','{self.payment}')"
