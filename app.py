from flask import Flask, render_template, request, redirect, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.config['SECRET_KEY'] = 'jsog_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"

PRIX_KM = 0.63

# ---------------- MODELS ----------------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))

class Deplacement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(50))
    motif = db.Column(db.String(100))
    km = db.Column(db.Float)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------- ROUTES ----------------

@app.route("/")
def home():
    return redirect("/login")

# -------- REGISTER --------
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        user = User(
            username=request.form["username"],
            password=generate_password_hash(request.form["password"])
        )
        db.session.add(user)
        db.session.commit()
        return redirect("/login")
    return render_template("register.html")

# -------- LOGIN --------
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()
        if user and check_password_hash(user.password, request.form["password"]):
            login_user(user)
            return redirect("/dashboard")
    return render_template("login.html")

# -------- DASHBOARD --------
@app.route("/dashboard", methods=["GET","POST"])
@login_required
def dashboard():

    if request.method == "POST":
        km = float(request.form["km"])
        montant = km * PRIX_KM

        d = Deplacement(
            date=request.form["date"],
            motif=request.form["motif"],
            km=km,
            user_id=current_user.id
        )

        db.session.add(d)
        db.session.commit()

    deplacements = Deplacement.query.filter_by(user_id=current_user.id).all()

    return render_template("dashboard.html", deplacements=deplacements)

# -------- PDF --------
@app.route("/pdf")
@login_required
def pdf():
    mois = request.args.get("mois")

    filename = "jsog.pdf"
    c = canvas.Canvas(filename)

    y = 800
    total = 0

    for d in Deplacement.query.filter_by(user_id=current_user.id).all():
        if mois and not d.date.startswith(mois):
            continue

        montant = d.km * PRIX_KM
        total += montant

        c.drawString(50, y, f"{d.date} - {d.motif} - {d.km} km - {montant:.2f}€")
        y -= 20

    c.drawString(50, y-20, f"TOTAL : {total:.2f}€")

    c.save()
    return send_file(filename, as_attachment=True)

# -------- LOGOUT --------
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")

# ---------------- INIT DB ----------------

with app.app_context():
    db.create_all()

# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(debug=True)