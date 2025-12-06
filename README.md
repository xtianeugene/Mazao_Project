# Mazao_Project


Mazao Project 🌱💰

A beginner-friendly Django-based farm produce marketplace with M-Pesa integration for seamless payments.

📋 Project Overview

Mazao is a web application that allows farmers to list their agricultural products and buyers to browse and purchase fresh produce directly from the source. The platform integrates M-Pesa payments via Safaricom's Daraja API for secure and convenient mobile money transactions.

The project is built on the Django framework and is designed to bring significant impact to the following Sustainable Development Goals (SDGs):

SDG 1: No Poverty

SDG 2: Zero Hunger

SDG 8: Decent Work and Economic Growth

🚀 Features

Core Features;

* User Management: Registration and login for farmers, buyers, and transporters

* Product Listings: Farmers can list their produce with details, prices, and images

* Browse & Search: Buyers can search, filter, and view available produce

* Order Management: Complete order lifecycle from cart to delivery

M-Pesa Integration;

* STK Push: Initiate payments directly to customer's phone

* Payment Confirmation: Real-time payment status updates

* Transaction History: Track all M-Pesa transactions

* Payment Security: Secure callback handling and validation

Additional Features;

* Shopping Cart: Add multiple products to cart

* Order Tracking: Track order status from purchase to delivery

* User Profiles: Complete profiles with verification badges

* Responsive Design: Mobile-first responsive interface

Tech Stack

* Backend
Framework: Django 4.x

* Database: SQLite (development)

* API: Django REST Framework (for future API expansion)

* Payments: Safaricom Daraja API v2

Frontend

* HTML/CSS: Bootstrap 5 for responsive design

* JavaScript: Vanilla JS with AJAX for M-Pesa integration

* Templates: Django Template Language

APIs & Services;

* M-Pesa Daraja API: For STK Push and payment processing

* B2C/B2B APIs: For future expansion (payouts to farmers)

📁 Project Structure


Mazao_Project/
├── mazao_app/     # Django project configuration
├── core/          # Homepage, about, contact pages
├── products/      # Product catalog and management
├── users/         # Authentication and user profiles
├── payments/      # M-Pesa integration and payment processing
├── orders/        # Order management and tracking
├── utils/         # Shared utilities and constants
└── [static, media, templates] # Frontend assets

Quick Start

Prerequisites;

* Python 3.8 or higher

* pip (Python package manager)

* Safaricom Daraja API credentials (for M-Pesa integration)

Installation Steps;

Clone the repository

    git clone <repository-url>
    cd Mazao_Project

Create and activate virtual environment

    python -m venv venv
    venv\Scripts\activate

Install dependencies

    pip install -r requirements.txt

Configure M-Pesa Daraja API

* Visit Safaricom Developer Portal

* Create an app to get credentials

* Copy .env.example to .env and add your credentials

* Set environment variables

    cp .env.example .env

Edit .env with your settings:

1. M-Pesa credentials
2. Database configuration
3. Django secret key

Run migrations

    python manage.py migrate

Create superuser

    python manage.py createsuperuser

Run development server

    python manage.py runserver

Visit the application

Open browser: http://127.0.0.1:8000/

Admin panel: http://127.0.0.1:8000/admin/

Requirements

Create requirements.txt with:

    # Django Framework
    Django==4.2.7
    
    # Database
    psycopg2-binary==2.9.7  # For PostgreSQL
    
    # Image Processing
    Pillow==10.0.0
    
    # Environment Variables
    python-dotenv==1.0.0
    
    # HTTP Requests (for M-Pesa API)
    requests==2.31.0
    
    # Security
    cryptography==41.0.7
    
    # Date/Time
    python-dateutil==2.8.2
    
    # API Development (optional)
    djangorestframework==3.14.0
    django-cors-headers==4.2.0


M-Pesa Configuration

Daraja API Credentials

Add these to your .env file:

    # M-Pesa Daraja API Credentials
    MPESA_CONSUMER_KEY=your_consumer_key
    MPESA_CONSUMER_SECRET=your_consumer_secret
    MPESA_SHORTCODE=your_business_shortcode
    MPESA_PASSKEY=your_passkey
    MPESA_CALLBACK_URL=https://yourdomain.com/api/payments/callback/
    MPESA_ENVIRONMENT=sandbox  # sandbox or production

Test Credentials (Sandbox)
For testing, you can use:

Test phone numbers: 2547xxxxxxxx (Safaricom numbers)

Test amount: KES 1-1000

Use Daraja API sandbox credentials from developer portal

Database Models

Core Models;

* User: Extended Django user with farmer/buyer roles

* Product: Agricultural produce with details and pricing

* Order: Purchase orders with status tracking

* Payment: M-Pesa transaction records

* Transaction: Detailed payment transactions

Payment Flow

1. User adds products to cart
2. User initiates checkout
3. System generates payment request
4. M-Pesa STK Push sent to user's phone
5. User enters PIN on phone
6. Callback received and order confirmed

Security Features

* M-Pesa Security: HTTPS callbacks, transaction validation

* Django Security: CSRF protection, XSS prevention

* Data Protection: Encrypted sensitive data

* Input Validation: Sanitized user inputs

Frontend Features

* Payment Modal: Clean M-Pesa payment interface

* Real-time Updates: AJAX-based payment status updates

* Responsive Design: Works on all devices

* Loading States: Visual feedback during payment processing

API Endpoints

Payment Endpoints

* POST /api/payments/initiate/ - Initiate M-Pesa payment

* POST /api/payments/callback/ - M-Pesa callback handler

* GET /api/payments/status/<transaction_id>/ - Check payment status

Acknowledgments

Safaricom PLC for the Daraja API

Django community for excellent documentation

Bootstrap team for frontend components

Support

For issues:

Check the troubleshooting section

Review Daraja API documentation

Open a GitHub issue with details

Include error logs and steps to reproduce


