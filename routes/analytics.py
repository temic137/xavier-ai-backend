
from extensions import db
from datetime import datetime
import json
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy import func, desc
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, session, current_app,logging, url_for, redirect
from extensions import db
import json
from functools import wraps
import logging
from sqlalchemy import desc
from models import Chatbot, GmailIntegration,QuestionAnalytics
from extensions import db

analytics_bp = Blueprint('analytics', __name__)


logging.basicConfig(level=logging.ERROR)


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


@analytics_bp.route('/analytics/questions/<chatbot_id>', methods=['GET'])
@login_required
@handle_errors
def get_chatbot_analytics(chatbot_id):
    """Get analytics for a specific chatbot"""
    try:
        
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        query = QuestionAnalytics.query.filter_by(chatbot_id=chatbot_id)
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(QuestionAnalytics.timestamp >= start_date)
        
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            query = query.filter(QuestionAnalytics.timestamp <= end_date)
        
        analytics = query.order_by(QuestionAnalytics.timestamp.desc()).all()
        
        return jsonify({
            "total_questions": len(analytics),
            "analytics": [{
                "question": record.question,
                "answer": record.answer,
                "timestamp": record.timestamp.isoformat(),
                "metadata": record.question_metadata
            } for record in analytics]
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving analytics: {str(e)}")
        return jsonify({"error": "Failed to retrieve analytics"}), 500


def track_question_helper(chatbot_id, question_data):
    """Helper function to track question analytics"""
    try:
        analytics_entry = QuestionAnalytics(
            chatbot_id=chatbot_id,
            question=question_data['question'],
            answer=question_data['answer'],
            question_metadata=question_data.get('question_metadata', {})
        )
        
        db.session.add(analytics_entry)
        db.session.commit()
        return True
    except Exception as e:
        current_app.logger.error(f"Error tracking analytics: {str(e)}")
        return False    

@analytics_bp.route('/analytics/common_questions/<chatbot_id>', methods=['GET'])
@login_required
@handle_errors
def get_common_questions(chatbot_id):
    """Get most commonly asked questions"""
    try:
        days = request.args.get('days', 30, type=int)
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        questions = QuestionAnalytics.query.filter(
            QuestionAnalytics.chatbot_id == chatbot_id,
            QuestionAnalytics.created_at >= cutoff_date
        ).all()

        
        question_counter = Counter(q.question for q in questions)
        
        top_questions = []
        for question, count in question_counter.most_common(10):
            latest_entry = QuestionAnalytics.query.filter_by(
                chatbot_id=chatbot_id,
                question=question
            ).order_by(desc(QuestionAnalytics.created_at)).first()

            top_questions.append({
                "question": question,
                "count": count,
                "latest_answer": latest_entry.answer,
                "last_asked": latest_entry.created_at.isoformat()
            })

        return jsonify({
            "top_questions": top_questions,
            "total_questions": len(questions),
            "timeframe_days": days
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error getting common questions: {str(e)}")
        return jsonify({"error": "Failed to get common questions"}), 500


@analytics_bp.route('/analytics/question_clusters/<chatbot_id>', methods=['GET'])
@login_required
@handle_errors
def get_question_clusters(chatbot_id):
    """Get question clusters by topic"""
    try:
        
        days = request.args.get('days', 30, type=int)
        cutoff_date = datetime.utcnow() - timedelta(days=days)

       
        entries = QuestionAnalytics.query.filter(
            QuestionAnalytics.chatbot_id == chatbot_id,
            QuestionAnalytics.created_at >= cutoff_date
        ).all()

        questions = [entry.question for entry in entries]
        
        if len(questions) < 5:
            return jsonify({
                "error": "Not enough questions for meaningful clustering",
                "minimum_required": 5,
                "current_count": len(questions)
            }), 400

       
        vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
        vectors = vectorizer.fit_transform(questions)
        
        n_clusters = min(10, len(questions) // 5)
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        clusters = kmeans.fit_predict(vectors)

        clustered_data = {}
        for idx, cluster_id in enumerate(clusters):
            if cluster_id not in clustered_data:
                clustered_data[cluster_id] = []
            clustered_data[cluster_id].append({
                "question": questions[idx],
                "answer": entries[idx].answer,
                "asked_at": entries[idx].created_at.isoformat()
            })

        feature_names = vectorizer.get_feature_names_out()
        clusters_info = []
        for cluster_id, questions_list in clustered_data.items():
            top_terms_idx = kmeans.cluster_centers_[cluster_id].argsort()[-5:][::-1]
            top_terms = [feature_names[idx] for idx in top_terms_idx]
            
            clusters_info.append({
                "cluster_id": int(cluster_id),
                "topic_terms": top_terms,
                "questions": questions_list,
                "question_count": len(questions_list)
            })

        return jsonify({
            "clusters": clusters_info,
            "total_questions": len(questions),
            "timeframe_days": days
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error clustering questions: {str(e)}")
        return jsonify({"error": "Failed to cluster questions"}), 500


@analytics_bp.route('/analytics/usage_patterns/<chatbot_id>', methods=['GET'])
@login_required
@handle_errors
def get_usage_patterns(chatbot_id):
    """Get usage patterns and trends"""
    try:
        
        days = request.args.get('days', 30, type=int)
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        
        daily_counts = db.session.query(
            func.date(QuestionAnalytics.created_at).label('date'),
            func.count(QuestionAnalytics.id).label('count')
        ).filter(
            QuestionAnalytics.chatbot_id == chatbot_id,
            QuestionAnalytics.created_at >= cutoff_date
        ).group_by(func.date(QuestionAnalytics.created_at))\
        .order_by('date').all()

       
        hourly_distribution = db.session.query(
            func.extract('hour', QuestionAnalytics.created_at).label('hour'),
            func.count(QuestionAnalytics.id).label('count')
        ).filter(
            QuestionAnalytics.chatbot_id == chatbot_id,
            QuestionAnalytics.created_at >= cutoff_date
        ).group_by('hour').order_by('hour').all()

        return jsonify({
            "daily_trends": [
                {"date": str(day.date), "count": day.count}
                for day in daily_counts
            ],
            "hourly_distribution": [
                {"hour": int(hour.hour), "count": hour.count}
                for hour in hourly_distribution
            ],
            "timeframe_days": days
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error getting usage patterns: {str(e)}")
        return jsonify({"error": "Failed to get usage patterns"}), 500


@analytics_bp.route('/analytics/dashboard/<chatbot_id>', methods=['GET'])
@login_required
@handle_errors
def get_analytics_dashboard(chatbot_id):
    """Get comprehensive analytics dashboard"""
    try:
        days = request.args.get('days', 30, type=int)
        
        
        common_questions = get_common_questions(chatbot_id)[0].json
        clusters = get_question_clusters(chatbot_id)[0].json
        usage_patterns = get_usage_patterns(chatbot_id)[0].json

        return jsonify({
            "common_questions": common_questions,
            "topic_clusters": clusters,
            "usage_patterns": usage_patterns,
            "last_updated": datetime.utcnow().isoformat(),
            "timeframe_days": days
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error getting dashboard data: {str(e)}")
        return jsonify({"error": "Failed to get dashboard data"}), 500
