/*Email Notifications with Google Wallet Support*/

import nodemailer from 'nodemailer';
import dotenv from 'dotenv';
import { generateGoogleWalletPass } from './google-wallet.js';

dotenv.config();

// Configure email transporter
const transporter = nodemailer.createTransport({
  service: process.env.EMAIL_SERVICE || 'gmail',
  auth: {
    user: process.env.EMAIL_USER,
    pass: process.env.EMAIL_PASSWORD,
  },
});

const EMAIL_FROM = process.env.EMAIL_FROM || process.env.EMAIL_USER;


/* SEND CONFIRMATION EMAIL */


export async function sendConfirmationEmail(registration) {
  try {
    const emailContent = generateConfirmationEmailHtml(registration);

    const mailOptions = {
      from: EMAIL_FROM,
      to: registration.email,
      subject: 'Registration confirmed',
      html: emailContent,
    };

    const info = await transporter.sendMail(mailOptions);
    console.log(`Confirmation email sent to ${registration.email}`);
    return info;
  } catch (error) {
    console.error('Error sending confirmation email:', error);
    throw error;
  }
}


/* SEND TICKET EMAIL WITH GOOGLE WALLET */


export async function sendTicketEmail(registration) {
  try {
    const emailContent = generateTicketEmailHtml(registration);

    const mailOptions = {
      from: EMAIL_FROM,
      to: registration.email,
      subject: `Your ${registration.ticket} ticket`,
      html: emailContent,
    };

    // Try to generate Google Wallet pass and attach it
    try {
      const googleWalletData = await generateGoogleWalletPass(registration);
      if (googleWalletData) {
        mailOptions.attachments = [
          {
            filename: `ticket-${registration.id}.pkpass`,
            content: Buffer.from(googleWalletData, 'base64'),
            contentType: 'application/vnd.apple.pkpass',
          },
        ];
      }
    } catch (walletError) {
      console.warn('Could not generate Google Wallet pass:', walletError.message);
      // Continue without attachment
    }

    const info = await transporter.sendMail(mailOptions);
    console.log(`Ticket email sent to ${registration.email}`);
    return info;
  } catch (error) {
    console.error('Error sending ticket email:', error);
    throw error;
  }
}

/* SEND ADMIN NOTIFICATION */


export async function sendAdminNotification(registration) {
  try {
    const adminEmails = process.env.ADMIN_EMAILS?.split(',') || [EMAIL_FROM];

    const emailContent = generateAdminNotificationHtml(registration);

    const mailOptions = {
      from: EMAIL_FROM,
      to: adminEmails.join(','),
      subject: `New Registration: ${registration.name}`,
      html: emailContent,
    };

    const info = await transporter.sendMail(mailOptions);
    console.log(`Admin notification sent`);
    return info;
  } catch (error) {
    console.error('Error sending admin notification:', error);
  }
}


/* EMAIL TEMPLATE GENERATORS */


function generateConfirmationEmailHtml(reg) {
  const date = new Date(reg.timestamp).toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

  return `
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="UTF-8">
        <style>
          body { font-family: Arial, sans-serif; color: #333; }
          .container { max-width: 600px; margin: 0 auto; }
          .header { background: #1f2937; color: white; padding: 20px; text-align: left; border-radius: 8px 8px 0 0; }
          .content { padding: 30px; border: 1px solid #ddd; }
          .info-box { background: #f5f3ee; padding: 15px; margin: 15px 0; border-radius: 5px; }
          .label { font-weight: bold; color: #5a5550; }
          .footer { text-align: center; padding: 20px; color: #999; font-size: 12px; border-top: 1px solid #ddd; }
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <h1>Registration confirmed</h1>
          </div>
          
          <div class="content">
            <p>Hi ${escapeHtml(reg.name)},</p>
            
            <p>Thanks for registering. Your spot is confirmed.</p>
            
            <div class="info-box">
              <p><span class="label">Registration ID:</span> ${reg.id}</p>
              <p><span class="label">Email:</span> ${escapeHtml(reg.email)}</p>
              <p><span class="label">Ticket Type:</span> ${reg.ticket}</p>
              <p><span class="label">Registered:</span> ${date}</p>
            </div>
            
            ${reg.dietary && reg.dietary !== 'None' ? `
              <p><span class="label">Dietary Requirements:</span> ${escapeHtml(reg.dietary)}</p>
            ` : ''}
            
            <p><strong>Selected Sessions:</strong></p>
            <ul>
              ${reg.sessions.map((session) => `<li>${escapeHtml(session)}</li>`).join('')}
            </ul>
            
            <p>You will receive your ticket details in a follow-up email.</p>
            
            <p>If anything looks incorrect, reply to this email and we will help.</p>
            
            <p>Kind regards,<br/>Event Team</p>
          </div>
          
          <div class="footer">
            <p>&copy; 2026 Event Team</p>
          </div>
        </div>
      </body>
    </html>
  `;
}

