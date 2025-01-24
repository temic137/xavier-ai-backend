from extensions import db
from sqlalchemy.dialects.postgresql import JSON  # Import JSON type if using PostgreSQL
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from sqlalchemy import Text
from sqlalchemy.dialects import postgresql
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(128), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)  # Increase length
    chatbots = db.relationship('Chatbot', backref='owner', lazy=True)
    feedbacks = db.relationship('Feedback', backref='user', lazy=True)


class Chatbot(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    data = db.Column(JSON)  # JSON column to store both PDF and database data
    feedbacks = db.relationship(
        'Feedback',
        backref='chatbot',
        lazy=True,
        cascade="all, delete-orphan"
    )


class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chatbot_id = db.Column(db.String(36), db.ForeignKey('chatbot.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    feedback = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime)


class QuestionAnalytics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chatbot_id = db.Column(db.String(36), db.ForeignKey('chatbot.id', ondelete='CASCADE'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    question_metadata = db.Column(db.JSON) 


#------------------------------------------------
# START  OF NEW MODELS
#----------------------------------------------
class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    chatbot_id = db.Column(db.String(36), db.ForeignKey('chatbot.id'), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='open')
    priority = db.Column(db.String(20), default='medium')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    account_details = db.Column(db.JSON)

class TicketResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

#----------------------------------------
# END OF NEW MODELS
#------------------------------------------


from extensions import db
from datetime import datetime

class GmailIntegration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    credentials = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to User model
    user = db.relationship('User', backref=db.backref('gmail_integrations', lazy=True, cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<GmailIntegration {self.email}>'
