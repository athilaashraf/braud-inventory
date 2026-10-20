from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from models import db, Product, Variant, StockEntry, StockAdjustment, Invoice, InvoiceItem, SIZES
from invoice import build_invoice_pdf
from flask import session
from datetime import datetime, date
from werkzeug.security import check_password_hash
import os
from dotenv import load_dotenv
app = Flask(__name__)
load_dotenv()
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
ADMIN_USER = os.environ["ADMIN_USER"]
ADMIN_HASH = os.environ["ADMIN_HASH"]
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///braud.db"

db.init_app(app)

with app.app_context():
    db.create_all()


@app.route("/")
def home():
    total_pieces = low = out = 0
    for p in Product.query.all():
        total = sum(v.quantity for v in p.variants)
        total_pieces += total
        if total == 0:
            out += 1
        elif total < p.low_stock_limit:
            low += 1

    start_of_day = datetime.combine(date.today(), datetime.min.time())
    todays = [i for i in Invoice.query.filter(Invoice.date >= start_of_day).all()
              if i.status != "Cancelled"]
    sales_today = sum(i.total for i in todays)

    return render_template("home.html",
                           total_pieces=total_pieces, low=low, out=out,
                           sales_today=sales_today, bills_today=len(todays),
                           today=date.today().strftime("%A, %d %B %Y"))

@app.route("/products", methods=["GET", "POST"])
def products():
    if request.method == "POST":
        name = request.form["name"].strip().title()
        try:
            price = float(request.form["price"])
            limit = int(request.form["low_stock_limit"])
        except ValueError:
            flash("Price and warning limit must be numbers.")
            return redirect(url_for("products"))

        if not name or price <= 0 or limit < 0:
            flash("Enter a name, a price above 0, and a valid limit.")
        elif Product.query.filter_by(name=name).first():
            flash(f"'{name}' already exists.")
        else:
            p = Product(name=name, price=price, low_stock_limit=limit)
            db.session.add(p)
            db.session.flush()  # gives p an id before saving
            for s in SIZES:
                db.session.add(Variant(product_id=p.id, size=s, quantity=0))
            db.session.commit()
            flash(f"{name} added.")
        return redirect(url_for("products"))

    all_products = Product.query.order_by(Product.name).all()
    return render_template("products.html", products=all_products)
@app.route("/stock", methods=["GET", "POST"])
def stock():
    if request.method == "POST":
        try:
            product_id = int(request.form["product_id"])
            sets = int(request.form["sets"])
        except ValueError:
            flash("Select a model and enter a whole number of sets.")
            return redirect(url_for("stock"))

        product = db.session.get(Product, product_id)
        if product is None or sets <= 0:
            flash("Select a valid model and enter at least 1 set.")
        else:
            for v in product.variants:
                v.quantity += sets          # one shirt per size in every set
            db.session.add(StockEntry(
                product_id=product.id,
                sets=sets,
                pieces=sets * len(SIZES),
            ))
            db.session.commit()
            flash(f"Added {sets} sets ({sets * len(SIZES)} pieces) of {product.name}: "
                  f"{sets} each of S, M, L, XL.")
        return redirect(url_for("stock"))

    products = Product.query.order_by(Product.name).all()
    entries = StockEntry.query.order_by(StockEntry.date.desc()).limit(10).all()
    return render_template("stock.html", products=products, entries=entries)
@app.route("/dashboard")
def dashboard():
    rows = []
    for p in Product.query.order_by(Product.name).all():
        sizes = {v.size: v.quantity for v in p.variants}
        total = sum(sizes.values())
        if total == 0:
            status = "Out"
        elif total < p.low_stock_limit:
            status = "Low"
        else:
            status = "OK"
        rows.append({
            "name": p.name,
            "sizes": sizes,
            "total": total,
            "limit": p.low_stock_limit,
            "status": status,
        })
    return render_template("dashboard.html", rows=rows, sizes=SIZES)
@app.route("/billing", methods=["GET", "POST"])
def billing():
    if request.method == "POST":
        name = request.form["customer_name"].strip()
        phone = request.form["phone"].strip()

        # 1. read the item rows
        lines = []
        for pid, size, qty in zip(request.form.getlist("product_id"),
                                  request.form.getlist("size"),
                                  request.form.getlist("quantity")):
            if not pid:
                continue                      # skip empty rows
            try:
                lines.append((int(pid), size, int(qty)))
            except ValueError:
                flash("Quantity must be a whole number.")
                return redirect(url_for("billing"))

        if not name or not lines:
            flash("Enter the customer name and at least one item.")
            return redirect(url_for("billing"))
        if any(q <= 0 or s not in SIZES for _, s, q in lines):
            flash("Every quantity must be at least 1.")
            return redirect(url_for("billing"))

        # 2. add up quantities per model+size, then check stock
        needed = {}
        for pid, size, qty in lines:
            needed[(pid, size)] = needed.get((pid, size), 0) + qty

        variants = {}
        for (pid, size), qty in needed.items():
            v = Variant.query.filter_by(product_id=pid, size=size).first()
            if v is None:
                flash("Invalid item selected.")
                return redirect(url_for("billing"))
            if qty > v.quantity:
                flash(f"Not enough stock: only {v.quantity} of {v.product.name} size {size} left.")
                return redirect(url_for("billing"))
            variants[(pid, size)] = v

        # 3. create the invoice (price comes from the database, not the browser)
        invoice = Invoice(customer_name=name, phone=phone)
        db.session.add(invoice)
        db.session.flush()                    # gives the invoice an id
        invoice.invoice_no = f"INV-{invoice.id:04d}"

        total = 0
        for pid, size, qty in lines:
            product = db.session.get(Product, pid)
            db.session.add(InvoiceItem(invoice_id=invoice.id, product_id=pid,
                                       size=size, quantity=qty,
                                       unit_price=product.price))
            total += qty * product.price

        # 4. reduce the stock
                # 4. work out the discount (checked here, not trusted from the browser)
        try:
            dval = float(request.form.get("discount") or 0)
        except ValueError:
            db.session.rollback()
            flash("Discount must be a number.")
            return redirect(url_for("billing"))

        dtype = request.form.get("discount_type", "percent")
        if dval < 0 or (dtype == "percent" and dval > 100):
            db.session.rollback()
            flash("Enter a valid discount.")
            return redirect(url_for("billing"))

        discount = total * dval / 100 if dtype == "percent" else dval
        if discount > total:
            db.session.rollback()
            flash("The discount cannot be more than the bill total.")
            return redirect(url_for("billing"))

        # 5. reduce the stock
        for key, qty in needed.items():
            variants[key].quantity -= qty

        invoice.discount = round(discount, 2)
        invoice.total = round(total - discount, 2)
        db.session.commit()                   # bill + stock change saved together
        flash(f"Bill {invoice.invoice_no} saved. Total: {invoice.total:.2f}")
        return redirect(url_for("invoices"))

    products = Product.query.order_by(Product.name).all()
    catalog = {p.id: {"price": p.price,
                      "stock": {v.size: v.quantity for v in p.variants}}
               for p in products}
    return render_template("billing.html", products=products,
                           catalog=catalog, sizes=SIZES)
