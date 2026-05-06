/* ── RSVP Event Registration System — Backend Server ───────────────── */

import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import bodyParser from 'body-parser';
import Stripe from 'stripe';
import path from 'path';
import { fileURLToPath } from 'url';

// Load environment variables
dotenv.config();

// Import routes and utilities
import { initDb, saveRegistration, getRegistrations, updateRegistration, deleteRegistration, getRegistrationById } from './db.js';
import { sendConfirmationEmail, sendTicketEmail } from './email.js';
import { createStripeSession, handleStripeWebhook } from './stripe-handler.js';
import { loginAdmin, verifyToken, createAdminUser } from './auth.js';

// Get __dirname equivalent in ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Initialize Express app
const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

// Serve static files
app.use(express.static(__dirname));

// Initialize database
await initDb();

/* ────────────────────────────────────────────────────────────────── */
/* API ROUTES                                                         */
/* ────────────────────────────────────────────────────────────────── */

/**
 * GET /api/registrations
 * Fetch all registrations (with optional filtering)
 */
app.get('/api/registrations', async (req, res) => {
  try {
    const registrations = await getRegistrations();
    res.json(registrations);
  } catch (error) {
    console.error('Error fetching registrations:', error);
    res.status(500).json({ error: 'Failed to fetch registrations' });
  }
});

/**
 * GET /api/registrations/:id
 * Fetch a single registration by ID
 */
app.get('/api/registrations/:id', async (req, res) => {
  try {
    const registration = await getRegistrationById(req.params.id);
    if (!registration) {
      return res.status(404).json({ error: 'Registration not found' });
    }
    res.json(registration);
  } catch (error) {
    console.error('Error fetching registration:', error);
    res.status(500).json({ error: 'Failed to fetch registration' });
  }
});

/**
 * POST /api/registrations
 * Create a new registration and initialize payment
 */
app.post('/api/registrations', async (req, res) => {
  try {
    const { name, email, ticket, dietary, sessions, paymentMethod } = req.body;

    // Validate required fields
    if (!name || !email || !ticket || !sessions || sessions.length === 0) {
      return res.status(400).json({ error: 'Missing required fields' });
    }

    // Create registration object
    const registration = {
      name,
      email,
      ticket,
      dietary: dietary || 'None',
      sessions,
      paymentStatus: paymentMethod === 'stripe' ? 'Pending' : 'Paid',
      paymentMethod: paymentMethod || 'cash',
      timestamp: new Date().toISOString(),
    };

    // If Stripe payment is requested, create checkout session
    if (paymentMethod === 'stripe') {
      const stripeSession = await createStripeSession(registration);
      return res.json({
        success: true,
        message: 'Stripe session created',
        redirectUrl: stripeSession.url,
      });
    }

    // Save registration directly if not using Stripe
    const savedReg = await saveRegistration(registration);

    // Send confirmation email
    await sendConfirmationEmail(savedReg);

    res.json({
      success: true,
      message: 'Registration created successfully',
      registration: savedReg,
    });
  } catch (error) {
    console.error('Error creating registration:', error);
    res.status(500).json({ error: 'Failed to create registration' });
  }
});

/**
 * PUT /api/registrations/:id
 * Update an existing registration
 */
app.put('/api/registrations/:id', async (req, res) => {
  try {
    const { name, email, ticket, dietary, sessions, paymentStatus } = req.body;
    const id = req.params.id;

    const updatedReg = await updateRegistration(id, {
      name,
      email,
      ticket,
      dietary,
      sessions,
      paymentStatus,
    });

    if (!updatedReg) {
      return res.status(404).json({ error: 'Registration not found' });
    }

    res.json({
      success: true,
      message: 'Registration updated successfully',
      registration: updatedReg,
    });
  } catch (error) {
    console.error('Error updating registration:', error);
    res.status(500).json({ error: 'Failed to update registration' });
  }
});

