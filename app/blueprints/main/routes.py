from flask import render_template
from app.blueprints.main import bp

@bp.route('/')
def index():
    return render_template('main/index.html', title='Home')

@bp.route('/contact.html')
def contact():
    return render_template('main/contact.html', title='Contact')

@bp.route('/about.html')
def about():
    return render_template('main/about.html', title='About')

@bp.route('/login.html')
def login():
    return render_template('main/login.html', show_navbar=False)

