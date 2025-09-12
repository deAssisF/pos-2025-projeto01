from flask import Flask, redirect, url_for, session, request, render_template
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
import os

load_dotenv()
app = Flask(__name__)
app.debug = True
app.secret_key = os.getenv('SECRET_KEY', 'dev')
oauth = OAuth(app)

oauth.register(
    name='suap',
    client_id=os.getenv("SUAP_CLIENT_ID"),
    client_secret=os.getenv("SUAP_CLIENT_SECRET"),
    api_base_url='https://suap.ifrn.edu.br/api/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://suap.ifrn.edu.br/o/token/',
    authorize_url='https://suap.ifrn.edu.br/o/authorize/',
    fetch_token=lambda: session.get('suap_token')
)

class User:
    def __init__(self, oauth):
        self.oauth = oauth

    def get_user_data(self):
        return self.oauth.suap.get('rh/meus-dados').json()

    def get_boletim(self, ano_letivo, periodo_letivo):
        return self.oauth.suap.get(f"v2/minhas-informacoes/boletim/{ano_letivo}/{periodo_letivo}/").json()

    def get_periodos(self):
        return self.oauth.suap.get("v2/minhas-informacoes/meus-periodos-letivos/").json()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/user')
def user():
    if 'suap_token' in session:
        suap_user = User(oauth)
        user = suap_user.get_user_data()
        return render_template('perfil.html', user=user)
    else:
        return render_template('index.html')

@app.route("/boletim/", methods=["GET", "POST"])
def boletim():
    if 'suap_token' not in session:
        return redirect(url_for('login'))
    suap_user = User(oauth)
    if request.method == "POST":
        periodo = request.form.get("periodo")
        return redirect(url_for("boletim", periodo=periodo))
    periodo = request.args.get("periodo", "2025.1")
    if '.' not in periodo:
        periodo = "2025.1"
    ano_letivo, periodo_letivo = periodo.split(".")
    user = suap_user.get_user_data()
    boletim = suap_user.get_boletim(ano_letivo, periodo_letivo)
    periodos = suap_user.get_periodos()
    return render_template(
        "boletim.html",
        user=user,
        boletim_data=boletim,
        periodos=periodos,
        selected_periodo=periodo
    )

@app.route('/login')
def login():
    return oauth.suap.authorize_redirect(url_for('auth', _external=True))

@app.route('/logout')
def logout():
    session.pop('suap_token', None)
    return redirect(url_for('index'))

@app.route('/login/authorized')
def auth():
    session['suap_token'] = oauth.suap.authorize_access_token()
    return redirect(url_for('user'))

if __name__ == '__main__':
    app.run(port=5000)