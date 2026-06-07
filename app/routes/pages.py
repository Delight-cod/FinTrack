from flask import Blueprint, redirect, url_for, render_template, session

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
def index():
    return redirect(url_for("pages.dashboard") if "user" in session else url_for("pages.signup_page"))


@pages_bp.route("/signup")
def signup_page():
    return render_template("signup.html")


@pages_bp.route("/login")
def login_page():
    if "user" in session:
        return redirect(url_for("pages.dashboard"))
    return render_template("login.html")


@pages_bp.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("pages.login_page"))
    return render_template("dashboard.html")


@pages_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("pages.login_page"))
