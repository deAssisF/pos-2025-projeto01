import os
from datetime import date
from flask import Flask, redirect, url_for, session, render_template, request, jsonify
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
import requests

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

def make_suap_request(endpoint):
    """Faz requisições autenticadas para a API do SUAP"""
    if not is_logged_in():
        return None
        
    headers = {
        "Authorization": f"Bearer {session['token']['access_token']}",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(f"https://suap.ifrn.edu.br/api/{endpoint}", headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Erro {response.status_code} na requisição para {endpoint}")
            return None
    except Exception as e:
        print(f"Erro na requisição para {endpoint}: {e}")
        return None

def fetch_user():
    """Busca dados básicos do usuário logado"""
    user_data = make_suap_request("eu/")
    if user_data:
        # Adiciona campos que seus templates esperam
        user_data['matricula'] = user_data.get('identificacao', '')
        user_data['url_foto'] = user_data.get('foto', '')
        user_data['nome_completo'] = user_data.get('nome_registro', '')
    return user_data

def fetch_student_data():
    """Busca dados acadêmicos do estudante"""
    return make_suap_request("ensino/meus-dados-aluno/")

def fetch_periods():
    """Busca períodos letivos disponíveis"""
    periods_data = make_suap_request("ensino/meus-periodos-letivos/")
    if periods_data and 'results' in periods_data:
        return periods_data['results']
    return []

def fetch_boletim(ano, periodo):
    """Busca boletim para um ano e período específico"""
    boletim_data = make_suap_request(f"ensino/meu-boletim/{ano}/{periodo}/")
    if boletim_data and 'results' in boletim_data:
        return boletim_data['results']
    return []

@app.context_processor
def inject_user():
    """Disponibiliza user em todos os templates"""
    user = fetch_user() if is_logged_in() else None
    return dict(user=user)

# --- Rotas ---
@app.route("/")
def index():
    # Se o usuário estiver logado, redireciona para o perfil
    if is_logged_in():
        return redirect(url_for('perfil'))
    return render_template("index.html")

@app.route("/login")
def login():
    redirect_uri = url_for("authorize", _external=True)
    return suap.authorize_redirect(redirect_uri)

@app.route("/login/authorized")
def authorize():
    try:
        token = suap.authorize_access_token()
        session["token"] = token
        return redirect(url_for("perfil"))
    except Exception as e:
        print(f"Erro na autenticação: {e}")
        return redirect(url_for("index"))

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
    
    # Obter ano e período da query string
    ano = request.args.get("ano", type=int)
    periodo = request.args.get("periodo", type=int)
    
    # Se não foram fornecidos, tentar usar o período mais recente
    if not ano or not periodo:
        if periods:
            # Ordenar períodos: primeiro por ano decrescente, depois por período decrescente
            sorted_periods = sorted(periods, key=lambda x: (x['ano_letivo'], x['periodo_letivo']), reverse=True)
            ano = sorted_periods[0]['ano_letivo']
            periodo = sorted_periods[0]['periodo_letivo']
        else:
            # Se não há períodos, usar o ano atual e período 1 ou 2 baseado no mês
            current_date = date.today()
            ano = current_date.year
            periodo = 1 if current_date.month <= 6 else 2

    # Buscar boletim para o ano e período
    boletim_data = fetch_boletim(ano, periodo)
    
    return render_template("boletim.html", 
                         boletim=boletim_data, 
                         ano=ano, 
                         periodo=periodo,
                         periods=periods)

if __name__ == "__main__":
    app.run(debug=True, port=8888)