@app.route("/invoices")
def invoices():
    all_invoices = Invoice.query.order_by(Invoice.date.desc()).all()
    return render_template("invoices.html", invoices=all_invoices)


@app.route("/invoice/<int:invoice_id>/pdf")
def invoice_pdf(invoice_id):
    invoice = db.get_or_404(Invoice, invoice_id)
    pdf = build_invoice_pdf(invoice)
    return send_file(pdf, mimetype="application/pdf",
                     
                     download_name=f"{invoice.invoice_no}.pdf")
@app.before_request
def require_login():
    # runs before every page; only the login page and static files are open
    if request.endpoint in ("login", "static"):
        return
    if not session.get("logged_in"):
        return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        if username == ADMIN_USER and check_password_hash(ADMIN_HASH, password):
            session.clear()
            session["logged_in"] = True
            return redirect(url_for("home"))
        flash("Wrong username or password.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))
@app.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
def edit_product(product_id):
    product = db.get_or_404(Product, product_id)

    if request.method == "POST":
        try:
            price = float(request.form["price"])
            limit = int(request.form["low_stock_limit"])
        except ValueError:
            flash("Price and warning limit must be numbers.")
            return redirect(url_for("edit_product", product_id=product_id))

        if price <= 0 or limit < 0:
            flash("Price must be above 0 and the limit cannot be negative.")
            return redirect(url_for("edit_product", product_id=product_id))

        product.price = price
        product.low_stock_limit = limit
        db.session.commit()
        flash(f"{product.name} updated.")
        return redirect(url_for("products"))

    return render_template("edit_product.html", product=product)

@app.route("/adjust", methods=["GET", "POST"])
def adjust():
    if request.method == "POST":
        try:
            product_id = int(request.form["product_id"])
            new_qty = int(request.form["new_quantity"])
        except ValueError:
            flash("Select a model and enter a whole number.")
            return redirect(url_for("adjust"))

        size = request.form["size"]
        reason = request.form["reason"].strip()

        if new_qty < 0 or size not in SIZES or not reason:
            flash("Enter a quantity of 0 or more and a reason.")
            return redirect(url_for("adjust"))

        variant = Variant.query.filter_by(product_id=product_id, size=size).first()
        if variant is None:
            flash("Invalid model or size.")
            return redirect(url_for("adjust"))

        old_qty = variant.quantity
        if old_qty == new_qty:
            flash("That is already the current stock. Nothing changed.")
            return redirect(url_for("adjust"))

        variant.quantity = new_qty
        db.session.add(StockAdjustment(product_id=product_id, size=size,
                                       old_quantity=old_qty, new_quantity=new_qty,
                                       reason=reason))
        db.session.commit()
        flash(f"{variant.product.name} size {size}: {old_qty} changed to {new_qty}.")
        return redirect(url_for("adjust"))

    products = Product.query.order_by(Product.name).all()
    catalog = {p.id: {v.size: v.quantity for v in p.variants} for p in products}
    adjustments = StockAdjustment.query.order_by(StockAdjustment.date.desc()).limit(10).all()
    return render_template("adjust.html", products=products, sizes=SIZES,
                           catalog=catalog, adjustments=adjustments)
@app.route("/invoice/<int:invoice_id>/cancel", methods=["POST"])
def cancel_invoice(invoice_id):
    invoice = db.get_or_404(Invoice, invoice_id)

    if invoice.status == "Cancelled":
        flash(f"{invoice.invoice_no} is already cancelled.")
        return redirect(url_for("invoices"))

    reason = request.form.get("reason", "").strip()
    if not reason:
        flash("Enter a reason to cancel the bill.")
        return redirect(url_for("invoices"))

    # put every piece back into stock
    for item in invoice.items:
        variant = Variant.query.filter_by(product_id=item.product_id,
                                          size=item.size).first()
        if variant:
            variant.quantity += item.quantity

    invoice.status = "Cancelled"
    invoice.cancel_reason = reason
    db.session.commit()          # stock and status saved together
    flash(f"{invoice.invoice_no} cancelled. Stock added back.")
    return redirect(url_for("invoices"))
if __name__ == "__main__":
    app.run(debug=True)