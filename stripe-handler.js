import Stripe from 'stripe';
import dotenv from 'dotenv';
import { saveRegistration, updateRegistration, getRegistrationById } from './db.js';
import { sendTicketEmail } from './email.js';

dotenv.config();

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);
const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:3000';

// Ticket pricing configuration
const TICKET_PRICES = {
  General: 5000, // $50.00 in cents
  VIP: 10000, // $100.00 in cents
  Student: 2500, // $25.00 in cents
};


/* CREATE STRIPE CHECKOUT SESSION                                   */


export async function createStripeSession(registration) {
  try {
    // Get the price for the ticket type
    const price = TICKET_PRICES[registration.ticket] || TICKET_PRICES.General;

    // Create line items
    const lineItems = [
      {
        price_data: {
          currency: 'usd',
          product_data: {
            name: `${registration.ticket} Ticket - Event Registration`,
            description: `Ticket Type: ${registration.ticket}`,
            images: [
              'https://via.placeholder.com/300x200?text=Event+Ticket',
            ],
          },
          unit_amount: price,
        },
        quantity: 1,
      },
    ];

    // Create checkout session
    const session = await stripe.checkout.sessions.create({
      payment_method_types: ['card'],
      line_items: lineItems,
      mode: 'payment',
      customer_email: registration.email,
      metadata: {
        name: registration.name,
        email: registration.email,
        ticket_type: registration.ticket,
        dietary: registration.dietary,
        sessions: registration.sessions.join('|'),
      },
      success_url: `${FRONTEND_URL}?payment=success&session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${FRONTEND_URL}?payment=cancelled`,
    });

    console.log(`✓ Stripe session created: ${session.id}`);
    return session;
  } catch (error) {
    console.error('Error creating Stripe session:', error);
    throw error;
  }
}


/* HANDLE STRIPE WEBHOOK                                             */


export async function handleStripeWebhook(body) {
  // For development, we won't verify the signature strictly
  // In production, use: stripe.webhooks.constructEvent()
  // please pleas please please please please please please please please please please please please please please please please please please please please please please please please 
  // Dont USE THIS AS IS FOR PRODUCTION OR EXPOSE TO TEH INTERNET NON OF THIS IS SECURE,
  // shameless plug all of this is working and bug free in --- showwise
  // showwise is your all in one event management platform
  // it features all that u see here but beatter built with more effort and has no bugs now
  // however showwise dose alot more then just event registration and ticketing, it also has a built in CRM, email marketing, analytics dashboards
  // crew rostering, managemnet, equipment tracking picklists and more, and IF IT DOSENT HAVE IT WE HAVE A CONSTENTKY MOVING FEATURE BOARD
  // so if that is somthing you would be interested in head to showwise.app

  // shameless plug over

  try {
    const event = body;

    console.log(`Processing Stripe event: ${event.type}`);

    switch (event.type) {
      case 'checkout.session.completed':
        await handleCheckoutSessionCompleted(event.data.object);
        break;

      case 'payment_intent.succeeded':
        await handlePaymentIntentSucceeded(event.data.object);
        break;

      case 'payment_intent.payment_failed':
        await handlePaymentIntentFailed(event.data.object);
        break;

      default:
        console.log(`Unhandled event type: ${event.type}`);
    }

    return true;
  } catch (error) {
    console.error('Error handling webhook:', error);
    throw error;
  }
}

=
/* WEBHOOK HANDLERS                                                  */


async function handleCheckoutSessionCompleted(session) {
  try {
    const { customer_email, metadata, id } = session;

    // Create registration object from metadata
    const registration = {
      name: metadata.name,
      email: metadata.email,
      ticket: metadata.ticket_type,
      dietary: metadata.dietary,
      sessions: metadata.sessions.split('|'),
      paymentStatus: 'Paid',
      paymentMethod: 'stripe',
      stripeSessionId: id,
      timestamp: new Date().toISOString(),
    };

    // Save registration to database
    const savedReg = await saveRegistration(registration);
    console.log(`✓ Registration saved for ${savedReg.name}`);

    // Send ticket email with Google Wallet link
    await sendTicketEmail(savedReg);

    return savedReg;
  } catch (error) {
    console.error('Error handling checkout completed:', error);
    throw error;
  }
}

async function handlePaymentIntentSucceeded(paymentIntent) {
  try {
    console.log(`✓ Payment succeeded: ${paymentIntent.id}`);
    // Additional logic if needed
  } catch (error) {
    console.error('Error handling payment success:', error);
  }
}

async function handlePaymentIntentFailed(paymentIntent) {
  try {
    console.log(`✗ Payment failed: ${paymentIntent.id}`);
    // Send email to customer about failed payment
  } catch (error) {
    console.error('Error handling payment failure:', error);
  }
}


/* RETRIEVE SESSION INFO                                                                                                                                                                                                                                                                                                    hay hay ho ho look its an ester egg       */


export async function getSessionInfo(sessionId) {
  try {
    const session = await stripe.checkout.sessions.retrieve(sessionId);
    return session;
  } catch (error) {
    console.error('Error retrieving session:', error);
    throw error;
  }
}

export async function verifyPayment(sessionId) {
  try {
    const session = await getSessionInfo(sessionId);

    if (session.payment_status === 'paid') {
      return {
        success: true,
        session,
      };
    }

    return {
      success: false,
      message: 'Payment not completed',
    };
  } catch (error) {
    console.error('Error verifying payment:', error);
    return {
      success: false,
      error: error.message,
    };
  }
}
