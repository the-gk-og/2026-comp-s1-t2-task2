"""
Database Module - PostgreSQL + CSV Support
Events & Form Builder Support
"""

import os
import csv
import json
import uuid
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DB_TYPE = os.getenv('DB_TYPE', 'csv').lower()
CSV_FILE_PATH = os.getenv('CSV_FILE_PATH', 'data/registrations.csv')
ADMIN_CSV_PATH = os.path.join(Path(CSV_FILE_PATH).parent, 'admin_users.csv')
EVENTS_CSV_PATH = os.path.join(Path(CSV_FILE_PATH).parent, 'events.csv')

# Conditional import of psycopg2 (only if using PostgreSQL)
if DB_TYPE == 'postgres':
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
    except ImportError:
        print("ERROR: psycopg2 not installed. Install with: pip install psycopg2-binary")
        exit(1)

# PostgreSQL connection pool
db_connection = None


def init_db():
    """Initialize database"""
    if DB_TYPE == 'postgres':
        init_postgres()
    else:
        init_csv()
    print(f"✓ Database initialized ({DB_TYPE.upper()})")


def init_postgres():
    """Initialize PostgreSQL database"""
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            database=os.getenv('DB_NAME', 'rsvp_db'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', '')
        )
        cur = conn.cursor()

        # Create tables
        cur.execute("""
            CREATE TABLE IF NOT EXISTS registrations (
                id VARCHAR(36) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL,
                ticket VARCHAR(50) NOT NULL,
                dietary VARCHAR(100),
                sessions TEXT NOT NULL,
                payment_status VARCHAR(50) NOT NULL,
                payment_method VARCHAR(50),
                timestamp TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS admin_users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_email ON registrations(email);
            CREATE INDEX IF NOT EXISTS idx_ticket ON registrations(ticket);
        """)

        conn.commit()
        conn.close()
        print("✓ PostgreSQL tables created")
    except Exception as e:
        print(f"Error initializing PostgreSQL: {e}")
        raise


def init_csv():
    """Initialize CSV files"""
    # Create data directory
    Path(CSV_FILE_PATH).parent.mkdir(parents=True, exist_ok=True)

    # Create registrations CSV if it doesn't exist
    if not Path(CSV_FILE_PATH).exists():
        headers = [
            'id', 'event_id', 'name', 'email', 'ticket', 'dietary',
            'sessions', 'paymentStatus', 'paymentMethod', 'custom_fields', 'timestamp'
        ]
        with open(CSV_FILE_PATH, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
        print(f"✓ Registrations CSV created at {CSV_FILE_PATH}")

    # Create events CSV if it doesn't exist
    if not Path(EVENTS_CSV_PATH).exists():
        with open(EVENTS_CSV_PATH, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'name', 'description', 'form_fields', 'is_active', 'created_at', 'updated_at'])
        
        # Create default demo event
        demo_fields = [
            {'name': 'name', 'label': 'Full Name', 'type': 'text', 'required': True},
            {'name': 'email', 'label': 'Email Address', 'type': 'email', 'required': True},
            {'name': 'ticket', 'label': 'Ticket Type', 'type': 'select', 'required': True, 'options': ['General', 'VIP', 'Student']},
        ]
        with open(EVENTS_CSV_PATH, 'a', newline='') as f:
            writer = csv.writer(f)
            event_id = str(uuid.uuid4())
            writer.writerow([
                event_id, 
                'Demo Event', 
                'Sample event for testing',
                json.dumps(demo_fields),
                'true',
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ])
        print(f"✓ Events CSV created with demo event")

    # Create admin users CSV if it doesn't exist
    if not Path(ADMIN_CSV_PATH).exists():
        with open(ADMIN_CSV_PATH, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'username', 'password_hash'])
        
        # Create default admin user
        import bcrypt
        default_password_hash = bcrypt.hashpw(b'admin123', bcrypt.gensalt(10)).decode('utf-8')
        with open(ADMIN_CSV_PATH, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['1', 'admin', default_password_hash])
        print(f"✓ Admin users file created with default admin (admin/admin123)")



