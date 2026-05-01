from flask import Flask, render_template, request, redirect, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

from collections import defaultdict

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"

PRIX_KM = 0.63

# ================= MODELS =================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))

class Frais(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(50))
    lieu = db.Column(db.String(100))
    km = db.Column(db.Float)
    montant = db.Column(db.Float)
    user_id = db.Column(db.Integer)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ================= ROUTES =================

@app.route("/")
def home():
    return redirect("/login")

# ---------- REGISTER ----------
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])

        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()

        return redirect("/login")

    return render_template("register.html")

# ---------- LOGIN ----------
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()

        if user and check_password_hash(user.password, request.form["password"]):
            login_user(user)
            return redirect("/dashboard")

    return render_template("login.html")

# ---------- DASHBOARD ----------
@app.route("/dashboard", methods=["GET","POST"])
@login_required
def dashboard():
    if request.method == "POST":
        km = float(request.form["km"])
        montant = km * PRIX_KM

        f = Frais(
            date=request.form["date"],
            lieu=request.form["lieu"],
            km=km,
            montant=montant,
            user_id=current_user.id
        )

        db.session.add(f)
        db.session.commit()

    frais = Frais.query.filter_by(user_id=current_user.id).all()

    frais_par_mois = defaultdict(list)
    for f in frais:
        mois = f.date[:7]
        frais_par_mois[mois].append(f)

    return render_template("dashboard.html", frais_par_mois=frais_par_mois)

# ---------- PDF ----------
@app.route('/pdf')
@login_required
def generate_pdf():
    filename = "deplacements.pdf"
    c = canvas.Canvas(filename)

    y = 800
    c.setFont("Helvetica-Bold", 16)
    c.drawString(200, y, "JSOG - Rapport de déplacements")
    y -= 40

    c.setFont("Helvetica", 12)

    total_km = 0

    for d in Deplacement.query.all():
        c.drawString(50, y, f"{d.date} | {d.motif} | {d.km} km")
        total_km += d.km
        y -= 20

    y -= 20
    c.drawString(50, y, f"TOTAL KM : {total_km} km")

    c.save()
    return send_file(filename, as_attachment=True)
# ---------- LOGOUT ----------
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")

# ================= RUN =================

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)