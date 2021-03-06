from loan_app import app,db,bcrypt, mail, admin
from flask import render_template,redirect,url_for, request,flash, abort, jsonify
from loan_app.forms import RegistrationForm, LoginForm,WorkForm, EditProfileForm, RequestResetForm, ResetPasswordForm
from loan_app.models import User, Loan, History
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message
from threading import Thread
from PIL import Image
from loan_app.dectors import detail_required, check_confirm
import os
import secrets
from datetime import timedelta, datetime
from flask_admin.contrib.sqla import ModelView
from flask_admin import BaseView, expose
import stripe
from math import ceil

stripe_keys = {
	'secret_key': os.getenv('STRIPE_SK'),
	'public_key': os.getenv('STRIPE_PBK')
}

stripe.api_key = stripe_keys['secret_key']




def send_async_email(app, msg):
	with app.app_context():
		mail.send(msg)


def send_email(msg):
	thr = Thread(target=send_async_email, args=[app, msg])
	thr.start()
	return thr


@app.route('/')
def home():
	return render_template('home.html')

@app.route('/login', methods=['GET','POST'])
def login():
	if current_user.is_authenticated:
		return redirect(url_for('home'))
	form = LoginForm()
	if form.validate_on_submit():
		user = User.query.filter_by(email=form.email.data).first()
		if  user and bcrypt.check_password_hash(user.password,form.password.data):
			login_user(user,form.remember.data)
			next_page = request.args.get('next')
			if current_user.username == 'admin':
				flash('Welcome Admin','success')
				return redirect('/admin')
			return redirect(next_page) if next_page else redirect(url_for('account'))
			flash('Login Successful','success')
		else:
			flash('You entered invalid credentials','danger')
			return redirect(url_for('login'))
	return render_template('login.html', form=form)

def save_picture(form_picture):
	rand_hex = secrets.token_hex(8)
	_,ext = os.path.splitext(form_picture.filename)
	picture_fn = rand_hex + ext
	picture_path = os.path.join(app.root_path,'static',picture_fn)
	size = (200,200)
	img = Image.open(form_picture)
	img.thumbnail(size)
	img.save(picture_path)
	return picture_fn


@app.route('/user/logout')
@login_required
#@check_confirm
def logout():
	logout_user()
	return redirect(url_for('home'))

@app.route('/user/register', methods=['GET','POST'])
def signup():
	if current_user.is_authenticated:
		return redirect(url_for('home'))
	form = RegistrationForm()
	if form.validate_on_submit():
		password_hash = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
		new_user = User(username=form.username.data,email=form.email.data,password=password_hash)
		db.session.add(new_user)
		db.session.commit()
		token = new_user.generate_confirmation_token()
		msg = Message('Confirm Email', sender=app.config['MAIL_USERNAME'], recipients=[new_user.email])
		msg.body = f'''
		To confirm your account, follow the link:
		{url_for('confirm', token=token, _external=True)}
		link is valid for 1 hour
		'''
		send_email(msg)
		flash('Registration successful','success')
		return redirect(url_for('login'))
	return render_template('register.html', form=form)

@app.route('/confirm/<token>')
@login_required
def confirm(token):
	if current_user.confirmed:
		return redirect(url_for('home'))
	if current_user.confirm(token):
		db.session.commit()
		flash('You have confirmed your account','success')
	else:
		flash('Confirmation link has expired or is invalid')
	return redirect(url_for('home'))

@app.route('/unconfirmed')
def unconfirmed():
	if current_user.is_anonymous or current_user.confirmed:
		return redirect(url_for('home'))
	return render_template('unconfirmed.html')

@app.route('/confirm')
@login_required
def resend_confirmation():
	token = current_user.generate_confirmation_token()
	msg = Message('Confirm Email', sender=app.config['MAIL_USERNAME'], recipients=[current_user.email])
	msg.body = f'''
			To confirm your account, follow the link:
	{url_for('confirm', token=token, _external=True)}
	link is valid for 1 hour
	'''
	send_email(msg)
	flash('A new confirmation email has been sent to you by email','info')
	return redirect(url_for('home'))