/**
 * DELETE /api/registrations/:id
 * Delete a registration
 */
app.delete('/api/registrations/:id', async (req, res) => {
  try {
    const success = await deleteRegistration(req.params.id);

    if (!success) {
      return res.status(404).json({ error: 'Registration not found' });
    }

    res.json({
      success: true,
      message: 'Registration deleted successfully',
    });
  } catch (error) {
    console.error('Error deleting registration:', error);
    res.status(500).json({ error: 'Failed to delete registration' });
  }
});

/* ────────────────────────────────────────────────────────────────── */
/* STRIPE WEBHOOK                                                    */
/* ────────────────────────────────────────────────────────────────── */

app.post('/webhook/stripe', async (req, res) => {
  try {
    await handleStripeWebhook(req.body);
    res.json({ received: true });
  } catch (error) {
    console.error('Webhook error:', error);
    res.status(400).json({ error: error.message });
  }
});

/* ────────────────────────────────────────────────────────────────── */
/* ADMIN AUTHENTICATION ROUTES                                       */
/* ────────────────────────────────────────────────────────────────── */

/**
 * POST /api/admin/login
 * Admin login endpoint
 */
app.post('/api/admin/login', async (req, res) => {
  try {
    const { username, password } = req.body;

    if (!username || !password) {
      return res.status(400).json({ error: 'Missing username or password' });
    }

    const token = await loginAdmin(username, password);
    res.json({ success: true, token });
  } catch (error) {
    console.error('Login error:', error);
    res.status(401).json({ error: 'Invalid credentials' });
  }
});

/**
 * POST /api/admin/create-user
 * Create a new admin user (protected route)
 */
app.post('/api/admin/create-user', verifyToken, async (req, res) => {
  try {
    const { username, password } = req.body;

    if (!username || !password) {
      return res.status(400).json({ error: 'Missing username or password' });
    }

    const user = await createAdminUser(username, password);
    res.json({ success: true, message: 'Admin user created', username: user.username });
  } catch (error) {
    console.error('Error creating admin user:', error);
    res.status(400).json({ error: error.message });
  }
});

/* ────────────────────────────────────────────────────────────────── */
/* ADMIN DASHBOARD ROUTES (Protected)                                 */
/* ────────────────────────────────────────────────────────────────── */

/**
 * GET /admin
 * Serve admin dashboard (protected by middleware on frontend)
 */
app.get('/admin', (req, res) => {
  res.sendFile(path.join(__dirname, 'admin.html'));
});

/* ────────────────────────────────────────────────────────────────── */
/* EMAIL RESEND ROUTE                                                 */
/* ────────────────────────────────────────────────────────────────── */

/**
 * POST /api/resend-email/:id
 * Resend ticket email to an attendee
 */
app.post('/api/resend-email/:id', async (req, res) => {
  try {
    const registration = await getRegistrationById(req.params.id);

    if (!registration) {
      return res.status(404).json({ error: 'Registration not found' });
    }

    await sendTicketEmail(registration);

    res.json({
      success: true,
      message: 'Ticket email sent successfully',
    });
  } catch (error) {
    console.error('Error sending email:', error);
    res.status(500).json({ error: 'Failed to send email' });
  }
});

/* ────────────────────────────────────────────────────────────────── */
/* HEALTH CHECK                                                       */
/* ────────────────────────────────────────────────────────────────── */

app.get('/api/health', (req, res) => {
  res.json({ status: 'Server is running', timestamp: new Date().toISOString() });
});

/* ────────────────────────────────────────────────────────────────── */
/* START SERVER                                                       */
/* ────────────────────────────────────────────────────────────────── */

app.listen(PORT, () => {
  console.log(`🎫 RSVP Event Registration Server running on http://localhost:${PORT}`);
  console.log(`📊 Admin Dashboard: http://localhost:${PORT}/admin`);
  console.log(`🗄️  Database Type: ${process.env.DB_TYPE}`);
});
