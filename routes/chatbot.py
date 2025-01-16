from flask import Blueprint, request, jsonify, session, current_app,logging, url_for, redirect,  render_template, url_for,Response
from models import Chatbot,Feedback, Ticket, TicketResponse
from werkzeug.utils import secure_filename
from extensions import db
from utils.nlp_utils import preprocess_text, get_general_answer
from utils.file_utils import extract_text_from_pdf, read_text_file,extract_folder_content,extract_text_from_url
from utils.api_utils import fetch_real_time_data
import json
import uuid
import os
from functools import wraps
from transformers import pipeline
import logging
import speech_recognition as sr
import tempfile
from sqlalchemy import desc
from flask_cors import cross_origin
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64
from models import Chatbot, GmailIntegration
from extensions import db
from routes.analytics import track_question_helper
from time import time
from datetime import datetime
logging.basicConfig(level=logging.ERROR)
chatbot_bp = Blueprint('chatbot', __name__)
recognizer = sr.Recognizer()




def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function

def handle_errors(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            current_app.logger.error(f"Error in {f.__name__}: {str(e)}")
            return jsonify({"error": "An unexpected error occurred"}), 500
    return decorated_function

@chatbot_bp.route('/create_chatbot', methods=['POST'])
@login_required
@handle_errors
def create_chatbot():
    data = request.json
    name = data.get('name')

    new_chatbot = Chatbot(
        id=str(uuid.uuid4()),
        name=name,
        user_id=session['user_id'],
        data=json.dumps([])
    )
    db.session.add(new_chatbot)
    db.session.commit()

    return jsonify({"message": "Chatbot created successfully", "chatbot_id": new_chatbot.id}), 201






@chatbot_bp.route('/chatbots', methods=['GET'])
@login_required
@handle_errors
def get_chatbots():
    try:
        user_id = session.get('user_id') 
        if not user_id:
            return jsonify({"error": "Unauthorized"}), 401
            
        chatbots = Chatbot.query.filter_by(user_id=user_id).all()
        chatbot_list = [{"id": c.id, "name": c.name} for c in chatbots]
        
        return jsonify(chatbot_list), 200
    except Exception as e:
        current_app.logger.error(f"Error in get_chatbots: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500



@chatbot_bp.route('/gmail/authorize', methods=['GET'])
def gmail_authorize():
    """
    Initiate Gmail OAuth authorization flow
    """
    # Ensure you have set up Google Cloud OAuth 2.0 credentials
    client_secrets_file = current_app.config.get('GOOGLE_OAUTH_CLIENT_SECRETS_FILE')
    
    if not client_secrets_file or not os.path.exists(client_secrets_file):
        return jsonify({"error": "Google OAuth client secrets file not configured"}), 500

    # Define the scopes required for Gmail integration
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.send'
    ]

    # Create a Flow object
    flow = Flow.from_client_secrets_file(
        client_secrets_file,
        scopes=SCOPES,
        redirect_uri=url_for('chatbot.gmail_oauth_callback', _external=True)
    )

    # Generate authorization URL
    authorization_url, state = flow.authorization_url(
        access_type='offline',  # Enables refresh tokens
        prompt='consent'  # Force user to approve access every time
    )

    # Store the state in the session for CSRF protection
    session['oauth_state'] = state

    return redirect(authorization_url)

@chatbot_bp.route('/gmail/oauth/callback', methods=['GET'])
def gmail_oauth_callback():
    """
    Handle OAuth callback and store Gmail credentials
    """
    
    if 'oauth_state' not in session:
        return jsonify({"error": "Invalid OAuth state"}), 400

    client_secrets_file = current_app.config.get('GOOGLE_OAUTH_CLIENT_SECRETS_FILE')
    
    if not client_secrets_file or not os.path.exists(client_secrets_file):
        return jsonify({"error": "Google OAuth client secrets file not configured"}), 500

    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.send'
    ]

    # Create a Flow object
    flow = Flow.from_client_secrets_file(
        client_secrets_file,
        scopes=SCOPES,
        redirect_uri=url_for('chatbot.gmail_oauth_callback', _external=True)
    )

    # Exchange authorization code for credentials
    flow.fetch_token(authorization_response=request.url)

    # Get credentials
    credentials = flow.credentials

    try:
        # Build Gmail service to get user's email
        gmail_service = build('gmail', 'v1', credentials=credentials)
        user_profile = gmail_service.users().getProfile(userId='me').execute()
        user_email = user_profile['emailAddress']

        # Convert credentials to a storable format
        cred_dict = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }

        # Check if a Gmail integration already exists for this user
        existing_integration = GmailIntegration.query.filter_by(
            user_id=session['user_id'], 
            email=user_email
        ).first()

        if existing_integration:
            # Update existing integration
            existing_integration.credentials = json.dumps(cred_dict)
        else:
            # Create new Gmail integration
            new_integration = GmailIntegration(
                user_id=session['user_id'],
                credentials=json.dumps(cred_dict),
                email=user_email
            )
            db.session.add(new_integration)

        db.session.commit()

        return jsonify({
            "message": "Gmail account successfully integrated",
            "email": user_email
        }), 200

    except Exception as e:
        current_app.logger.error(f"Gmail integration error: {str(e)}")
        return jsonify({"error": "Failed to complete Gmail integration"}), 500

