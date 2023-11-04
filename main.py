import json

from flask import Flask, render_template, url_for, request, redirect, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import stripe


stripe.api_key = os.environ.get("API_KEY")
db = SQLAlchemy()
app = Flask(__name__)
app.config["SECRET_KEY"] = "SECRET_KEY"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///onlineshop.db"
db.init_app(app)
year = datetime.now().year

login_manager = LoginManager()
login_manager.init_app(app)

YOUR_DOMAIN = "http://127.0.0.1:4242"


@login_manager.user_loader
def load_user(user_id):
    return db.session.execute(db.select(User).filter_by(id=int(user_id))).scalar()


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))
    items = relationship("Item", back_populates="user")


class Item(db.Model):
    __tablename__ = "items"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    user = relationship("User", back_populates="items")
    item = db.Column(db.String(200))
    price = db.Column(db.Integer)
    qty = db.Column(db.Integer)


def get_path():
    return request.full_path


@app.route("/")
def home():
    return render_template("index.html", year=year, current_user=current_user)


@app.route("/product")
def product():
    return render_template("product.html", year=year, current_user=current_user)


@app.route("/categories")
def categories():
    return render_template("categories.html", year=year, current_user=current_user)


@app.route("/add_to_cart", methods=["GET", "POST"])
def add_to_cart():
    if request.method == "POST":

        name = request.form.get("product-name")
        price = int(request.form.get("price"))
        qty = request.form.get("qty")
        new_item = Item(item=name, price=price, qty=qty)
        db.session.add(new_item)
        db.session.commit()
        if current_user.is_authenticated:
            new_item.user_id = current_user.id
            db.session.commit()
            return redirect(url_for("cart"))
        return redirect(url_for("login", item_id=new_item.id))


@app.route("/login", methods=["GET", "POST"])
def login():
    item_id = request.args.get("item_id")

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
            item_id = request.form.get("item_id")
            login_user(user)

            return redirect(url_for("add", item_id=item_id))

    return render_template("login.html", year=year, item_id=item_id, current_user=current_user)


@app.route("/register", methods=["GET", "POST"])
def register():
    item_id = request.args.get("item_id")
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
        item_id = request.form.get("item_id")

        return redirect(url_for("add", item_id=item_id))

    return render_template("register.html", year=year, current_user=current_user, item_id=item_id)


@app.route("/add_after_log_or_reg", methods=["GET"])
@login_required
def add():
    item_id = request.args.get("item_id")

    try:
        item_to_add = db.get_or_404(Item, item_id)
        item_to_add.user_id = current_user.id
        db.session.commit()
        return redirect(url_for("cart"))
    except:
        pass
        return redirect(url_for("home"))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))


@app.route("/cart", methods=["GET", "POST"])
def cart():
    if current_user.is_authenticated:
        user = db.session.execute(db.select(User).filter_by(id=int(current_user.id))).scalar()
        items = user.items
        total_price = 0
        for item in items:
            total_price += (item.price * item.qty)

        return render_template("cart.html", year=year, current_user=current_user,
                               items=items, total=total_price, cart_length=len(items))
    return render_template("login.html", year=year)


@app.route("/d_qty")
def d_qty():
    item_id = request.args.get("item_id")
    item = db.get_or_404(Item, item_id)
    item.qty = item.qty - 1
    db.session.commit()
    return redirect(url_for("cart"))


@app.route("/i_qty")
def i_qty():
    item_id = request.args.get("item_id")
    item = db.get_or_404(Item, item_id)
    item.qty = item.qty + 1
    db.session.commit()
    return redirect(url_for("cart"))


@app.route("/delete")
def delete():
    item_id = request.args.get("item_id")
    item = db.get_or_404(Item, item_id)
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for("cart"))


@app.route("/success")
def success():
    return render_template("success.html", year=year, current_user=current_user)


@app.route("/cancel")
def cancel():
    return render_template("cancel.html", year=year, current_user=current_user)


@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    total = int(request.form.get("total"))

    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": "Product"},
                        "unit_amount": total * 100,
                        "tax_behavior": "exclusive",
                    },
                    "quantity": 1,
                },
            ],
            mode='payment',
            success_url=YOUR_DOMAIN + '/success',
            cancel_url=YOUR_DOMAIN + '/cancel',
        )
    except Exception as e:
        return str(e)

    return redirect(checkout_session.url, code=303)


if __name__ == "__main__":
    with app.app_context():
        # db.drop_all()
        db.create_all()
    app.run(debug=True, port=4242)