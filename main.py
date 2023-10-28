from flask import Flask, render_template, url_for, request, redirect, flash, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash

from datetime import datetime


db = SQLAlchemy()
app = Flask(__name__)
app.config["SECRET_KEY"] = "SECRET_KEY"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///onlineshop.db"
db.init_app(app)
year = datetime.now().year

login_manager = LoginManager()

login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.session.execute(db.select(User).filter_by(id=int(user_id))).scalar()

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))

    # carts = relationship("Cart", back_populates="user")
    items = relationship("Item", back_populates="user")


# class Cart(db.Model):
#     __tablename__ = "carts"
#     id = db.Column(db.Integer, primary_key=True)
#     user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
#     user = relationship("User", back_populates="carts")
#     items = relationship("Item", back_populates="parent_cart")


class Item(db.Model):
    __tablename__ = "items"
    id = db.Column(db.Integer, primary_key=True)
    # cart_id = db.Column(db.Integer, db.ForeignKey("carts.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # parent_cart = relationship("Cart", back_populates="items")
    user = relationship("User", back_populates="items")
    item = db.Column(db.String(200))
    qty = db.Column(db.Integer)




@app.route("/")
def home():
    return render_template("index.html", year=year)

@app.route("/product")
def product():
    return render_template("product.html", year=year)

@app.route("/categories")
def categories():
    return render_template("categories.html", year=year)



@app.route("/add_to_cart", methods=["GET", "POST"])
def add_to_cart():
    if request.method == "POST":
        qty = request.form.get("qty")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")

        user = db.session.execute(db.select(User).filter_by(email=email)).scalar()

        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for("login"))

        elif not check_password_hash(user.password, password):
            flash("Password incorrect, please try again.")
            return redirect(url_for("login"))

        else:
            login_user(user)
            # cart_id = request.form.get("list_id")
            # if list_id:
            #     list_to_add = db.get_or_404(TodoList, list_id)
            #     list_to_add.user = current_user
            #     for todo in list_to_add.tasks:
            #         todo.user_id = current_user.id
            #     db.session.commit()

            return redirect(url_for("cart"))
    return render_template("login.html", year=year)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        if db.session.execute(db.select(User).filter_by(email=request.form.get("email"))).scalar():
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for("login"))
        hash_and_salted_password = generate_password_hash(
            request.form.get("password"),
            method="pbkdf2:sha256",
            salt_length=8
        )
        user = User()
        user.email = request.form.get("email")
        user.name = request.form.get("name")
        user.password = hash_and_salted_password
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for("cart"))
    return render_template("register.html", year=year)


@app.route("/cart", methods=["GET", "POST"])
@login_required
def cart():
    return render_template("cart.html", year=year)


if __name__ == "__main__":
    with app.app_context():
        # db.drop_all()
        db.create_all()
    app.run(debug=True)