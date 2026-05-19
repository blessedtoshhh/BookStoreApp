import csv
import os
from app import app
from models import db, User, Author, Book
from werkzeug.security import generate_password_hash

with app.app_context():
    # Test accounts
    accounts = [
        {"name": "Employee Test", "email": "employee@inkandleather.com", "password": "employee123", "role": "employee"},
        {"name": "Manager Test",  "email": "manager@inkandleather.com",  "password": "manager123",  "role": "manager"},
        {"name": "Customer Test", "email": "customer@inkandleather.com", "password": "customer123", "role": "customer"},
    ]

    for a in accounts:
        if not User.query.filter_by(email=a["email"]).first():
            db.session.add(User(
                name=a["name"],
                email=a["email"],
                password_hash=generate_password_hash(a["password"]),
                role=a["role"],
            ))
            print(f"Created {a['role']}: {a['email']}")
        else:
            print(f"Already exists: {a['email']}")

    # Sample books
    books = [
        {"author": "Herman Melville",    "title": "Moby Dick",                   "isbn": "978-0-14-243723-9", "price": 12.99, "stock": 5,  "category": "Classic Fiction",  "description": "A sailor's obsessive quest to hunt a white whale."},
        {"author": "Jane Austen",        "title": "Pride and Prejudice",         "isbn": "978-0-14-143951-8", "price": 9.99,  "stock": 8,  "category": "Classic Fiction",  "description": "A witty story of love and social standing in Regency England."},
        {"author": "F. Scott Fitzgerald","title": "The Great Gatsby",            "isbn": "978-0-7432-7356-5", "price": 10.99, "stock": 2,  "category": "Classic Fiction",  "description": "A portrait of the Jazz Age and the American Dream."},
        {"author": "George Orwell",      "title": "1984",                        "isbn": "978-0-45-152493-5", "price": 11.99, "stock": 0,  "category": "Dystopian Fiction","description": "A chilling vision of a totalitarian surveillance state."},
        {"author": "Frank Herbert",      "title": "Dune",                        "isbn": "978-0-44-101844-5", "price": 14.99, "stock": 3,  "category": "Science Fiction",  "description": "An epic tale of politics, religion, and survival on a desert planet."},
        {"author": "J.R.R. Tolkien",    "title": "The Hobbit",                  "isbn": "978-0-54-792822-7", "price": 13.99, "stock": 1,  "category": "Fantasy",          "description": "Bilbo Baggins is swept into an unexpected adventure."},
        {"author": "Agatha Christie",    "title": "Murder on the Orient Express","isbn": "978-0-06-207350-3", "price": 10.49, "stock": 6,  "category": "Mystery",          "description": "Hercule Poirot investigates a murder aboard a snowbound train."},
        {"author": "Toni Morrison",      "title": "Beloved",                     "isbn": "978-1-40-003341-6", "price": 12.49, "stock": 0,  "category": "Historical Fiction","description": "A haunting story of slavery's trauma and legacy."},
    ]

    for b in books:
        author = Author.query.filter_by(name=b["author"]).first()
        if not author:
            author = Author(name=b["author"])
            db.session.add(author)
            db.session.flush()

        if not Book.query.filter_by(isbn=b["isbn"]).first():
            db.session.add(Book(
                title=b["title"],
                author_id=author.id,
                isbn=b["isbn"],
                price=b["price"],
                stock_quantity=b["stock"],
                category=b["category"],
                description=b["description"],
            ))
            print(f"Added book: {b['title']}")
        else:
            print(f"Already exists: {b['title']}")

    # Books from CSV
    csv_path = os.path.join(os.path.dirname(__file__), "books.csv")
    if os.path.exists(csv_path):
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            csv_added = 0
            for row in reader:
                isbn = row["isbn"].strip()
                if isbn and Book.query.filter_by(isbn=isbn).first():
                    continue
                author = Author.query.filter_by(name=row["author"].strip()).first()
                if not author:
                    author = Author(name=row["author"].strip())
                    db.session.add(author)
                    db.session.flush()
                db.session.add(Book(
                    title=row["title"].strip(),
                    author_id=author.id,
                    isbn=isbn,
                    price=float(row["price_usd"]),
                    stock_quantity=int(row["stock_quantity"]),
                    category=row["genre"].strip(),
                ))
                csv_added += 1
        print(f"Added {csv_added} books from books.csv")

    db.session.commit()
    print("\nDone.")
