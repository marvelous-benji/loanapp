from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, IntegerField, DateTimeField, FloatField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from loan_app.models import User, Loan
from flask_login import current_user

class RegistrationForm(FlaskForm):
	username = StringField('Username', validators=[DataRequired(), Length(min=4,max=20)])
	email = StringField('Email', validators=[DataRequired(), Email()])
	password = PasswordField('Password', validators=[DataRequired(), Length(min=8,max=20)])
	confirm = PasswordField('Confirm Password', validators=[DataRequired(),
	Length(min=8,max=20), EqualTo('password')])
	submit = SubmitField('Signup')

	def validate_username(self,username):
		user = User.query.filter_by(username=username.data).first()
		if user:
			raise ValidationError('Username Already Exists')

	def validate_email(self,email):
		user = User.query.filter_by(email=email.data).first()
		if user:
			raise ValidationError('Email Address Already Exists')

class WorkForm(FlaskForm):
    occupation = StringField('Occupation', validators=[DataRequired()])
    phone_number = StringField('Phone number', validators=[DataRequired()])
    account_number = StringField('acount number', validators=[DataRequired(), Length(min=10,max=10)])
    bvn = PasswordField('enter your bvn', validators=[DataRequired(), Length(min=11,max=11)])
    bank = StringField('Bank name', validators=[DataRequired()])
    address = TextAreaField('Your house address', validators=[DataRequired()])
    next_of_kin = StringField('next of kin name', validators=[DataRequired()])
    next_address = TextAreaField('next of kin address', validators=[DataRequired()])
    reasons = TextAreaField('Reasons for the loan', validators=[DataRequired()])
    submit = SubmitField('Save')

    def validate_phone_number(self,phone_number):
        if not phone_number.data.startswith('+') or len(phone_number.data[4:]) != 10:
            raise ValidationError('Invalid phone number')

    def validate_account_number(self,account_number):
        if not account_number.data.isnumeric():
            raise ValidationError('account number must contain only digits')

    def validate_bvn(self,bvn):
        if not bvn.data.isnumeric():
            raise ValidationError('BVN must contain only digits')

class LoginForm(FlaskForm):
	email = StringField('Email', validators=[DataRequired(), Email()])
	password = PasswordField('Password', validators=[DataRequired(), Length(min=8,max=20)])
	remember = BooleanField('Remember Me')
	submit = SubmitField('Login')

'''class LoanForm(FlaskForm):
    loan_amount = IntegerField('Amount', validators=[DataRequired()])
    duration = IntegerField('Duration',validators=[DataRequired()])
    rate = FloatField('Rate',validators=[DataRequired()])
    date_of_payment = DateTimeField('Payment_date', validators=[DataRequired()])
    submit = SubmitField('Request loan')'''

class EditProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4,max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    picture = FileField('Update Profile Picture', validators=[FileAllowed(['jpg','png','jpeg'])])
    submit = SubmitField('Update Account')

    def validate_username(self,username):
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('Username Already Exists')

    def validate_email(self,email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('Email Already Exists')

class RequestResetForm(FlaskForm):
	email = StringField('Email', validators=[DataRequired(), Email()])
	submit = SubmitField('Request Password Reset')

	def validate_email(self,email):
		user = User.query.filter_by(email=email.data).first()
		if user is None:
			raise ValidationError('Email address not found')

class ResetPasswordForm(FlaskForm):
	password = PasswordField('Password', validators=[DataRequired(), Length(min=8,max=20)])
	confirm = PasswordField('Confirm Password', validators=[DataRequired(),
	Length(min=8,max=20), EqualTo('password')])
	submit = SubmitField('Reset Password')
