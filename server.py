"""
RSVP Event Registration System - Flask Backend
Main application server serving HTML + API
"""

import os
from flask import Flask, jsonify, request, render_template, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
from datetime import timedelta
from pathlib import Path

# Load environment variables
load_dotenv()

# Import modules
from db import init_db, get_registrations, save_registration, get_registration_by_id, update_registration, delete_registration, get_event_by_id
from auth import create_routes as create_auth_routes
from stripe_handler import create_routes as create_stripe_routes
from event_routes import create_routes as create_event_routes
from email_service import send_confirmation_email, send_ticket_email
from google_wallet import get_wallet_setup_instructions

# Initialize Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# Configuration
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET', 'your_super_secret_key_change_this')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)

# Initialize JWT
jwt = JWTManager(app)

# Initialize database
with app.app_context():
    init_db()

# Register blueprints
create_auth_routes(app)
create_stripe_routes(app)
create_event_routes(app)

PORT = int(os.getenv('PORT', 3001))


# ──────────────────────────────────────────────────────────────────
# SERVE HTML PAGES
# ──────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Serve events listing page"""
    return render_template('index.html')


@app.route('/event/<event_id>')
def register_event(event_id):
    """Serve event registration form"""
    event = get_event_by_id(event_id)
    
    if not event:
        return jsonify({'error': 'Event not found'}), 404
    
    return render_template('register.html', event=event)


@app.route('/admin')
def admin_login():
    """Serve admin login page"""
    return render_template('admin/login.html')


@app.route('/admin/dashboard')
def admin_dashboard():
    """Serve admin dashboard"""
    return render_template('admin/events.html')


# Serve static files (CSS, JS)
@app.route('/style.css')
def serve_css():
    """Serve CSS file"""
    return send_from_directory('.', 'style.css')


@app.route('/app.js')
def serve_app_js():
    """Serve app JavaScript"""
    return send_from_directory('.', 'app.js')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'Server is running',
        'timestamp': __import__('datetime').datetime.now().isoformat()
    })


# ──────────────────────────────────────────────────────────────────
# REGISTRATIONS ENDPOINTS
# ──────────────────────────────────────────────────────────────────

@app.route('/api/registrations', methods=['GET'])
def get_all_registrations():
    """Fetch all registrations"""
    try:
        registrations = get_registrations()
        return jsonify(registrations)
    except Exception as e:
        print(f"Error fetching registrations: {e}")
        return jsonify({'error': 'Failed to fetch registrations'}), 500


@app.route('/api/registrations/<registration_id>', methods=['GET'])
def get_single_registration(registration_id):
    """Fetch a single registration by ID"""
    try:
        registration = get_registration_by_id(registration_id)
        if not registration:
            return jsonify({'error': 'Registration not found'}), 404
        return jsonify(registration)
    except Exception as e:
        print(f"Error fetching registration: {e}")
        return jsonify({'error': 'Failed to fetch registration'}), 500


@app.route('/api/registrations', methods=['POST'])
def create_registration():
    """Create a new registration"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['name', 'email', 'ticket', 'sessions']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400

        if not data['sessions'] or len(data['sessions']) == 0:
            return jsonify({'error': 'At least one session must be selected'}), 400

        # Determine payment method
        payment_method = data.get('paymentMethod', 'cash')

        # Create registration object
        registration = {
            'name': data['name'],
            'email': data['email'],
            'ticket': data['ticket'],
            'dietary': data.get('dietary', 'None'),
            'sessions': data['sessions'],
            'paymentStatus': 'Pending' if payment_method == 'stripe' else 'Paid',
            'paymentMethod': payment_method,
        }

        # If Stripe payment, redirect to checkout
        if payment_method == 'stripe':
            from stripe_handler import create_stripe_session
            try:
                session = create_stripe_session(registration)
                return jsonify({
                    'success': True,
                    'message': 'Stripe session created',
                    'redirectUrl': session.url
                })
            except Exception as e:
                print(f"Stripe error: {e}")
                return jsonify({'error': 'Failed to create payment session'}), 500

        # Save registration directly if not using Stripe
        saved_reg = save_registration(registration)

        # Send confirmation email
        try:
            send_confirmation_email(saved_reg)
        except Exception as e:
            print(f"Email error: {e}")
            # Continue even if email fails

        return jsonify({
            'success': True,
            'message': 'Registration created successfully',
            'registration': saved_reg
        }), 201

    except Exception as e:
        print(f"Error creating registration: {e}")
        return jsonify({'error': 'Failed to create registration'}), 500


@app.route('/api/registrations/<registration_id>', methods=['PUT'])
def update_single_registration(registration_id):
    """Update an existing registration"""
    try:
        data = request.get_json()

        updated_reg = update_registration(registration_id, {
            'name': data.get('name'),
            'email': data.get('email'),
            'ticket': data.get('ticket'),
            'dietary': data.get('dietary'),
            'sessions': data.get('sessions'),
            'paymentStatus': data.get('paymentStatus'),
        })

        if not updated_reg:
            return jsonify({'error': 'Registration not found'}), 404

        return jsonify({
            'success': True,
            'message': 'Registration updated successfully',
            'registration': updated_reg
        })

    except Exception as e:
        print(f"Error updating registration: {e}")
        return jsonify({'error': 'Failed to update registration'}), 500


@app.route('/api/registrations/<registration_id>', methods=['DELETE'])
def delete_single_registration(registration_id):
    """Delete a registration"""
    try:
        success = delete_registration(registration_id)

        if not success:
            return jsonify({'error': 'Registration not found'}), 404

        return jsonify({
            'success': True,
            'message': 'Registration deleted successfully'
        })

    except Exception as e:
        print(f"Error deleting registration: {e}")
        return jsonify({'error': 'Failed to delete registration'}), 500


# ──────────────────────────────────────────────────────────────────
# EMAIL ENDPOINTS
# ──────────────────────────────────────────────────────────────────

@app.route('/api/resend-email/<registration_id>', methods=['POST'])
def resend_email(registration_id):
    """Resend ticket email to an attendee"""
    try:
        registration = get_registration_by_id(registration_id)

        if not registration:
            return jsonify({'error': 'Registration not found'}), 404

        send_ticket_email(registration)

        return jsonify({
            'success': True,
            'message': 'Ticket email sent successfully'
        })

    except Exception as e:
        print(f"Error sending email: {e}")
        return jsonify({'error': 'Failed to send email'}), 500


# ──────────────────────────────────────────────────────────────────
# INFO ENDPOINTS
# ──────────────────────────────────────────────────────────────────

@app.route('/api/wallet-setup', methods=['GET'])
def wallet_setup_info():
    """Get wallet setup instructions"""
    return jsonify(get_wallet_setup_instructions())


# ──────────────────────────────────────────────────────────────────
# ERROR HANDLERS
# ──────────────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Internal server error'}), 500


# ──────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────

if __name__ == '__main__':

    app.run(debug=True, port=PORT, host='0.0.0.0')
