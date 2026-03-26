import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_db, init_db

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ------------------------------------------------------------------ #
# Database Helpers                                                   #
# ------------------------------------------------------------------ #

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()

@app.cli.command("init-db")
def init_db_command():
    """Clear existing data and create new tables."""
    init_db()
    print("Database initialized.")

# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")

@app.route("/terms")
def terms():
    return render_template("terms.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        db = get_db()
        
        try:
            db.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (name, email, generate_password_hash(password))
            )
            db.commit()
            flash("Account created! Please log in.", "success")
            return redirect(url_for("login"))
        except db.IntegrityError:
            flash("Email already exists.", "danger")
            
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        db = get_db()
        
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        
        if user and check_password_hash(user['password_hash'], password):
            session.clear()
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("dashboard"))
        
        flash("Invalid credentials.", "danger")
        
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Successfully logged out.", "info")
    return redirect(url_for("landing"))

@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for("login"))
    
    db = get_db()
    
    # 1. Fetch user budget
    user = db.execute("SELECT monthly_budget FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    monthly_budget = user['monthly_budget'] if user else 10000.0

    # 2. Fetch all expenses for the list with optional search/filter
    search_query = request.args.get('q', '')
    category_filter = request.args.get('category', '')
    
    query = "SELECT * FROM expenses WHERE user_id = ?"
    params = [session['user_id']]
    
    if search_query:
        query += " AND (description LIKE ? OR category LIKE ?)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])
    
    if category_filter:
        query += " AND category = ?"
        params.append(category_filter)
        
    query += " ORDER BY date DESC"
    
    all_expenses = db.execute(query, params).fetchall()
    
    total_spent = sum(e['amount'] for e in all_expenses)

    # 3. Calculate current month's spending for the budget progress bar
    from datetime import datetime
    current_month_str = datetime.now().strftime("%Y-%m")
    
    current_month_spent = db.execute(
        "SELECT SUM(amount) as total FROM expenses WHERE user_id = ? AND date LIKE ?",
        (session['user_id'], f"{current_month_str}%")
    ).fetchone()['total'] or 0.0

    # 4. Calculate category-wise totals for the chart
    categories_data = db.execute(
        "SELECT category, SUM(amount) as total FROM expenses WHERE user_id = ? GROUP BY category",
        (session['user_id'],)
    ).fetchall()
    
    # Format categories for Chart.js
    chart_labels = [c['category'] for c in categories_data]
    chart_values = [c['total'] for c in categories_data]
    
    return render_template(
        "dashboard.html", 
        expenses=all_expenses, 
        total_spent=total_spent,
        current_month_spent=current_month_spent,
        monthly_budget=monthly_budget,
        chart_labels=chart_labels,
        chart_values=chart_values
    )

@app.route("/budget/update", methods=["POST"])
def update_budget():
    if 'user_id' not in session:
        return redirect(url_for("login"))
        
    new_budget = request.form.get("budget")
    db = get_db()
    db.execute("UPDATE users SET monthly_budget = ? WHERE id = ?", (new_budget, session['user_id']))
    db.commit()
    flash("Budget updated successfully!", "success")
    return redirect(url_for("dashboard"))

@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if 'user_id' not in session:
        return redirect(url_for("login"))
    
    if request.method == "POST":
        amount = request.form.get("amount")
        category = request.form.get("category")
        description = request.form.get("description")
        date = request.form.get("date")
        
        db = get_db()
        db.execute(
            "INSERT INTO expenses (user_id, amount, category, description, date) VALUES (?, ?, ?, ?, ?)",
            (session['user_id'], amount, category, description, date)
        )
        db.commit()
        flash("Expense added!", "success")
        return redirect(url_for("dashboard"))
        
    return render_template("add_expense.html")

@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    if 'user_id' not in session:
        return redirect(url_for("login"))
        
    db = get_db()
    expense = db.execute("SELECT * FROM expenses WHERE id = ? AND user_id = ?", (id, session['user_id'])).fetchone()
    
    if not expense:
        flash("Expense not found.", "danger")
        return redirect(url_for("dashboard"))
        
    if request.method == "POST":
        amount = request.form.get("amount")
        category = request.form.get("category")
        description = request.form.get("description")
        date = request.form.get("date")
        
        db.execute(
            "UPDATE expenses SET amount = ?, category = ?, description = ?, date = ? WHERE id = ?",
            (amount, category, description, date, id)
        )
        db.commit()
        flash("Expense updated!", "success")
        return redirect(url_for("dashboard"))
        
    return render_template("edit_expense.html", expense=expense)

@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    if 'user_id' not in session:
        return redirect(url_for("login"))
        
    db = get_db()
    db.execute("DELETE FROM expenses WHERE id = ? AND user_id = ?", (id, session['user_id']))
    db.commit()
    flash("Expense deleted.", "info")
    return redirect(url_for("dashboard"))

@app.route("/profile")
def profile():
    if 'user_id' not in session:
        return redirect(url_for("login"))
    return render_template("profile.html")


if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(debug=True, port=5001)
