import os
from datetime import date
from flask import Flask, redirect, url_for, session, render_template, request
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.getenv("SECRET_KEY", "chave-dev")

# Config OAuth SUAP
oauth = OAuth(app)
suap = oauth.register(
    name="suap",
    client_id=os.getenv("SUAP_CLIENT_ID"),
    client_secret=os.getenv("SUAP_CLIENT_SECRET"),
    access_token_url="https://suap.ifrn.edu.br/o/token/",
    authorize_url="https://suap.ifrn.edu.br/o/authorize/",
    api_base_url="https://suap.ifrn.edu.br/",
    client_kwargs={"scope": "identificacao email"},
)

# --- Helpers ---
def is_logged_in():
    return "token" in session

def fetch_user():
    """Busca dados do usuário logado"""
    if not is_logged_in():
        return None
    # ENDPOINT CORRETO: /api/eu/
    resp = suap.get("api/eu/", token=session["token"])
    return resp.json() if resp.ok else None

@app.context_processor
def inject_user():
    """Disponibiliza user em todos os templates"""
    return dict(user=fetch_user())

# --- Rotas ---
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login")
def login():
    redirect_uri = url_for("authorize", _external=True)
    return suap.authorize_redirect(redirect_uri)

@app.route("/login/authorized")
def authorize():
    token = suap.authorize_access_token()
    session["token"] = token
    return redirect(url_for("perfil"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/perfil")
def perfil():
    if not is_logged_in():
        return redirect(url_for("login"))
    
    user_data = fetch_user()
    student_data = fetch_student_data()
    
    return render_template("perfil.html", user_data=user_data, student_data=student_data)

@app.route("/boletim")
def boletim():
    if not is_logged_in():
        return redirect(url_for("login"))

    # Buscar períodos disponíveis
    periods = fetch_periods()
    
    # Parâmetros da URL ou valores padrão
    ano = request.args.get("ano", type=int)
    periodo = request.args.get("periodo", type=int)
    
    # Se não foram fornecidos, usar o primeiro período disponível
    if not ano or not periodo:
        if periods:
            latest_period = periods[0]  # Assuming the first is the latest
            ano = latest_period.get("ano_letivo", date.today().year)
            periodo = latest_period.get("periodo_letivo", 1)
        else:
            ano = date.today().year
            periodo = 1 if date.today().month <= 6 else 2

    # Buscar boletim
    boletim_data = []
    if ano and periodo:
        resp = suap.get(f"api/ensino/meu-boletim/{ano}/{periodo}/", token=session["token"])
        if resp.ok:
            boletim_data = resp.json().get("results", [])
    
    return render_template("boletim.html", 
                         boletim=boletim_data, 
                         ano=ano, 
                         periodo=periodo,
                         periods=periods)

if __name__ == "__main__":
    app.run(debug=True, port=8888)