@app.route('/user/account')
@login_required
@check_confirm
def account():
	new_user = User.query.filter_by(email=current_user.email).first()
	debts = new_user.loans.all()
	return render_template('account.html', func=timedelta, func1=datetime, debts=debts,)

@app.route('/user/<int:loan_id>/cancel', methods=['POST'])
@login_required
@check_confirm
@detail_required
def cancel_loan(loan_id):
	loan = Loan.query.get_or_404(loan_id)
	current_user.loans.remove(loan)
	flash('Your request for loan has been canceled','info')
	db.session.commit()
	trans = History.query.filter_by(loanee=current_user).first()
	db.session.delete(trans)
	db.session.commit()
	return redirect(url_for('account'))


@app.route('/loans/request_loan', methods=['GET','POST'])
@login_required
@check_confirm
@detail_required
def loan_data():
	if not current_user.details_verified:
		return redirect(url_for('verify_user'))
	loans = Loan.query.all()
	for loan in loans:
		loan.date_of_payment = datetime.now() + timedelta(loan.duration)
	db.session.commit()
	return render_template('loans.html', loans=loans)


@app.route('/loans/user_details', methods=['GET','POST'])
@login_required
@check_confirm
def verify_user():
	form = WorkForm()
	if request.method == 'GET':
		if not current_user.details_verified:
			return render_template('workform.html',form=form)
		flash('Your details have already been stored, go to profile to edit them','info')
		return redirect(url_for('loan_data'))
	else:
		if form.validate_on_submit():
			user = User.query.filter_by(email=current_user.email).first()
			user.occupation = form.occupation.data
			user.phone_number = form.phone_number.data
			user.account_number = form.account_number.data
			user.bvn = form.bvn.data
			user.bank = form.bank.data
			user.address = form.address.data
			user.next_name = form.next_of_kin.data
			user.next_address = form.next_address.data
			user.reasons = form.reasons.data
			user.details_verified = True
			db.session.commit()
			flash('Your details have been stored successfully','success')
			return redirect(url_for('loan_data'))
		return render_template('workform.html',form=form)


@app.route('/user/profile', methods=['GET','POST'])
@login_required
@check_confirm
def profile():
	form = EditProfileForm()
	if form.validate_on_submit():
		if form.picture.data:
			picture_file = save_picture(form.picture.data)
			current_user.image_file = picture_file
		current_user.username = form.username.data
		if current_user.email != form.email.data:
			current_user.confirmed = False
			current_user.email = form.email.data
		db.session.commit()
		flash('Account Updated Successfully','success')
		return redirect(url_for('account'))
	elif request.method == 'GET':
		form.username.data = current_user.username
		form.email.data = current_user.email
		image_file = url_for('static',filename=current_user.image_file)
	return render_template('profile.html',image_file=image_file, form=form)

