import dotenv from 'dotenv';
import pkg from 'pg';
import fs from 'fs';
import path from 'path';
import { createReadStream, createWriteStream } from 'fs';
import csv from 'csv-parser';
import { stringify } from 'csv-stringify';
import { v4 as uuidv4 } from 'uuid';
import { fileURLToPath } from 'url';

dotenv.config();

const { Pool } = pkg;
const __dirname = path.dirname(fileURLToPath(import.meta.url));

const DB_TYPE = process.env.DB_TYPE || 'csv';
const CSV_FILE_PATH = process.env.CSV_FILE_PATH || path.join(__dirname, 'data', 'registrations.csv');

let pool = null;

// Initialize PostgreSQL pool if needed
if (DB_TYPE === 'postgres') {
  pool = new Pool({
    host: process.env.DB_HOST,
    port: process.env.DB_PORT,
    database: process.env.DB_NAME,
    user: process.env.DB_USER,
    password: process.env.DB_PASSWORD,
  });

  pool.on('error', (err) => {
    console.error('Unexpected error on idle client', err);
  });
}


/* INITIALIZE DATABASE */


export async function initDb() {
  if (DB_TYPE === 'postgres') {
    await initPostgres();
  } else {
    await initCsv();
  }
  console.log(`Database initialized (${DB_TYPE.toUpperCase()})`);
}

async function initPostgres() {
  try {
    await pool.query(`
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
    `);

    console.log('PostgreSQL tables created');
  } catch (error) {
    console.error('Error initializing PostgreSQL:', error);
    throw error;
  }
}

async function initCsv() {
  const dir = path.dirname(CSV_FILE_PATH);

  // Create data directory if it doesn't exist
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }

  // Create CSV file with headers if it doesn't exist
  if (!fs.existsSync(CSV_FILE_PATH)) {
    const headers = [
      'id',
      'name',
      'email',
      'ticket',
      'dietary',
      'sessions',
      'paymentStatus',
      'paymentMethod',
      'timestamp',
    ];

    const csvWriter = createWriteStream(CSV_FILE_PATH, { flags: 'w' });
    csvWriter.write(headers.join(',') + '\n');
    csvWriter.end();

    console.log(`CSV file created at ${CSV_FILE_PATH}`);
  }
}


/* REGISTRATION CRUD OPERATIONS */


export async function saveRegistration(data) {
  const id = uuidv4();
  const registration = {
    id,
    ...data,
    sessions: Array.isArray(data.sessions) ? data.sessions.join('|') : data.sessions,
    timestamp: data.timestamp || new Date().toISOString(),
  };

  if (DB_TYPE === 'postgres') {
    return await saveRegistrationPostgres(registration);
  } else {
    return await saveRegistrationCsv(registration);
  }
}

async function saveRegistrationPostgres(reg) {
  const query = `
    INSERT INTO registrations 
    (id, name, email, ticket, dietary, sessions, payment_status, payment_method, timestamp)
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
    RETURNING *;
  `;

  const values = [
    reg.id,
    reg.name,
    reg.email,
    reg.ticket,
    reg.dietary,
    reg.sessions,
    reg.paymentStatus,
    reg.paymentMethod,
    reg.timestamp,
  ];

  const result = await pool.query(query, values);
  const row = result.rows[0];

  return {
    ...row,
    sessions: row.sessions.split('|'),
  };
}

async function saveRegistrationCsv(reg) {
  return new Promise((resolve, reject) => {
    const data = [
      reg.id,
      reg.name,
      reg.email,
      reg.ticket,
      reg.dietary,
      reg.sessions,
      reg.paymentStatus,
      reg.paymentMethod,
      reg.timestamp,
    ];

    stringify([data], {}, (err, output) => {
      if (err) return reject(err);

      fs.appendFile(CSV_FILE_PATH, output, (err) => {
        if (err) return reject(err);

        resolve({
          id: reg.id,
          name: reg.name,
          email: reg.email,
          ticket: reg.ticket,
          dietary: reg.dietary,
          sessions: reg.sessions.split('|'),
          paymentStatus: reg.paymentStatus,
          paymentMethod: reg.paymentMethod,
          timestamp: reg.timestamp,
        });
      });
    });
  });
}


/* FETCH REGISTRATIONS */


export async function getRegistrations() {
  if (DB_TYPE === 'postgres') {
    return await getRegistrationsPostgres();
  } else {
    return await getRegistrationsCsv();
  }
}

async function getRegistrationsPostgres() {
  const result = await pool.query('SELECT * FROM registrations ORDER BY timestamp DESC;');

  return result.rows.map((row) => ({
    ...row,
    sessions: row.sessions.split('|'),
    paymentStatus: row.payment_status,
    paymentMethod: row.payment_method,
  }));
}

async function getRegistrationsCsv() {
  return new Promise((resolve, reject) => {
    const registrations = [];

    if (!fs.existsSync(CSV_FILE_PATH)) {
      resolve([]);
      return;
    }

    createReadStream(CSV_FILE_PATH)
      .pipe(csv())
      .on('data', (row) => {
        registrations.push({
          id: row.id,
          name: row.name,
          email: row.email,
          ticket: row.ticket,
          dietary: row.dietary,
          sessions: row.sessions.split('|').filter((s) => s),
          paymentStatus: row.paymentStatus,
          paymentMethod: row.paymentMethod,
          timestamp: row.timestamp,
        });
      })
      .on('end', () => {
        resolve(registrations.reverse()); // Most recent first
      })
      .on('error', reject);
  });
}

/*  ────────────────── */
/* FETCH SINGLE REGISTRATION                                         */
/*  ────────────────── */

