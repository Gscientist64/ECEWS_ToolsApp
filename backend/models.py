# models.py
import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Item(db.Model):
    __tablename__ = 'items'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name
        }



class Users(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(250), nullable=False)
    other_name = db.Column(db.String(250), nullable=False)
    lga = db.Column(db.String(250), nullable=False)
    facility = db.Column(db.String(250), nullable=False)
    username = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    role = db.Column(db.String(250), default="user")
    requests = db.relationship('Request', backref='users', lazy=True)

    def request_book(self, book, quantity):
        if book.quantity >= quantity:
            request_book = Request(book_id=book.id, user_id=self.id, quantity=quantity, status='Pending')
            db.session.add(request_book)
            db.session.commit()
            return request_book
        else:
            return None

class Admin(Users):
    def add_or_update_book(self, title, author, isbn, quantity):
        book = Book.query.filter_by(isbn=isbn).first()
        if book:
            book.quantity += quantity
        else:
            new_book = Book(title=title, author=author, isbn=isbn, quantity=quantity)
            db.session.add(new_book)
        db.session.commit()

    def view_stock(self):
        return Book.query.all()

    def view_pending_requests(self):
        return Request.query.filter_by(status='Pending').all()

    def approve_request(self, req):
        req.status = 'Approved'
        db.session.commit()

    def reject_request(self, req):
        req.status = 'Rejected'
        db.session.commit()

class Book(db.Model):
    __tablename__ = 'book'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(200), nullable=False)
    isbn = db.Column(db.String(250), unique=True, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

class Request(db.Model):
    __tablename__ = 'request'
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), default='Pending')
    date_created = db.Column(db.DateTime, default=datetime.datetime.utcnow)
from extensions import db
from datetime import datetime
from flask_login import UserMixin

class Users(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    other_name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(100), nullable=False)
    facility = db.Column(db.String(100), nullable=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    roles = db.Column(db.String(50), nullable=False, default='user')
    is_active_flag = db.Column(db.Boolean, default=True)
    
    # Establishing relationship with requests
    requests = db.relationship('Request', back_populates='user', cascade="all, delete-orphan")
    
    # Flask-Login required properties
    @property
    def is_active(self):
        return self.is_active_flag  # Ensure you have this column in your database

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)
    
    
    def to_dict(self):
        return {
            "id": self.id,
            "first_name": self.first_name,
            "other_name": self.other_name,
            "email": self.email,
            "facility": self.facility,
            "username": self.username,
            "roles": self.roles
        }

from extensions import db

class ToolCategory(db.Model):
    __tablename__ = 'tool_category'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    tools = db.relationship('Tool', backref='category', lazy=True)

    def __repr__(self):
        return f"<ToolCategory {self.name}>"

class Tool(db.Model):
    __tablename__ = 'tool'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    category_id = db.Column(db.Integer, db.ForeignKey('tool_category.id'))


    # Relationship with requested_tool (a tool can appear in many requested_tool records)
    requested_tool = db.relationship('RequestedTool', back_populates='tool', cascade="all, delete-orphan")                       

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.name
        }
    
    # Define a property to calculate available quantity dynamically
    @property
    def available_quantity(self):
        approved_requests = RequestedTool.query.filter_by(tool_id=self.id, status='approved').all()
        total_requested_quantity = sum(request.quantity for request in approved_requests)
        total_used_quantity = sum(usage.quantity_used for usage in self.usage_records)
        return total_requested_quantity - total_used_quantity

class Request(db.Model):
    __tablename__ = 'request'
    id = db.Column(db.Integer, primary_key=True)
#   tool_id = db.Column(db.Integer, db.ForeignKey('tool.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(50), default='Pending')
    date_requested = db.Column(db.DateTime, default=datetime.utcnow)
    date_approved = db.Column(db.DateTime, nullable=True)
    date_rejected = db.Column(db.DateTime, nullable=True)  # <-- ADDED ONLY THIS LINE
    
    # Relationship with User
    user = db.relationship('Users', back_populates='requests')

    # Relationship with Tool
  #  tool = db.relationship('Tool', back_populates='requests')

    # Relationship with RequestedTool
    requested_tools = db.relationship('RequestedTool', back_populates='request', cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "id": self.id,
        #    "tool_id": self.tool_id,
            "user_id": self.user_id,
            "user": self.user.first_name,  # Include user name for easy access
            "status": self.status,
            "tools": [tool.to_dict() for tool in self.requested_tools],
            "requested_tools": [tool.to_dict() for tool in self.requested_tools]
        }

class RequestedTool(db.Model):
    __tablename__ = 'requested_tool'
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('request.id'), nullable=False)
    tool_id = db.Column(db.Integer, db.ForeignKey('tool.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), default='Pending')  # Status for each requested tool


    # Relationship with Request
    request = db.relationship('Request', back_populates='requested_tools')

    # Relationship with Tool
    tool = db.relationship('Tool', back_populates='requested_tool')

  
    
    def to_dict(self):
        return {
            "id": self.id,
            "request_id": self.request_id,
            "tool_name": self.tool.name,  # Include tool name for easy access
            "quantity": self.quantity,
            "status": self.status
        }

class ToolUsage(db.Model):
    __tablename__ = 'tool_usage'
    id = db.Column(db.Integer, primary_key=True)
    tool_id = db.Column(db.Integer, db.ForeignKey('tool.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    quantity_used = db.Column(db.Integer, nullable=False)
    date_used = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    tool = db.relationship('Tool', backref='usage_records')
    user = db.relationship('Users', backref='usage_records')

    def to_dict(self):
        return {
            "id": self.id,
            "tool_id": self.tool_id,
            "tool_name": self.tool.name,
            "user_id": self.user_id,
            "user_name": self.user.first_name,
            "quantity_used": self.quantity_used,
            "date_used": self.date_used
        }