# ──────────────────────────────────────────────────────────────────
# REGISTRATION CRUD OPERATIONS
# ──────────────────────────────────────────────────────────────────

def save_registration(data):
    """Save a new registration"""
    reg_id = str(uuid.uuid4())
    registration = {
        'id': reg_id,
        **data,
        'sessions': '|'.join(data['sessions']) if isinstance(data['sessions'], list) else data['sessions'],
        'timestamp': data.get('timestamp', datetime.now().isoformat()),
    }

    if DB_TYPE == 'postgres':
        return save_registration_postgres(registration)
    else:
        return save_registration_csv(registration)


def save_registration_postgres(reg):
    """Save registration to PostgreSQL"""
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        database=os.getenv('DB_NAME', 'rsvp_db'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', '')
    )
    cur = conn.cursor()

    query = """
        INSERT INTO registrations 
        (id, name, email, ticket, dietary, sessions, payment_status, payment_method, timestamp)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *;
    """

    cur.execute(query, (
        reg['id'],
        reg['name'],
        reg['email'],
        reg['ticket'],
        reg['dietary'],
        reg['sessions'],
        reg['paymentStatus'],
        reg['paymentMethod'],
        reg['timestamp'],
    ))

    result = cur.fetchone()
    conn.commit()
    conn.close()

    if result:
        return {
            'id': result[0],
            'name': result[1],
            'email': result[2],
            'ticket': result[3],
            'dietary': result[4],
            'sessions': result[5].split('|'),
            'paymentStatus': result[6],
            'paymentMethod': result[7],
            'timestamp': result[8].isoformat(),
        }
    return None


