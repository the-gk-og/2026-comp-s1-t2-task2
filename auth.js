/* ── Authentication Module for Admin Panel ──────────────────────── */

import dotenv from 'dotenv';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import { saveAdminUser, getAdminUserByUsername } from './db.js';

dotenv.config();

const JWT_SECRET = process.env.JWT_SECRET || 'your_super_secret_key_change_this';
const JWT_EXPIRY = '24h';

/* ────────────────────────────────────────────────────────────────── */
/* LOGIN ADMIN USER                                                  */
/* ────────────────────────────────────────────────────────────────── */

export async function loginAdmin(username, password) {
  try {
    // Get user from database
    const user = await getAdminUserByUsername(username);

    if (!user) {
      throw new Error('User not found');
    }

    // Compare passwords
    const isPasswordValid = await bcrypt.compare(password, user.password_hash);

    if (!isPasswordValid) {
      throw new Error('Invalid password');
    }

    // Generate JWT token
    const token = jwt.sign(
      {
        userId: user.id,
        username: user.username,
      },
      JWT_SECRET,
      { expiresIn: JWT_EXPIRY }
    );

    console.log(`✓ Admin user ${username} logged in`);
    return token;
  } catch (error) {
    console.error('Login error:', error);
    throw error;
  }
}

/* ────────────────────────────────────────────────────────────────── */
/* CREATE ADMIN USER                                                 */
/* ────────────────────────────────────────────────────────────────── */

export async function createAdminUser(username, password) {
  try {
    // Check if user already exists
    const existingUser = await getAdminUserByUsername(username);

    if (existingUser) {
      throw new Error('User already exists');
    }

    // Hash password
    const saltRounds = 10;
    const passwordHash = await bcrypt.hash(password, saltRounds);

    // Save user to database
    const user = await saveAdminUser(username, passwordHash);

    console.log(`✓ Admin user ${username} created`);
    return user;
  } catch (error) {
    console.error('Error creating admin user:', error);
    throw error;
  }
}

/* ────────────────────────────────────────────────────────────────── */
/* VERIFY JWT TOKEN MIDDLEWARE                                       */
/* ────────────────────────────────────────────────────────────────── */

export function verifyToken(req, res, next) {
  try {
    const token = req.headers.authorization?.split(' ')[1];

    if (!token) {
      return res.status(401).json({ error: 'No token provided' });
    }

    const decoded = jwt.verify(token, JWT_SECRET);
    req.user = decoded;
    next();
  } catch (error) {
    console.error('Token verification error:', error);
    res.status(401).json({ error: 'Invalid or expired token' });
  }
}

/* ────────────────────────────────────────────────────────────────── */
/* DECODE TOKEN (for frontend validation)                            */
/* ────────────────────────────────────────────────────────────────── */

export function decodeToken(token) {
  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    return {
      valid: true,
      user: decoded,
    };
  } catch (error) {
    return {
      valid: false,
      error: error.message,
    };
  }
}

/* ────────────────────────────────────────────────────────────────── */
/* GENERATE DEFAULT ADMIN CREDENTIALS                                */
/* ────────────────────────────────────────────────────────────────── */

export async function generateDefaultAdmin() {
  try {
    const defaultUsername = 'admin';
    const defaultPassword = 'admin123'; // CHANGE THIS IN PRODUCTION!

    // Check if default admin already exists
    const existingAdmin = await getAdminUserByUsername(defaultUsername);

    if (existingAdmin) {
      console.log('ℹ️  Default admin already exists');
      return existingAdmin;
    }

    // Create default admin
    const admin = await createAdminUser(defaultUsername, defaultPassword);

    console.log('⚠️  DEFAULT ADMIN CREATED:');
    console.log(`   Username: ${defaultUsername}`);
    console.log(`   Password: ${defaultPassword}`);
    console.log('   ⚠️  CHANGE THE PASSWORD IMMEDIATELY!');

    return admin;
  } catch (error) {
    console.error('Error generating default admin:', error);
  }
}
