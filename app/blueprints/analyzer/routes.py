from flask import render_template
from app.blueprints.analyzer import bp

@bp.route('/analyze')
def analyze():
    return render_template('analyzer/analyze.html', title='Analyze')