def save_registration_csv(reg):
    """Save registration to CSV"""
    row = [
        reg['id'],
        reg['name'],
        reg['email'],
        reg['ticket'],
        reg['dietary'],
        reg['sessions'],
        reg['paymentStatus'],
        reg['paymentMethod'],
        reg['timestamp'],
    ]

    with open(CSV_FILE_PATH, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(row)

    return {
        'id': reg['id'],
        'name': reg['name'],
        'email': reg['email'],
        'ticket': reg['ticket'],
        'dietary': reg['dietary'],
        'sessions': reg['sessions'].split('|'),
        'paymentStatus': reg['paymentStatus'],
        'paymentMethod': reg['paymentMethod'],
        'timestamp': reg['timestamp'],
    }


def get_registrations():
    """Fetch all registrations"""
    if DB_TYPE == 'postgres':
        return get_registrations_postgres()
    else:
        return get_registrations_csv()


def get_registrations_postgres():
    """Get registrations from PostgreSQL"""
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        database=os.getenv('DB_NAME', 'rsvp_db'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', '')
    )
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute('SELECT * FROM registrations ORDER BY timestamp DESC;')
    rows = cur.fetchall()
    conn.close()

    registrations = []
    for row in rows:
        registrations.append({
            'id': row['id'],
            'name': row['name'],
            'email': row['email'],
            'ticket': row['ticket'],
            'dietary': row['dietary'],
            'sessions': row['sessions'].split('|'),
            'paymentStatus': row['payment_status'],
            'paymentMethod': row['payment_method'],
            'timestamp': row['timestamp'].isoformat(),
        })

    return registrations


def get_registrations_csv():
    """Get registrations from CSV"""
    if not Path(CSV_FILE_PATH).exists():
        return []

    registrations = []
    with open(CSV_FILE_PATH, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            registrations.append({
                'id': row['id'],
                'name': row['name'],
                'email': row['email'],
                'ticket': row['ticket'],
                'dietary': row['dietary'],
                'sessions': [s for s in row['sessions'].split('|') if s],
                'paymentStatus': row['paymentStatus'],
                'paymentMethod': row['paymentMethod'],
                'timestamp': row['timestamp'],
            })

    return list(reversed(registrations))  # Most recent first


def get_registration_by_id(reg_id):
    """Fetch a single registration by ID"""
    if DB_TYPE == 'postgres':
        return get_registration_by_id_postgres(reg_id)
    else:
        return get_registration_by_id_csv(reg_id)


def get_registration_by_id_postgres(reg_id):
    """Get registration from PostgreSQL"""
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        database=os.getenv('DB_NAME', 'rsvp_db'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', '')
    )
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute('SELECT * FROM registrations WHERE id = %s;', (reg_id,))
    row = cur.fetchone()
    conn.close()

    if row:
        return {
            'id': row['id'],
            'name': row['name'],
            'email': row['email'],
            'ticket': row['ticket'],
            'dietary': row['dietary'],
            'sessions': row['sessions'].split('|'),
            'paymentStatus': row['payment_status'],
            'paymentMethod': row['payment_method'],
            'timestamp': row['timestamp'].isoformat(),
        }
    return None


def get_registration_by_id_csv(reg_id):
    """Get registration from CSV"""
    registrations = get_registrations_csv()
    for reg in registrations:
        if reg['id'] == reg_id:
            return reg
    return None


def update_registration(reg_id, updates):
    """Update a registration"""
    if DB_TYPE == 'postgres':
        return update_registration_postgres(reg_id, updates)
    else:
        return update_registration_csv(reg_id, updates)


def update_registration_postgres(reg_id, updates):
    """Update registration in PostgreSQL"""
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        database=os.getenv('DB_NAME', 'rsvp_db'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', '')
    )
    cur = conn.cursor()

    fields = []
    values = []

    if updates.get('name'):
        fields.append('name = %s')
        values.append(updates['name'])
    if updates.get('email'):
        fields.append('email = %s')
        values.append(updates['email'])
    if updates.get('ticket'):
        fields.append('ticket = %s')
        values.append(updates['ticket'])
    if updates.get('dietary'):
        fields.append('dietary = %s')
        values.append(updates['dietary'])
    if updates.get('sessions'):
        fields.append('sessions = %s')
        sessions_str = '|'.join(updates['sessions']) if isinstance(updates['sessions'], list) else updates['sessions']
        values.append(sessions_str)
    if updates.get('paymentStatus'):
        fields.append('payment_status = %s')
        values.append(updates['paymentStatus'])

    if not fields:
        return get_registration_by_id_postgres(reg_id)

    fields.append('updated_at = CURRENT_TIMESTAMP')
    values.append(reg_id)

    query = f"UPDATE registrations SET {', '.join(fields)} WHERE id = %s RETURNING *;"

    cur.execute(query, values)
    result = cur.fetchone()
    conn.commit()
    conn.close()

    if result:
        return {
            'id': result[0],
            'name': result[1],
            'email': result[2],
            'ticket': result[3],
            'dietary': result[4],
            'sessions': result[5].split('|'),
            'paymentStatus': result[6],
            'paymentMethod': result[7],
            'timestamp': result[8].isoformat(),
        }
    return None


def update_registration_csv(reg_id, updates):
    """Update registration in CSV"""
    registrations = get_registrations_csv()
    updated = False

    for i, reg in enumerate(registrations):
        if reg['id'] == reg_id:
            if updates.get('name'):
                reg['name'] = updates['name']
            if updates.get('email'):
                reg['email'] = updates['email']
            if updates.get('ticket'):
                reg['ticket'] = updates['ticket']
            if updates.get('dietary'):
                reg['dietary'] = updates['dietary']
            if updates.get('sessions'):
                reg['sessions'] = updates['sessions']
            if updates.get('paymentStatus'):
                reg['paymentStatus'] = updates['paymentStatus']
            updated = True
            break

    if updated:
        write_csv_file(registrations)
        return registrations[i]
    return None


def delete_registration(reg_id):
    """Delete a registration"""
    if DB_TYPE == 'postgres':
        return delete_registration_postgres(reg_id)
    else:
        return delete_registration_csv(reg_id)


def delete_registration_postgres(reg_id):
    """Delete registration from PostgreSQL"""
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        database=os.getenv('DB_NAME', 'rsvp_db'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', '')
    )
    cur = conn.cursor()

    cur.execute('DELETE FROM registrations WHERE id = %s;', (reg_id,))
    deleted = cur.rowcount > 0
    conn.commit()
    conn.close()

    return deleted


def delete_registration_csv(reg_id):
    """Delete registration from CSV"""
    registrations = get_registrations_csv()
    original_count = len(registrations)

    registrations = [r for r in registrations if r['id'] != reg_id]

    if len(registrations) < original_count:
        write_csv_file(registrations)
        return True
    return False


def write_csv_file(registrations):
    """Write registrations back to CSV"""
    headers = [
        'id', 'name', 'email', 'ticket', 'dietary',
        'sessions', 'paymentStatus', 'paymentMethod', 'timestamp'
    ]

    with open(CSV_FILE_PATH, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()

        for reg in registrations:
            sessions_str = '|'.join(reg['sessions']) if isinstance(reg['sessions'], list) else reg['sessions']
            writer.writerow({
                'id': reg['id'],
                'name': reg['name'],
                'email': reg['email'],
                'ticket': reg['ticket'],
                'dietary': reg['dietary'],
                'sessions': sessions_str,
                'paymentStatus': reg['paymentStatus'],
                'paymentMethod': reg['paymentMethod'],
                'timestamp': reg['timestamp'],
            })


# ──────────────────────────────────────────────────────────────────
# ADMIN USER OPERATIONS
# ──────────────────────────────────────────────────────────────────

def save_admin_user(username, password_hash):
    """Save admin user"""
    if DB_TYPE == 'postgres':
        return save_admin_user_postgres(username, password_hash)
    else:
        return save_admin_user_csv(username, password_hash)


def save_admin_user_postgres(username, password_hash):
    """Save admin user (PostgreSQL)"""
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        database=os.getenv('DB_NAME', 'rsvp_db'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', '')
    )
    cur = conn.cursor()

    query = """
        INSERT INTO admin_users (username, password_hash)
        VALUES (%s, %s)
        RETURNING id, username;
    """

    cur.execute(query, (username, password_hash))
    result = cur.fetchone()
    conn.commit()
    conn.close()

    return result


def save_admin_user_csv(username, password_hash):
    """Save admin user (CSV)"""
    # Read existing users
    users = []
    if Path(ADMIN_CSV_PATH).exists():
        with open(ADMIN_CSV_PATH, 'r') as f:
            reader = csv.DictReader(f)
            users = list(reader) if reader else []
    
    # Check if user exists
    for user in users:
        if user.get('username') == username:
            return None  # User already exists
    
    # Add new user
    new_id = str(max([int(u.get('id', 0)) for u in users] + [0]) + 1)
    with open(ADMIN_CSV_PATH, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['id', 'username', 'password_hash'])
        writer.writerow({'id': new_id, 'username': username, 'password_hash': password_hash})
    
    return {'id': new_id, 'username': username}


def get_admin_user_by_username(username):
    """Get admin user by username"""
    if DB_TYPE == 'postgres':
        return get_admin_user_by_username_postgres(username)
    else:
        return get_admin_user_by_username_csv(username)


def get_admin_user_by_username_postgres(username):
    """Get admin user from PostgreSQL"""
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        database=os.getenv('DB_NAME', 'rsvp_db'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', '')
    )
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute('SELECT * FROM admin_users WHERE username = %s;', (username,))
    result = cur.fetchone()
    conn.close()

    return result


def get_admin_user_by_username_csv(username):
    """Get admin user from CSV"""
    if not Path(ADMIN_CSV_PATH).exists():
        return None
    
    with open(ADMIN_CSV_PATH, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('username') == username:
                return row
    
    return None


# ──────────────────────────────────────────────────────────────────
# EVENT MANAGEMENT
# ──────────────────────────────────────────────────────────────────

def create_event(name, description, form_fields):
    """Create a new event"""
    if DB_TYPE == 'postgres':
        return create_event_postgres(name, description, form_fields)
    else:
        return create_event_csv(name, description, form_fields)


def create_event_csv(name, description, form_fields):
    """Create event in CSV"""
    event_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    
    with open(EVENTS_CSV_PATH, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            event_id,
            name,
            description,
            json.dumps(form_fields),
            'true',
            now,
            now
        ])
    
    return {
        'id': event_id,
        'name': name,
        'description': description,
        'form_fields': form_fields,
        'is_active': True,
        'created_at': now
    }


def get_events():
    """Get all events"""
    if DB_TYPE == 'postgres':
        return get_events_postgres()
    else:
        return get_events_csv()


def get_events_csv():
    """Get events from CSV"""
    if not Path(EVENTS_CSV_PATH).exists():
        return []
    
    events = []
    with open(EVENTS_CSV_PATH, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            events.append({
                'id': row['id'],
                'name': row['name'],
                'description': row['description'],
                'form_fields': json.loads(row.get('form_fields', '[]')),
                'is_active': row.get('is_active', 'true').lower() == 'true',
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            })
    
    return list(reversed(events))  # Most recent first


def get_event_by_id(event_id):
    """Get event by ID"""
    if DB_TYPE == 'postgres':
        return get_event_by_id_postgres(event_id)
    else:
        return get_event_by_id_csv(event_id)


def get_event_by_id_csv(event_id):
    """Get event from CSV"""
    if not Path(EVENTS_CSV_PATH).exists():
        return None
    
    with open(EVENTS_CSV_PATH, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['id'] == event_id:
                return {
                    'id': row['id'],
                    'name': row['name'],
                    'description': row['description'],
                    'form_fields': json.loads(row.get('form_fields', '[]')),
                    'is_active': row.get('is_active', 'true').lower() == 'true',
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                }
    
    return None


def update_event(event_id, updates):
    """Update event"""
    if DB_TYPE == 'postgres':
        return update_event_postgres(event_id, updates)
    else:
        return update_event_csv(event_id, updates)


def update_event_csv(event_id, updates):
    """Update event in CSV"""
    events = []
    with open(EVENTS_CSV_PATH, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['id'] == event_id:
                row['name'] = updates.get('name', row['name'])
                row['description'] = updates.get('description', row['description'])
                if 'form_fields' in updates:
                    row['form_fields'] = json.dumps(updates['form_fields'])
                row['is_active'] = str(updates.get('is_active', row.get('is_active', 'true'))).lower()
                row['updated_at'] = datetime.now().isoformat()
            events.append(row)
    
    # Write back to CSV
    headers = ['id', 'name', 'description', 'form_fields', 'is_active', 'created_at', 'updated_at']
    with open(EVENTS_CSV_PATH, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(events)
    
    return get_event_by_id_csv(event_id)


def delete_event(event_id):
    """Delete event"""
    if DB_TYPE == 'postgres':
        return delete_event_postgres(event_id)
    else:
        return delete_event_csv(event_id)


def delete_event_csv(event_id):
    """Delete event from CSV"""
    events = []
    deleted = False
    with open(EVENTS_CSV_PATH, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['id'] != event_id:
                events.append(row)
            else:
                deleted = True
    
    if deleted:
        headers = ['id', 'name', 'description', 'form_fields', 'is_active', 'created_at', 'updated_at']
        with open(EVENTS_CSV_PATH, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(events)
    
    return deleted


def get_event_registrations(event_id):
    """Get registrations for an event"""
    registrations = get_registrations()
    return [r for r in registrations if r.get('event_id') == event_id]


# PostgreSQL event functions (stubs for now)
def create_event_postgres(name, description, form_fields):
    """Create event in PostgreSQL"""
    # TODO: Implement PostgreSQL event creation
    pass


def get_events_postgres():
    """Get events from PostgreSQL"""
    # TODO: Implement PostgreSQL event retrieval
    return []


def get_event_by_id_postgres(event_id):
    """Get event from PostgreSQL"""
    # TODO: Implement PostgreSQL event retrieval by ID
    return None


def update_event_postgres(event_id, updates):
    """Update event in PostgreSQL"""
    # TODO: Implement PostgreSQL event update
    pass


def delete_event_postgres(event_id):
    """Delete event from PostgreSQL"""
    # TODO: Implement PostgreSQL event deletion
    return False
