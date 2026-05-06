"""
Authentication Module for Admin Panel
"""

import os
import bcrypt
from flask import jsonify, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from functools import wraps
from dotenv import load_dotenv
from db import save_admin_user, get_admin_user_by_username

load_dotenv()

JWT_SECRET = os.getenv('JWT_SECRET', 'your_super_secret_key_change_this')


def create_routes(app):
    """Create authentication routes"""

    @app.route('/api/admin/login', methods=['POST'])
    def login_admin():
        """Admin login endpoint"""
        try:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')

            if not username or not password:
                return jsonify({'error': 'Missing username or password'}), 400

            user = get_admin_user_by_username(username)

            if not user:
                return jsonify({'error': 'Invalid credentials'}), 401

            # Check password
            if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                return jsonify({'error': 'Invalid credentials'}), 401

            # Create JWT token
            access_token = create_access_token(
                identity={'userId': user['id'], 'username': user['username']}
            )

            print(f"✓ Admin user {username} logged in")
            return jsonify({'success': True, 'token': access_token})

        except Exception as e:
            print(f"Login error: {e}")
            return jsonify({'error': 'Login failed'}), 500

    @app.route('/api/admin/create-user', methods=['POST'])
    @jwt_required()
    def create_admin_user():
        """Create a new admin user (protected route)"""
        try:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')

            if not username or not password:
                return jsonify({'error': 'Missing username or password'}), 400

            # Hash password
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(10))

            user = save_admin_user(username, password_hash.decode('utf-8'))

            print(f"✓ Admin user {username} created")
            return jsonify({
                'success': True,
                'message': 'Admin user created',
                'username': user['username']
            })

        except Exception as e:
            print(f"Error creating admin user: {e}")
            return jsonify({'error': str(e)}), 400

    @app.route('/api/admin/verify', methods=['GET'])
    @jwt_required()
    def verify_token():
        """Verify JWT token"""
        try:
            current_user = get_jwt_identity()
            return jsonify({
                'valid': True,
                'user': current_user
            })
        except Exception as e:
            return jsonify({'valid': False, 'error': str(e)}), 401


def verify_admin_token(f):
    """Decorator to verify admin token"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function


def generate_default_admin():
    """Generate default admin user"""
    try:
        default_username = 'admin'
        default_password = 'admin123'  # CHANGE THIS IN PRODUCTION!

        # Check if default admin already exists
        existing_admin = get_admin_user_by_username(default_username)

        if existing_admin:
            print("ℹ️  Default admin already exists")
            return existing_admin

        # Create default admin
        password_hash = bcrypt.hashpw(default_password.encode('utf-8'), bcrypt.gensalt(10))
        admin = save_admin_user(default_username, password_hash.decode('utf-8'))

        print("⚠️  DEFAULT ADMIN CREATED:")
        print(f"   Username: {default_username}")
        print(f"   Password: {default_password}")
        print("   ⚠️  CHANGE THE PASSWORD IMMEDIATELY!")

        return admin

    except Exception as e:
        print(f"Error generating default admin: {e}")
