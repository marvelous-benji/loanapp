from flask_admin.contrib.sqla import ModelView
from flask_admin import BaseView, expose
from loan_app import db,login_manager, app, admin
from loan_app.models import User, Loan
from flask import url_for, app



class UserView(ModelView):
    column_exclude_list = ['password','occupation','account_number','bvn',
    'bank','address','next_name','next_address','reasons']

class TransView(BaseView):
    @expose('/')
    def trans(self):
        return self.render('admin/trans.html')

admin.add_view(UserView(User, db.session))
admin.add_view(UserView(Loan, db.session))
admin.add_view(TransView(name='Transactions', endpoint='transaction'))