function generateTicketEmailHtml(reg) {
  const qrCodeUrl = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(reg.id)}`;

  return `
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="UTF-8">
        <style>
          body { font-family: Arial, sans-serif; color: #333; }
          .container { max-width: 600px; margin: 0 auto; }
          .ticket { background: linear-gradient(135deg, #c8441c 0%, #a5350f 100%); color: white; padding: 30px; border-radius: 8px; margin: 20px 0; }
          .ticket-header { font-size: 24px; font-weight: bold; margin-bottom: 10px; }
          .ticket-detail { display: flex; justify-content: space-between; margin: 10px 0; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.3); }
          .ticket-label { opacity: 0.9; }
          .ticket-value { font-weight: bold; }
          .qr-code { text-align: center; margin: 20px 0; }
          .content { padding: 30px; border: 1px solid #ddd; }
          .wallet-button { display: inline-block; background: #000; color: white; padding: 12px 24px; border-radius: 5px; margin: 10px 0; text-decoration: none; font-weight: bold; }
          .footer { text-align: center; padding: 20px; color: #999; font-size: 12px; }
        </style>
      </head>
      <body>
        <div class="container">
          <div class="content">
            <h1>Your ticket details</h1>
            <p>Hi <strong>${escapeHtml(reg.name)}</strong>,</p>
            <p>Here are your registration details:</p>
          </div>
          
          <div class="ticket">
            <div class="ticket-header">Ticket</div>
            <div class="ticket-detail">
              <span class="ticket-label">Name:</span>
              <span class="ticket-value">${escapeHtml(reg.name)}</span>
            </div>
            <div class="ticket-detail">
              <span class="ticket-label">Ticket Type:</span>
              <span class="ticket-value">${reg.ticket}</span>
            </div>
            <div class="ticket-detail">
              <span class="ticket-label">Ticket ID:</span>
              <span class="ticket-value">${reg.id.substring(0, 8).toUpperCase()}</span>
            </div>
            ${reg.dietary && reg.dietary !== 'None' ? `
              <div class="ticket-detail">
                <span class="ticket-label">Dietary:</span>
                <span class="ticket-value">${escapeHtml(reg.dietary)}</span>
              </div>
            ` : ''}
            
            <div class="qr-code">
              <p style="font-size: 12px; opacity: 0.9;">Show this QR code at entry:</p>
              <img src="${qrCodeUrl}" alt="Ticket QR Code" />
              <p style="font-size: 12px; opacity: 0.9;">${reg.id}</p>
            </div>
          </div>
          
          <div class="content">
            <p><strong>Wallet options:</strong></p>
            <p>
              <a href="#" class="wallet-button">Add to Apple Wallet</a><br>
              <a href="#" class="wallet-button">Add to Google Wallet</a>
            </p>
            
            <p><strong>Your Sessions:</strong></p>
            <ul>
              ${reg.sessions.map((session) => `<li>${escapeHtml(session)}</li>`).join('')}
            </ul>
            
            <p>See you soon.</p>
          </div>
          
          <div class="footer">
            <p>&copy; 2026 Event Team</p>
          </div>
        </div>
      </body>
    </html>
  `;
}

function generateAdminNotificationHtml(reg) {
  return `
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="UTF-8">
        <style>
          body { font-family: Arial, sans-serif; color: #333; }
          .container { max-width: 600px; margin: 0 auto; }
          .header { background: #1a1714; color: white; padding: 20px; text-align: center; }
          .content { padding: 20px; border: 1px solid #ddd; }
          table { width: 100%; border-collapse: collapse; margin: 15px 0; }
          td { padding: 8px; border-bottom: 1px solid #ddd; }
          .label { font-weight: bold; width: 150px; background: #f5f3ee; }
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <h2>New Registration Received</h2>
          </div>
          
          <div class="content">
            <table>
              <tr>
                <td class="label">Name:</td>
                <td>${escapeHtml(reg.name)}</td>
              </tr>
              <tr>
                <td class="label">Email:</td>
                <td>${escapeHtml(reg.email)}</td>
              </tr>
              <tr>
                <td class="label">Ticket Type:</td>
                <td>${reg.ticket}</td>
              </tr>
              <tr>
                <td class="label">Payment Status:</td>
                <td>${reg.paymentStatus}</td>
              </tr>
              <tr>
                <td class="label">Dietary:</td>
                <td>${reg.dietary || 'None'}</td>
              </tr>
              <tr>
                <td class="label">Sessions:</td>
                <td>${reg.sessions.join(', ')}</td>
              </tr>
              <tr>
                <td class="label">Timestamp:</td>
                <td>${new Date(reg.timestamp).toLocaleString()}</td>
              </tr>
            </table>
          </div>
        </div>
      </body>
    </html>
  `;
}


/* UTILITY FUNCTIONS  */


function escapeHtml(text) {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;',
  };
  return text.replace(/[&<>"']/g, (m) => map[m]);
}


/* TEST EMAIL SENDING                                                */


export async function testEmailConnection() {
  try {
    await transporter.verify();
    console.log('Email service connected and ready');
    return true;
  } catch (error) {
    console.error('Email service connection failed:', error);
    return false;
  }
}