@chatbot_bp.route('/gmail/integrations', methods=['GET'])
def get_gmail_integrations():
    """
    Retrieve all Gmail integrations for the current user
    """
    integrations = GmailIntegration.query.filter_by(user_id=session['user_id']).all()
    
    integration_list = [{
        'id': integration.id,
        'email': integration.email,
        'created_at': integration.created_at.isoformat()
    } for integration in integrations]

    return jsonify(integration_list), 200

@chatbot_bp.route('/gmail/integrations/<int:integration_id>', methods=['DELETE'])
def delete_gmail_integration(integration_id):
    """
    Delete a specific Gmail integration
    """
    integration = GmailIntegration.query.get(integration_id)
    
    if not integration or integration.user_id != session['user_id']:
        return jsonify({"error": "Integration not found or unauthorized"}), 404

    db.session.delete(integration)
    db.session.commit()

    return jsonify({"message": "Gmail integration deleted successfully"}), 200



def transcribe_audio():
    with sr.Microphone() as source:
        print("Listening...")
        audio = recognizer.listen(source)
        try:
            text = recognizer.recognize_google(audio)
            print(f"You said: {text}")
            return text
        except sr.UnknownValueError:
            print("Sorry, I couldn't understand that.")
            return None
        except sr.RequestError as e:
            print(f"Could not request results; {e}")
            return None



