from flask import Flask, render_template, redirect, request, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, TextAreaField, FileField
from wtforms.validators import DataRequired, Email, Length
from flask_wtf.csrf import CSRFProtect
import os
from sqlalchemy.exc import IntegrityError
from flask_login import current_user
from flask import make_response
from xhtml2pdf import pisa
import io
import secrets


# Initialize Flask app and configurations
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///maaz_portfolio.db'
app.config['SECRET_KEY'] = secrets.token_hex(16)
app.config['UPLOAD_FOLDER'] = 'static/images/'

# Initialize extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
csrf = CSRFProtect(app)

# Model for the user details
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    bio = db.Column(db.Text, nullable=False)
    skills = db.Column(db.String(300), nullable=False)
    linkedin = db.Column(db.String(200))
    github = db.Column(db.String(200))
    profile_picture = db.Column(db.String(100), nullable=False)

# Form for collecting user details
class PortfolioForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=100)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=100)])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[DataRequired(), Length(max=15)])
    bio = TextAreaField('Short Bio', validators=[DataRequired()])
    skills = StringField('Skills', validators=[DataRequired()])
    linkedin = StringField('LinkedIn Profile')
    github = StringField('GitHub Profile')
    profile_picture = FileField('Profile Picture', validators=[DataRequired()])

# Routes
@app.route('/')
def home():
    return render_template('home.html', user=current_user)

@app.route('/create-portfolio', methods=['GET', 'POST'])
def create_portfolio():
    form = PortfolioForm()
    if form.validate_on_submit():
        # Check if the email already exists
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('Email already exists. Please use a different email.', 'danger')
            return redirect(url_for('create_portfolio'))

        # Save the profile picture
        profile_picture = form.profile_picture.data
        picture_filename = os.path.join(app.config['UPLOAD_FOLDER'], profile_picture.filename)
        profile_picture.save(picture_filename)

        # Create a new user
        user = User(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            phone=form.phone.data,
            bio=form.bio.data,
            skills=form.skills.data,
            linkedin=form.linkedin.data,
            github=form.github.data,
            profile_picture=profile_picture.filename
        )

        # Insert new user into the database
        try:
            db.session.add(user)
            db.session.commit()
            flash('Portfolio created successfully!', 'success')
            return redirect(url_for('home'))
        except IntegrityError:
            db.session.rollback()
            flash('An error occurred. Please try again.', 'danger')

    return render_template('form.html', form=form, user=current_user)

# @app.route('/portfolio/<int:user_id>')
# def view_portfolio(user_id):
#     user = User.query.get_or_404(user_id)
#     return render_template('portfolio.html', user=user)

@app.route('/view_portfolio')
def view_portfolio():
    portfolios = User.query.all()  # Fetch all users from the database (assuming each user represents a portfolio)
  # Fetch all portfolios from the database
    return render_template('view_portfolio.html', portfolios=portfolios)

@app.route('/portfolio/<int:portfolio_id>')
def portfolio_detail(portfolio_id):
    portfolio = User.query.get_or_404(portfolio_id)  # Fetch the specific portfolio by ID
    return render_template('portfolio_detail.html', user=portfolio)  # Passing user data

def render_pdf(template_name, **kwargs):
    # Convert HTML template into PDF
    html = render_template(template_name, **kwargs)
    pdf = io.BytesIO()
    pisa_status = pisa.CreatePDF(io.StringIO(html), dest=pdf)
    if pisa_status.err:
        return None
    pdf.seek(0)
    return pdf

@app.route('/portfolio/<int:portfolio_id>/download_pdf')
def download_pdf(portfolio_id):
    # Fetch portfolio details by ID
    portfolio = User.query.get_or_404(portfolio_id)
    
    # Generate PDF from the portfolio template
    pdf = render_pdf('portfolio_detail.html', portfolio=portfolio)
    
    if pdf:
        # Return the PDF as a downloadable file
        response = make_response(pdf.read())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'attachment; filename=portfolio.pdf'
        return response
    else:
        flash('PDF generation failed.', 'danger')
        return redirect(url_for('view_portfolio'))

if __name__ == '__main__':
    app.run(debug=True)