@app.route('/user/<int:loan_id>')
@login_required
@check_confirm
@detail_required
def Get_loan(loan_id):
	loan = Loan.query.get_or_404(loan_id)
	if not current_user.approved or current_user.payment_index == 0:
		if loan.amount != 1000:
			flash('Your payment index is too low for this loan','warning')
			return redirect(url_for('loan_data'))
		else:
			new_user = User.query.filter_by(email=current_user.email).first()
			if new_user.loans.all() != []:
				flash('You have an outstanding loan','warning')
				return redirect(url_for('account'))
			loan.users.append(new_user)
			db.session.add(loan)
			db.session.commit()
			recpt = loan.amount * -1
			trans = History(loan=loan.amount,receipt=recpt, loanee=current_user)
			db.session.add(trans)
			db.session.commit()
			msg = Message('Loan Request', sender=app.config['MAIL_USERNAME'], recipients=['benjikali@protonmail.com'])
			msg.body = f'''
			Dear Admin:
				A user with the following details has requested a loan;
				Occupation: {current_user.occupation}
				Phone number: {current_user.phone_number}
				Account_number: {current_user.account_number}
				Bvn: {current_user.bvn}
				Bank: {current_user.bank}
				Next of kin: {current_user.next_name}
				Reason for the loan: {current_user.reasons}

				To approve the loan click on the link below
				{url_for('decide_loan',id=current_user.id, _external=True)}
			'''
			send_email(msg)
			return redirect(url_for('account'))
	else:
		x = current_user.payment_index
		if 0 < x <= 0.2:
			if loan.amount <= 3000:
				new_user = User.query.filter_by(email=current_user.email).first()
				if new_user.loans.all() != []:
					flash('You have an outstanding loan','warning')
					return redirect(url_for('account'))
				loan.users.append(new_user)
				db.session.add(loan)
				db.session.commit()
				return redirect(url_for('account'))
			else:
				flash('Your payment index is too low for this loan','warning')
				return redirect(url_for('loan_data'))

		if 0.2 < x <= 0.4:
			if loan.amount <= 100000:
				new_user = User.query.filter_by(email=current_user.email).first()
				if new_user.loans.all() != []:
					flash('You have an outstanding loan','warning')
					return redirect(url_for('account'))
				loan.users.append(new_user)
				db.session.add(loan)
				db.session.commit()
				return redirect(url_for('account'))
			else:
				flash('Your payment index is too low for this loan','warning')
				return redirect(url_for('loan_data'))
		if 0.4 < x <= 0.6:
			if loan.amount <= 25000:
				new_user = User.query.filter_by(email=current_user.email).first()
				if new_user.loans.all() != []:
					flash('You have an outstanding loan','warning')
					return redirect(url_for('account'))
				loan.users.append(new_user)
				db.session.add(loan)
				db.session.commit()
				return redirect(url_for('account'))
			else:
				flash('Your payment index is too low for this loan','warning')
				return redirect(url_for('loan_data'))
		if 0.6 < x <= 0.8:
			if loan.amount <= 50000:
				new_user = User.query.filter_by(email=current_user.email).first()
				if new_user.loans.all() != []:
					flash('You have an outstanding loan','warning')
					return redirect(url_for('account'))
				loan.users.append(new_user)
				db.session.add(loan)
				db.session.commit()
				return redirect(url_for('account'))
			else:
				flash('Your payment index is too low for this loan','warning')
				return redirect(url_for('loan_data'))
		if 0.8 < x <= 1:
			if loan.amount <= 100000:
				new_user = User.query.filter_by(email=current_user.email).first()
				if new_user.loans.all() != []:
					flash('You have an outstanding loan','warning')
					return redirect(url_for('account'))
				loan.users.append(new_user)
				db.session.add(loan)
				db.session.commit()
				return redirect(url_for('account'))
			else:
				flash('Your payment index is too low for this loan','warning')
				return redirect(url_for('loan_data'))



@app.route('/loan/make_choices/<int:id>')
#@login_required
def decide_loan(id):
	return render_template('decide_loan.html', user_id=id)



@app.route('/loan/please_approve_my_loan/<int:id>')
@login_required
def approve_loan(id):
	print(type(current_user.username))
	if current_user.username != 'admin':
		abort(403)
	user = User.query.get_or_404(id)
	if user.payment_index != 0 and user.approved:
		flash('This loan has longed been approved','info')
		return redirect(url_for('home'))
	elif not user.approved:
		loan = Loan.query.get_or_404(1)
		if loan in user.loans.all():
			user.approved = True
			db.session.commit()
			flash('Loan successfully approved','success')
			return redirect(url_for('home'))
		else:
			flash('Loan request has been cancelled by user')
			return redirect(url_for('home'))
