import os
import stripe
from flask import request, jsonify
from dotenv import load_dotenv
from db import save_registration, update_registration, get_registration_by_id
from email_service import send_ticket_email

load_dotenv()

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')

# Ticket pricing configuration (in cents)
TICKET_PRICES = {
    'General': 5000,   # $50.00
    'VIP': 10000,     # $100.00
    'Student': 2500,  # $25.00
}


def create_routes(app):
    """Create Stripe routes"""

    @app.route('/api/stripe/create-session', methods=['POST'])
    def create_stripe_checkout():
        """Create a Stripe checkout session"""
        try:
            data = request.get_json()
            registration = data

            # Get the price for the ticket type
            price = TICKET_PRICES.get(registration.get('ticket'), TICKET_PRICES['General'])

            # Create line items
            line_items = [
                {
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f"{registration.get('ticket')} Ticket - Event Registration",
                            'description': f"Ticket Type: {registration.get('ticket')}",
                            'images': [
                                'https://via.placeholder.com/300x200?text=Event+Ticket',
                            ],
                        },
                        'unit_amount': price,
                    },
                    'quantity': 1,
                }
            ]

            # Create checkout session
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=line_items,
                mode='payment',
                customer_email=registration.get('email'),
                metadata={
                    'name': registration.get('name'),
                    'email': registration.get('email'),
                    'ticket_type': registration.get('ticket'),
                    'dietary': registration.get('dietary', ''),
                    'sessions': '|'.join(registration.get('sessions', [])),
                },
                success_url=f"{FRONTEND_URL}?payment=success&session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{FRONTEND_URL}?payment=cancelled",
            )

            print(f"✓ Stripe session created: {session.id}")
            return jsonify({'url': session.url})

        except Exception as e:
            print(f"Error creating Stripe session: {e}")
            return jsonify({'error': str(e)}), 400

    @app.route('/webhook/stripe', methods=['POST'])
    def stripe_webhook():
        """Handle Stripe webhook"""
        try:
            event = request.get_json()

            print(f"Processing Stripe event: {event.get('type')}")

            if event.get('type') == 'checkout.session.completed':
                session = event.get('data', {}).get('object', {})
                handle_checkout_session_completed(session)

            elif event.get('type') == 'payment_intent.succeeded':
                payment_intent = event.get('data', {}).get('object', {})
                handle_payment_intent_succeeded(payment_intent)

            elif event.get('type') == 'payment_intent.payment_failed':
                payment_intent = event.get('data', {}).get('object', {})
                handle_payment_intent_failed(payment_intent)

            return jsonify({'received': True})

        except Exception as e:
            print(f"Webhook error: {e}")
            return jsonify({'error': str(e)}), 400

    return app


def create_stripe_session(registration):
    """Create Stripe checkout session"""
    try:
        price = TICKET_PRICES.get(registration.get('ticket'), TICKET_PRICES['General'])

        line_items = [
            {
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f"{registration.get('ticket')} Ticket - Event Registration",
                        'description': f"Ticket Type: {registration.get('ticket')}",
                        'images': [
                            'https://via.placeholder.com/300x200?text=Event+Ticket',
                        ],
                    },
                    'unit_amount': price,
                },
                'quantity': 1,
            }
        ]

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            customer_email=registration.get('email'),
            metadata={
                'name': registration.get('name'),
                'email': registration.get('email'),
                'ticket_type': registration.get('ticket'),
                'dietary': registration.get('dietary', ''),
                'sessions': '|'.join(registration.get('sessions', [])),
            },
            success_url=f"{FRONTEND_URL}?payment=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}?payment=cancelled",
        )

        print(f"✓ Stripe session created: {session.id}")
        return session

    except Exception as e:
        print(f"Error creating Stripe session: {e}")
        raise


def handle_checkout_session_completed(session):
    """Handle checkout session completed"""
    try:
        metadata = session.get('metadata', {})

        # Create registration object from metadata
        registration = {
            'name': metadata.get('name'),
            'email': metadata.get('email'),
            'ticket': metadata.get('ticket_type'),
            'dietary': metadata.get('dietary', 'None'),
            'sessions': metadata.get('sessions', '').split('|'),
            'paymentStatus': 'Paid',
            'paymentMethod': 'stripe',
            'stripeSessionId': session.get('id'),
        }

        # Save registration to database
        saved_reg = save_registration(registration)
        print(f"✓ Registration saved for {saved_reg['name']}")

        # Send ticket email
        try:
            send_ticket_email(saved_reg)
        except Exception as e:
            print(f"Email error: {e}")

        return saved_reg

    except Exception as e:
        print(f"Error handling checkout completed: {e}")
        raise


def handle_payment_intent_succeeded(payment_intent):
    """Handle payment intent succeeded"""
    try:
        print(f"✓ Payment succeeded: {payment_intent.get('id')}")
    except Exception as e:
        print(f"Error handling payment success: {e}")


def handle_payment_intent_failed(payment_intent):
    """Handle payment intent failed"""
    try:
        print(f"✗ Payment failed: {payment_intent.get('id')}")
    except Exception as e:
        print(f"Error handling payment failure: {e}")
