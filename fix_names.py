from app import app
from models import db, Product

with app.app_context():
    for p in Product.query.all():
        p.name = p.name.strip().title()
    db.session.commit()
    print("Done:", [p.name for p in Product.query.all()])