export async function getRegistrationById(id) {
  if (DB_TYPE === 'postgres') {
    return await getRegistrationByIdPostgres(id);
  } else {
    return await getRegistrationByIdCsv(id);
  }
}

async function getRegistrationByIdPostgres(id) {
  const result = await pool.query('SELECT * FROM registrations WHERE id = $1;', [id]);

  if (result.rows.length === 0) return null;

  const row = result.rows[0];
  return {
    ...row,
    sessions: row.sessions.split('|'),
    paymentStatus: row.payment_status,
    paymentMethod: row.payment_method,
  };
}

async function getRegistrationByIdCsv(id) {
  const registrations = await getRegistrationsCsv();
  return registrations.find((r) => r.id === id) || null;
}


/* UPDATE REGISTRATION     */


export async function updateRegistration(id, updates) {
  if (DB_TYPE === 'postgres') {
    return await updateRegistrationPostgres(id, updates);
  } else {
    return await updateRegistrationCsv(id, updates);
  }
}

async function updateRegistrationPostgres(id, updates) {
  const fields = [];
  const values = [];
  let paramCount = 1;

  // Build dynamic UPDATE query
  if (updates.name) {
    fields.push(`name = $${paramCount}`);
    values.push(updates.name);
    paramCount++;
  }
  if (updates.email) {
    fields.push(`email = $${paramCount}`);
    values.push(updates.email);
    paramCount++;
  }
  if (updates.ticket) {
    fields.push(`ticket = $${paramCount}`);
    values.push(updates.ticket);
    paramCount++;
  }
  if (updates.dietary) {
    fields.push(`dietary = $${paramCount}`);
    values.push(updates.dietary);
    paramCount++;
  }
  if (updates.sessions) {
    fields.push(`sessions = $${paramCount}`);
    values.push(
      Array.isArray(updates.sessions) ? updates.sessions.join('|') : updates.sessions
    );
    paramCount++;
  }
  if (updates.paymentStatus) {
    fields.push(`payment_status = $${paramCount}`);
    values.push(updates.paymentStatus);
    paramCount++;
  }

  if (fields.length === 0) {
    return await getRegistrationByIdPostgres(id);
  }

  fields.push(`updated_at = CURRENT_TIMESTAMP`);
  values.push(id);

  const query = `UPDATE registrations SET ${fields.join(', ')} WHERE id = $${paramCount} RETURNING *;`;

  const result = await pool.query(query, values);

  if (result.rows.length === 0) return null;

  const row = result.rows[0];
  return {
    ...row,
    sessions: row.sessions.split('|'),
    paymentStatus: row.payment_status,
    paymentMethod: row.payment_method,
  };
}

async function updateRegistrationCsv(id, updates) {
  const registrations = await getRegistrationsCsv();
  const index = registrations.findIndex((r) => r.id === id);

  if (index === -1) return null;

  // Update the registration
  registrations[index] = {
    ...registrations[index],
    ...updates,
  };

  // Rewrite the entire CSV
  await writeCsvFile(registrations);

  return registrations[index];
}


/* DELETE REGISTRATION  */


export async function deleteRegistration(id) {
  if (DB_TYPE === 'postgres') {
    return await deleteRegistrationPostgres(id);
  } else {
    return await deleteRegistrationCsv(id);
  }
}

async function deleteRegistrationPostgres(id) {
  const result = await pool.query('DELETE FROM registrations WHERE id = $1 RETURNING id;', [id]);
  return result.rows.length > 0;
}

async function deleteRegistrationCsv(id) {
  const registrations = await getRegistrationsCsv();
  const filtered = registrations.filter((r) => r.id !== id);

  if (filtered.length === registrations.length) {
    return false; // Not found
  }

  await writeCsvFile(filtered);
  return true;
}


/* CSV UTILITY FUNCTIONS    */


async function writeCsvFile(registrations) {
  return new Promise((resolve, reject) => {
    const data = registrations.map((r) => [
      r.id,
      r.name,
      r.email,
      r.ticket,
      r.dietary,
      Array.isArray(r.sessions) ? r.sessions.join('|') : r.sessions,
      r.paymentStatus,
      r.paymentMethod,
      r.timestamp,
    ]);

    const headers = [
      'id',
      'name',
      'email',
      'ticket',
      'dietary',
      'sessions',
      'paymentStatus',
      'paymentMethod',
      'timestamp',
    ];

    stringify(data, { header: false }, (err, output) => {
      if (err) return reject(err);

      const csvContent = headers.join(',') + '\n' + output;

      fs.writeFile(CSV_FILE_PATH, csvContent, (err) => {
        if (err) return reject(err);
        resolve();
      });
    });
  });
}


/* ADMIN USER CRUD (PostgreSQL only for now, verry sad ik but what ya gona do, fight me about it, aslo u think i have time to do this look at how extra i went already)   */


export async function saveAdminUser(username, passwordHash) {
  if (DB_TYPE !== 'postgres') {
    throw new Error('Admin users only supported with PostgreSQL');
  }

  const query = `
    INSERT INTO admin_users (username, password_hash)
    VALUES ($1, $2)
    RETURNING id, username;
  `;

  const result = await pool.query(query, [username, passwordHash]);
  return result.rows[0];
}

export async function getAdminUserByUsername(username) {
  if (DB_TYPE !== 'postgres') {
    return null;
  }

  const query = 'SELECT * FROM admin_users WHERE username = $1;';
  const result = await pool.query(query, [username]);

  return result.rows[0] || null;
}

export async function closeDb() {
  if (pool) {
    await pool.end();
  }
}
