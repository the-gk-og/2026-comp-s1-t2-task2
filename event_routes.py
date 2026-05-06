from flask import jsonify, request, send_file
from db import (
    create_event, get_events, get_event_by_id, update_event, delete_event,
    get_event_registrations, get_registration_by_id, save_registration
)
from email_service import send_confirmation_email
from datetime import datetime
import csv
import io


def create_routes(app):
    """Create event management routes"""

    @app.route('/api/events', methods=['GET'])
    def list_events():
        """Get all events"""
        try:
            events = get_events()
            return jsonify(events)
        except Exception as e:
            print(f"Error fetching events: {e}")
            return jsonify({'error': 'Failed to fetch events'}), 500

    @app.route('/api/events', methods=['POST'])
    def create_new_event():
        """Create a new event (admin only)"""
        try:
            data = request.get_json()
            
            if not data.get('name'):
                return jsonify({'error': 'Event name is required'}), 400
            
            form_fields = data.get('form_fields', [])
            description = data.get('description', '')
            
            event = create_event(data['name'], description, form_fields)
            
            return jsonify({
                'success': True,
                'message': 'Event created successfully',
                'event': event
            }), 201
        
        except Exception as e:
            print(f"Error creating event: {e}")
            return jsonify({'error': 'Failed to create event'}), 500

    @app.route('/api/events/<event_id>', methods=['GET'])
    def get_single_event(event_id):
        """Get a single event by ID"""
        try:
            event = get_event_by_id(event_id)
            
            if not event:
                return jsonify({'error': 'Event not found'}), 404
            
            return jsonify(event)
        
        except Exception as e:
            print(f"Error fetching event: {e}")
            return jsonify({'error': 'Failed to fetch event'}), 500

    @app.route('/api/events/<event_id>', methods=['PUT'])
    def update_single_event(event_id):
        """Update an event (admin only)"""
        try:
            event = get_event_by_id(event_id)
            if not event:
                return jsonify({'error': 'Event not found'}), 404
            
            data = request.get_json()
            updated_event = update_event(event_id, data)
            
            return jsonify({
                'success': True,
                'message': 'Event updated successfully',
                'event': updated_event
            })
        
        except Exception as e:
            print(f"Error updating event: {e}")
            return jsonify({'error': 'Failed to update event'}), 500

    @app.route('/api/events/<event_id>', methods=['DELETE'])
    def delete_single_event(event_id):
        """Delete an event (admin only)"""
        try:
            success = delete_event(event_id)
            
            if not success:
                return jsonify({'error': 'Event not found'}), 404
            
            return jsonify({
                'success': True,
                'message': 'Event deleted successfully'
            })
        
        except Exception as e:
            print(f"Error deleting event: {e}")
            return jsonify({'error': 'Failed to delete event'}), 500

    @app.route('/api/events/<event_id>/registrations', methods=['GET'])
    def get_event_registrations_list(event_id):
        """Get registrations for an event (admin only)"""
        try:
            event = get_event_by_id(event_id)
            if not event:
                return jsonify({'error': 'Event not found'}), 404
            
            registrations = get_event_registrations(event_id)
            
            return jsonify({
                'event': event,
                'registrations': registrations,
                'count': len(registrations)
            })
        
        except Exception as e:
            print(f"Error fetching event registrations: {e}")
            return jsonify({'error': 'Failed to fetch registrations'}), 500

    @app.route('/api/register/<event_id>', methods=['POST'])
    def register_for_event(event_id):
        """Register for an event (public endpoint)"""
        try:
            # Get event to ensure it exists
            event = get_event_by_id(event_id)
            if not event:
                return jsonify({'error': 'Event not found'}), 404
            
            if not event.get('is_active'):
                return jsonify({'error': 'This event is not active'}), 400
            
            data = request.get_json()
            
            # Validate required fields from event's form
            required_fields = [f for f in event['form_fields'] if f.get('required')]
            for field in required_fields:
                if field['name'] not in data or not data[field['name']]:
                    return jsonify({'error': f"Missing required field: {field['label']}"}), 400
            
            # Extract standard fields
            registration = {
                'name': data.get('name', ''),
                'email': data.get('email', ''),
                'ticket': data.get('ticket', 'General'),
                'dietary': data.get('dietary', 'No requirements'),
                'sessions': data.get('sessions', []),
                'paymentStatus': data.get('paymentStatus', 'Pending'),
                'paymentMethod': data.get('paymentMethod', ''),
                'event_id': event_id,
                'custom_fields': {k: v for k, v in data.items() 
                                 if k not in ['name', 'email', 'ticket', 'dietary', 'sessions', 'paymentStatus', 'paymentMethod']},
                'timestamp': datetime.now().isoformat()
            }
            
            # Save registration
            reg = save_registration(registration)
            
            # Send confirmation email
            email_sent = send_confirmation_email(reg, event)
            
            return jsonify({
                'success': True,
                'message': 'Registration successful',
                'registration': reg,
                'email_sent': email_sent
            }), 201
        
        except Exception as e:
            print(f"Error registering for event: {e}")
            return jsonify({'error': 'Failed to register'}), 500

    @app.route('/api/events/<event_id>/export-csv', methods=['GET'])
    def export_registrations_csv(event_id):
        """Export event registrations as CSV"""
        try:
            event = get_event_by_id(event_id)
            if not event:
                return jsonify({'error': 'Event not found'}), 404
            
            registrations = get_event_registrations(event_id)
            
            # Create CSV in memory
            output = io.StringIO()
            
            if registrations:
                # Get all keys from registrations
                fieldnames = set()
                for reg in registrations:
                    fieldnames.update(reg.keys())
                fieldnames = sorted(list(fieldnames))
                
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(registrations)
            
            # Convert to bytes and send
            output.seek(0)
            mem = io.BytesIO()
            mem.write(output.getvalue().encode('utf-8'))
            mem.seek(0)
            
            return send_file(
                mem,
                mimetype='text/csv',
                as_attachment=True,
                download_name=f'{event["name"].replace(" ", "_")}_registrations.csv'
            )
        
        except Exception as e:
            print(f"Error exporting registrations: {e}")
            return jsonify({'error': 'Failed to export registrations'}), 500
