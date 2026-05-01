from flask import Flask, render_template, request, redirect, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

from collections import defaultdict

app = Flask(__name__)
app.config['SECRET_KEY'] = "secret123"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

CODE_CLUB = "COACH2026"
PRIX_KM = 0.63

# ================= MODELS =================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))
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

@app.route("/", methods=["GET", "POST"])
@login_required
def dashboard():
    if request.method == "POST":
        date = request.form["date"]
        lieu = request.form["lieu"]
        km = float(request.form["km"])

        montant = km * PRIX_KM

        frais = Frais(
            date=date,
            lieu=lieu,
            km=km,
            montant=montant,
            user_id=current_user.id
        )

        db.session.add(frais)
        db.session.commit()

    frais = Frais.query.filter_by(user_id=current_user.id).all()

    frais_par_mois = defaultdict(list)
    for f in frais:
        mois = f.date[:7]
        frais_par_mois[mois].append(f)

    return render_template("dashboard.html", frais_par_mois=frais_par_mois)

# ================= REGISTER =================

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])
        code = request.form["code"]

        if code != CODE_CLUB:
            return "Code club incorrect"

        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()

        return redirect("/login")

    return render_template("register.html")

# ================= LOGIN =================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()

        if user and check_password_hash(user.password, request.form["password"]):
            login_user(user)
            return redirect("/")

    return render_template("login.html")

# ================= LOGOUT =================

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")

# ================= PDF =================

@app.route("/pdf/<mois>")
@login_required
def pdf(mois):
    frais = Frais.query.filter_by(user_id=current_user.id).all()

    data = [["Date", "Lieu", "Km", "Montant €"]]
    total = 0

    for f in frais:
        if f.date.startswith(mois):
            data.append([f.date, f.lieu, f.km, f"{f.montant:.2f}"])
            total += f.montant

    doc = SimpleDocTemplate("frais.pdf", pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # LOGO (facultatif mais conseillé)
    try:
        elements.append(Image("static/logo.png", width=120, height=60))
    except:
        pass

    elements.append(Spacer(1, 20))

    elements.append(Paragraph("NOTE DE FRAIS", styles["Title"]))
    elements.append(Paragraph(f"Coach : {current_user.username}", styles["Heading2"]))
    elements.append(Paragraph(f"Mois : {mois}", styles["Normal"]))

    elements.append(Spacer(1, 20))

    table = Table(data)
    table.setStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.black),
        ("TEXTCOLOR", (0,0), (-1,0), colors.yellow),
        ("GRID", (0,0), (-1,-1), 1, colors.black),
    ])

    elements.append(table)

    elements.append(Spacer(1, 20))
    elements.append(Paragraph(f"TOTAL : {total:.2f} €", styles["Heading1"]))

    doc.build(elements)

    return send_file("frais.pdf", as_attachment=True)

# ================= RUN =================

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)