@chatbot_bp.route('/train_chatbot/<chatbot_id>', methods=['POST'])
@handle_errors
def train_chatbot(chatbot_id):
    try:
        chatbot = Chatbot.query.get(chatbot_id)
        if not chatbot or chatbot.user_id != session['user_id']:
            return jsonify({"error": "Chatbot not found or unauthorized"}), 404
        
        file = request.files.get('file')
        api_url = request.form.get('api_url')
        folder_path = request.form.get('folder_path')
        website_url = request.form.get('website_url')
        
        pdf_data = []
        db_data = []
        folder_data = []
        web_data = []
        
        if file:
            filename = secure_filename(file.filename)
            upload_folder = current_app.config['UPLOAD_FOLDER']
            
            os.makedirs(upload_folder, exist_ok=True)
            
            filepath = os.path.join(upload_folder, filename)
            file.save(filepath)
            
            file_extension = os.path.splitext(filename)[1].lower()
            
            try:
                if file_extension == '.pdf':
                    pdf_text = extract_text_from_pdf(filepath)
                    pdf_data.append(pdf_text)
                    print(f"data:{pdf_data}")
                elif file_extension in ['.txt', '.md', '.rst']:
                    raw_text = read_text_file(filepath)
                    pdf_data.append({'page': 'file', 'text': raw_text})
                    
                else:
                    return jsonify({"error": f"Unsupported file type: {file_extension}"}), 400
            except Exception as e:
                current_app.logger.error(f"Error processing file {filename}: {str(e)}")
                return jsonify({"error": f"Error processing file {filename}: {str(e)}"}), 500
            finally:
                if os.path.exists(filepath):
                    os.remove(filepath)
        
        if api_url:
            try:
                real_time_data = fetch_real_time_data(api_url)
                if real_time_data:
                    real_time_text = json.dumps(real_time_data, indent=2)
                    db_data.append({'page': 'real_time', 'text': real_time_text})
            except Exception as e:
                current_app.logger.error(f"Error fetching data from API {api_url}: {str(e)}")
                return jsonify({"error": f"Error fetching data from API: {str(e)}"}), 500
        
        if folder_path:
            try:
                folder_data = extract_folder_content(folder_path)
            except Exception as e:
                current_app.logger.error(f"Error extracting content from folder {folder_path}: {str(e)}")
                return jsonify({"error": f"Error extracting content from folder: {str(e)}"}), 500
        
        if website_url:
            try:
                extracted_data = extract_text_from_url(website_url)
                if isinstance(extracted_data, list) and extracted_data and extracted_data[0].get('tag') == 'error':
                    return jsonify({"error": extracted_data[0]['text']}), 400
                web_data = extracted_data
            except Exception as e:
                current_app.logger.error(f"Error extracting text from URL {website_url}: {str(e)}")
                return jsonify({"error": f"Error extracting text from URL: {str(e)}"}), 500
        

        
        if not pdf_data and not db_data and not folder_data and not web_data:
            return jsonify({"error": "No data provided. Please upload a file, provide a folder path, provide an API URL, provide a website URL, or ensure MongoDB has data."}), 400
       
        new_data = {
            "pdf_data": pdf_data,
            "db_data": db_data,
            "folder_data": folder_data,
            "web_data": web_data
        }
        
        # If chatbot.data is empty, initialize it as a list
        if not chatbot.data:
            chatbot.data = []
        
        # If chatbot.data is a string, parse it first
        if isinstance(chatbot.data, str):
            chatbot.data = json.loads(chatbot.data)
        
        # Append the new data to the existing data
        if isinstance(chatbot.data, list):
            chatbot.data.append(new_data)
        else:
            chatbot.data = [chatbot.data, new_data]
        
        # Convert the entire data structure back to a JSON string
        chatbot.data = json.dumps(chatbot.data)
        
        db.session.commit()
        
        return jsonify({"message": "Chatbot trained successfully"}), 200
    
    except Exception as e:
        current_app.logger.error(f"Unexpected error in train_chatbot: {str(e)}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500



@chatbot_bp.route('/chatbot/<chatbot_id>', methods=['GET'])
def get_chatbot_data(chatbot_id):
    chatbot = Chatbot.query.get(chatbot_id)
    if not chatbot or chatbot.user_id != session['user_id']:
        return jsonify({"error": "Chatbot not found or unauthorized"}), 404
    
   

    return jsonify({"id": chatbot.id, "name": chatbot.name, "data": chatbot.data}), 200


@chatbot_bp.route('/chatbot/<chatbot_id>', methods=['PUT'])
def update_chatbot_data(chatbot_id):
    chatbot = Chatbot.query.get(chatbot_id)
    if not chatbot or chatbot.user_id != session['user_id']:
        return jsonify({"error": "Chatbot not found or unauthorized"}), 404

    data = request.json
    chatbot.name = data.get('name', chatbot.name)
    chatbot.data = data.get('data', chatbot.data)

    db.session.commit()

    return jsonify({"message": "Chatbot updated successfully"}), 200


@chatbot_bp.route('/delete_chatbot/<chatbot_id>', methods=['DELETE'])
@handle_errors
def delete_chatbot(chatbot_id):
    chatbot = Chatbot.query.get(chatbot_id)
    if not chatbot or chatbot.user_id != session['user_id']:
        return jsonify({"error": "Chatbot not found or unauthorized"}), 404
    
    db.session.delete(chatbot)
    db.session.commit()
    
    return jsonify({"message": "Chatbot deleted successfully"}), 200



@chatbot_bp.route('/chatbots/<chatbot_id>', methods=['GET'])
@handle_errors
def get_chatbot(chatbot_id):
    user_id = session['user_id']
    chatbots = Chatbot.query.filter_by(user_id=user_id).all()

    chatbot = Chatbot.query.get_or_404(chatbot_id)
    
   
    if chatbot.user_id != user_id:
        return jsonify({"error": "Unauthorized access"}), 403

    chatbot_list = [{"id": c.id, "name": c.name} for c in chatbots]
    
    return jsonify({
        "chatbot": {
            "id": chatbot.id, 
            "name": chatbot.name
        },
        "chatbot_list": chatbot_list
    }), 200

@chatbot_bp.route('/chatbot/<chatbot_id>/ask', methods=['POST'])
def chatbot_ask(chatbot_id):
    start_time = time()  
    
    chatbot = Chatbot.query.get(chatbot_id)
    if not chatbot:
        return jsonify({"error": "Chatbot not found"}), 404

    if request.content_type == 'application/json':
        # Handle JSON input
        data = request.json
        question = data.get('question')
    else:
        return jsonify({"error": "Unsupported content type"}), 415

    if not question:
        return jsonify({"error": "No question provided"}), 400

    try:
        chatbot_data_str = chatbot.data if isinstance(chatbot.data, str) else json.dumps(chatbot.data)
        chatbot_data = json.loads(chatbot_data_str)
        
        current_app.logger.debug(f"Chatbot data type: {type(chatbot_data)}")
        current_app.logger.debug(f"Chatbot data: {chatbot_data}")
        
        if isinstance(chatbot_data, list):
            if len(chatbot_data) > 0:
                chatbot_data = chatbot_data[-1]
            else:
                raise ValueError("Chatbot data list is empty")
        elif not isinstance(chatbot_data, dict):
            raise ValueError(f"Invalid chatbot data format: {type(chatbot_data)}")
        
        current_app.logger.debug(f"Processed chatbot data type: {type(chatbot_data)}")
        current_app.logger.debug(f"Processed chatbot data: {chatbot_data}")

       
       
        answer = get_general_answer(json.dumps(chatbot_data), question)
        
       
        processing_time = time() - start_time
        
        
       # Track analytics
        analytics_data = {
            "question": question,
            "answer": answer,
            "question_metadata": {
                "processing_time": time() - start_time,
                "keywords_matched": [
                    keyword for keyword in ["proce", "inventory", "stock", "available", "category", "type"]
                    if keyword in question.lower()
                ]
            }
        }
        track_question_helper(chatbot_id, analytics_data)
        
        return jsonify({
            "question": question,
            "answer": answer,
            "processing_time": round(time() - start_time, 3)
        })

    except json.JSONDecodeError as e:
        current_app.logger.error(f"JSON decode error: {str(e)}")
        return jsonify({"error": "Invalid chatbot data format"}), 500
    except ValueError as e:
        current_app.logger.error(f"Value error: {str(e)}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        current_app.logger.error(f"Error in chatbot_ask: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500




def transcribe_audio_file(file_path):
    r = sr.Recognizer()
    with sr.AudioFile(file_path) as source:
        audio = r.record(source)
    try:
        return r.recognize_google(audio)
    except sr.UnknownValueError:
        print("Google Speech Recognition could not understand audio")
    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")
    return None





@chatbot_bp.route('/chatbot/<chatbot_id>/feedback', methods=['POST', 'OPTIONS'])
def submit_feedback(chatbot_id):
    if request.method == 'OPTIONS':
        return '', 204
    
    chatbot = Chatbot.query.get(chatbot_id)
    if not chatbot:
        return jsonify({"error": "Chatbot not found"}), 404

    data = request.json
    feedback_text = data.get('feedback')
    
    user_id = request.headers.get('User-ID', '4269')  # Retrieve the user ID

    user_id = data.get('user_id')  
    if not user_id:
        
        user_id = '4269'
    if not feedback_text:
        return "Feedback is missing", 400

    if not feedback_text:
        return jsonify({"error": "No feedback provided"}), 400
    if not user_id:
        return jsonify({"error": "User ID is missing"}), 400  

    try:
        new_feedback = Feedback(
            chatbot_id=chatbot_id,
            user_id=4269,  
            feedback=feedback_text,
            created_at=datetime.utcnow()
        )
        db.session.add(new_feedback)
        db.session.commit()
        return jsonify({"message": "Feedback submitted successfully"}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error in submit_feedback: {str(e)}")
        return jsonify({"error": "An error occurred while saving the feedback"}), 500




@chatbot_bp.route('/chatbot/<chatbot_id>/feedback', methods=['GET'])
@login_required
@handle_errors
def get_chatbot_feedback(chatbot_id):
    chatbot = Chatbot.query.get(chatbot_id)
    if not chatbot:
        return jsonify({"error": "Chatbot not found"}), 404
    
    
    feedback_list = Feedback.query.filter_by(chatbot_id=chatbot_id).order_by(desc(Feedback.created_at)).all()
    
    
    feedback_strings = []
    for feedback in feedback_list:
        feedback_str = (
            f"Feedback ID: {feedback.id}\n"
            f"User ID: {feedback.user_id}\n"
            f"Feedback: {feedback.feedback}\n"
            f"Created At: {feedback.created_at.isoformat()}\n"
            f"------------------------"
        )
        feedback_strings.append(feedback_str)
    
    
    combined_feedback = "\n".join(feedback_strings)
    
    return jsonify({
        "chatbot_name": chatbot.name,
        "feedback": combined_feedback
    }), 200






@chatbot_bp.route('/chatbot/all-feedback', methods=['GET'])
def get_all_chatbots_feedback():
    
    chatbots = Chatbot.query.all()
    
    if not chatbots:
        return jsonify({"error": "No chatbots found"}), 404
    
    response_data = []
    
    for chatbot in chatbots:
        # Query all feedback for each chatbot
        feedback_list = Feedback.query.filter_by(chatbot_id=chatbot.id)\
                              .order_by(desc(Feedback.created_at)).all()
        
       
        feedback_strings = []
        for feedback in feedback_list:
            feedback_str = (
                f"Feedback ID: {feedback.id}\n"
                f"User ID: {feedback.user_id}\n"
                f"Feedback: {feedback.feedback}\n"
                f"Created At: {feedback.created_at.isoformat()}\n"
                f"------------------------"
            )
            feedback_strings.append(feedback_str)
        
       
        chatbot_data = {
            "chatbot_id": chatbot.id,
            "chatbot_name": chatbot.name,
            "feedback": "\n".join(feedback_strings) if feedback_strings else "No feedback available"
        }
        response_data.append(chatbot_data)
    
    return jsonify({
        "total_chatbots": len(chatbots),
        "chatbots": response_data
    }), 200




@chatbot_bp.route('/get_chatbot_script/<chatbot_id>')
@login_required
@handle_errors
def get_chatbot_script(chatbot_id):
    chatbot = Chatbot.query.get(chatbot_id)
    if not chatbot:
        return jsonify({"error": "Chatbot not found"}), 404
    
    # Generate URLs for the API endpoints
    ask_url = url_for('chatbot.chatbot_ask', chatbot_id=chatbot_id, _external=True)
    feedback_url = url_for('chatbot.submit_feedback', chatbot_id=chatbot_id, _external=True)
    widget_url = url_for('static', filename='js/widget.js', _external=True)
    theme_color=""
    ticket_url=url_for('chatbot.create_ticket', chatbot_id=chatbot_id, _external=True )
    avatar=""
   
    integration_code = f'''<!-- you can change the color of the theme used in this chat toggle to be integrated into your website  with hexadecimal color -->
    <!-- you can also change the default image of the avatar used in the chatbot widget by changing the data-avatar variable an image   -->
   <script 
    src="{widget_url}"
    data-chatbot-id="{chatbot_id}"
    data-name="{chatbot.name}"
    data-ask-url="{ask_url}"
    data-feedback-url="{feedback_url}"
    data-ticket-url="{ticket_url}"
    data-theme-color="{theme_color}"
    data-avatar="{avatar}"
    ></script>'''
    
    return jsonify({
        'integration_code': integration_code,
        'preview': integration_code
    })







@chatbot_bp.route('/ticket/create/<chatbot_id>', methods=['POST'])
def create_ticket(chatbot_id):
    data = request.json

    # Check required fields
    if not all(field in data for field in ['subject', 'description', 'account_details']):
        return jsonify({"error": "Missing required fields"}), 400

   
    new_ticket = Ticket(
        user_id=4269,  # Always use the default user
        chatbot_id=chatbot_id,
        subject=data['subject'],
        description=data['description'],
        priority=data.get('priority', 'medium'),
        account_details=data['account_details']
    )

    try:
        db.session.add(new_ticket)
        db.session.commit()
        return jsonify({
            "message": "Ticket created successfully",
            "ticket_id": new_ticket.id
        }), 201
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error in create_ticket: {str(e)}")
        return jsonify({"error": "An error occurred while creating the ticket"}), 500



@chatbot_bp.route('/tickets/<chatbot_id>', methods=['GET'])
@login_required
@handle_errors
def list_tickets1(chatbot_id):
    
    user_tickets = Ticket.query.filter_by(chatbot_id=chatbot_id).all()
    
    return jsonify({
        "tickets": [{
            "id": ticket.id,
            "subject": ticket.subject,
            "status": ticket.status,
            "priority": ticket.priority,
            "created_at": ticket.created_at.isoformat(),
            "chatbot_id": ticket.chatbot_id,
            "user_id": ticket.user_id,
            "account_details": ticket.account_details
        } for ticket in user_tickets]
    }), 200


@chatbot_bp.route('/tickets', methods=['GET'])
@login_required
def list_tickets():
    
    user_tickets = Ticket.query.all()
    return jsonify({
        "tickets": [{
            "id": ticket.id,
            "subject": ticket.subject,
            "status": ticket.status,
            "priority": ticket.priority,
            "created_at": ticket.created_at.isoformat()
        } for ticket in user_tickets]
    }), 200


@chatbot_bp.route('/ticket/<ticket_id>', methods=['GET'])
@login_required
@handle_errors
def get_ticket(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    responses = TicketResponse.query.filter_by(ticket_id=ticket_id).all()
    
    return jsonify({
        "ticket": {
            "id": ticket.id,
            "subject": ticket.subject,
            "description": ticket.description,
            "status": ticket.status,
            "priority": ticket.priority,
            "account_details": ticket.account_details,
            "created_at": ticket.created_at.isoformat()
        },
        "responses": [{
            "id": response.id,
            "message": response.message,
            "user_id": response.user_id,
            "created_at": response.created_at.isoformat()
        } for response in responses]
    }), 200


@chatbot_bp.route('/ticket/<ticket_id>/update-status', methods=['PATCH'])
@login_required
@handle_errors
def update_ticket_status(ticket_id):
    data = request.json
    if 'status' not in data:
        return jsonify({"error": "Status is required"}), 400
    
    ticket = Ticket.query.get_or_404(ticket_id)
    ticket.status = data['status']
    db.session.commit()
    
    return jsonify({
        "message": "Ticket status updated successfully",
        "ticket": {
            "id": ticket.id,
            "status": ticket.status
        }
    }), 200



@chatbot_bp.route('/ticket/delete/<ticket_id>', methods=['DELETE'])
@login_required
@handle_errors
def delete_ticket(ticket_id):
    ticket = Ticket.query.get(ticket_id)
    if not ticket:
        return jsonify({"error": "Ticket not found"}), 404

    db.session.delete(ticket)
    db.session.commit()
    return jsonify({"message": "Ticket deleted successfully"}), 200