@app.route('/loan/disapprove_loan/<int:id>')
@login_required
def disapprove_loan(id):
	if current_user.username != 'admin':
		abort(403)
	user = User.query.get_or_404(id)
	loan = Loan.query.get_or_404(1)
	if loan in user.loans.all():
		user.loans.remove(loan)
		trans = History.query.filter_by(loanee=user).first()
		db.session.delete(trans)
		db.session.commit()
		flash('Loan was not approved','danger')
	else:
		flash('Loan request was cancelled','info')
	return redirect(url_for('home'))


@app.route('/user/payloan/<int:id>')
@login_required
@check_confirm
@detail_required
def payloan(id):
	loan = Loan.query.get(id)
	if not loan in current_user.loans.all():
		abort(403)
	total = ceil(float(f"{(loan.amount + loan.interest)/385:,.2f}"))
	total2 = total*100
	return render_template('checkout.html',loan=loan, total1=total,total2=total2)

@app.route('/create-checkout-session/<int:id>', methods=['POST'])
def checkout(id):
	loan = Loan.query.get(id)
	try:
		customer = stripe.Customer.create(
		    email=request.form['stripeEmail'],
		    source=request.form['stripeToken']
		)

		charge = stripe.Charge.create(
		    amount=ceil(float(f"{(loan.amount + loan.interest)/385:,.2f}"))*100,
		    currency='usd',
		    customer=customer.id,
		    description='A payment for loan'
		)
		user = (current_user.historys)[-1]
		receipt = user.receipt + loan.amount
		trans = History(payment=loan.amount,receipt=receipt, loanee=current_user)
		db.session.add(trans)
		current_user.loans.remove(loan)
		db.session.commit()
	except Exception as e:
		print(e)
		abort(404)

	flash('Transaction successful','success')
	return redirect(url_for('home'))


@app.route('/user/transaction_history')
@login_required
@detail_required
def view_trans():
	data = current_user.historys
	return render_template('receipt.html',data=data,func=abs)



@app.route('/reset_password', methods=['GET','POST'])
@check_confirm
def reset_request():
	if current_user.is_authenticated:
		return redirect(url_for('index'))
	form = RequestResetForm()
	if form.validate_on_submit():
		user = User.query.filter_by(email=form.email.data).first()
		token = user.get_reset_token()
		msg = Message('Password Reset', sender=app.config['MAIL_USERNAME'], recipients=[user.email])
		msg.body = f'''
				To reset your password, follow the link:
		{url_for('reset_password', token=token, _external=True)}
		link is valid for 30 minutes

		If you didn't make this request, kindly ignore
		'''
		send_email(msg)
		flash('Password reset email has been sent to your email','info')
		return redirect('login')
	return render_template('reset_request.html', title='Reset Request', form=form)


@app.route('/reset_password/<token>', methods=['GET','POST'])
def reset_password(token):
	if current_user.is_authenticated:
		return redirect(url_for('home'))
	user = User.verify_reset_token(token)
	if user is None:
		flash('Token is invalid or expired','warning')
		return redirect(url_for('reset_request'))
	form = ResetPasswordForm()
	if form.validate_on_submit():
		hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
		user.password = hashed_password
		db.session.commit()
		flash(f"Password reset successful!", 'success')
		return redirect(url_for('login'))
	return render_template('reset_password.html', title='Reset Request', form=form)




@app.errorhandler(404)
def page_not_found(e):
	return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
	return render_template('500.html'), 500

@app.errorhandler(403)
def forbidden(e):
	return render_template('403.html'), 403


class MyView(ModelView):
	column_exclude_list = ['password','occupation','account_number','bvn','bank','address','next_name','next_address','reasons']

class UserView(MyView):
	def is_accessible(self):
		if current_user.is_anonymous:
			abort(403)
		elif current_user.username != 'admin':
			abort(403)
		else:
			return True

'''class TransView(BaseView):
	@expose('/')
	def trans(self):
		users = User.query.all()
		return self.render('admin/trans.html', users=users)'''


admin.add_view(UserView(User, db.session))
admin.add_view(UserView(Loan, db.session))
admin.add_view(UserView(History, db.session))
