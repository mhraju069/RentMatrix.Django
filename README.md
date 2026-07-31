# 🏠 RentMatrix — Property Rental Backend API

A production-ready **Django REST Framework** backend for a multi-currency property rental platform. Built to power Flutter/mobile apps with full booking lifecycle management, dynamic pricing, push notifications, and real-time currency conversion.

---

## 📋 Table of Contents

- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Environment Variables](#-environment-variables)
- [API Overview](#-api-overview)
  - [Authentication](#authentication-authapiv1)
  - [Property](#property-propertyapiv1)
  - [Booking](#booking-bookingapiv1)
  - [Notifications](#notifications-notifyapiv1)
  - [Others](#others-otherapiv1)
- [Pricing Engine](#-pricing-engine)
- [Multi-Currency System](#-multi-currency-system)
- [Push Notifications](#-push-notifications)
- [Admin Panel](#-admin-panel)
- [API Documentation](#-api-documentation)

---

## ✨ Features

- **JWT Authentication** — Secure login, OTP verification, and token refresh
- **Role-Based Access** — Separate flows for property owners and guests
- **Dynamic Pricing Engine** — Multi-layer pricing with surcharges, add-ons, and discounts
- **Multi-Currency Support** — All prices stored in USD, dynamically converted per user preference
- **Real-Time Booking** — Full booking lifecycle: PENDING → CONFIRMED → CHECKED_IN → CHECKED_OUT
- **Booking Date Validation** — Prevents overlapping bookings automatically
- **Push Notifications** — Firebase FCM integration for booking events and announcements
- **Response Translation Middleware** — Multilingual API message support (EN/AR)
- **Property Reviews & Ratings** — Dynamic rating-based surcharge system
- **Favourites & Reports** — Guest-facing property interaction features
- **Swagger / ReDoc API Docs** — Auto-generated interactive documentation
- **Unfold Admin Panel** — Modern Django admin UI

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| **Framework** | Django 5.x + Django REST Framework |
| **Auth** | JWT via `djangorestframework-simplejwt` |
| **API Docs** | `drf-spectacular` (Swagger + ReDoc) |
| **Push Notifications** | Firebase Admin SDK (FCM) |
| **Email** | SMTP (configurable via env) |
| **Database** | SQLite (dev) / PostgreSQL (prod) |
| **Admin UI** | `django-unfold` |
| **Media Storage** | Django FileSystemStorage + WhiteNoise |

---

## 📁 Project Structure

```
Rent/
├── config/
│   ├── settings.py          # Django settings
│   ├── api.py               # Root URL configuration
│   ├── wsgi.py
│   └── asgi.py
│
├── apps/
│   ├── auth/                # User auth, OTP, documents
│   ├── property/            # Property listings, amenities, reviews
│   ├── booking/             # Booking creation, pricing engine
│   ├── notify/              # Push notifications, announcements
│   └── others/              # Currency, language, user preferences
│
├── media/                   # Uploaded files (images, documents)
├── static/                  # Static assets
├── firebase-key.json        # Firebase credentials (not committed)
├── manage.py
├── .env                     # Local environment variables
└── .env-demo                # Example env template
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- pip
- Firebase project with a service account key

### 1. Clone the repository
```bash
git clone <repo-url>
cd Rent
```

### 2. Create and activate virtual environment
```bash
python -m venv env
source env/bin/activate      # Linux/macOS
env\Scripts\activate         # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment
```bash
cp .env-demo .env
# Edit .env with your values (see Environment Variables section)
```

### 5. Add Firebase credentials
Place your Firebase service account JSON file at the project root:
```
Rent/firebase-key.json
```

### 6. Run database migrations
```bash
python manage.py migrate
```

### 7. Create a superuser
```bash
python manage.py createsuperuser
```

### 8. Start the development server
```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000`.

---

## 🔐 Environment Variables

Copy `.env-demo` to `.env` and fill in the values:

```env
# PostgreSQL
PSQL=True
DB_NAME=your-db-name
DB_USER=your-db-user
DB_PASSWORD=your-db-password
DB_HOST=your-db-host
DB_PORT=your-db-port

# Email (SMTP)
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=your@email.com
EMAIL_HOST_PASSWORD=your_password
DEFAULT_FROM_EMAIL=your@email.com

# JWT Token Lifetimes (in seconds)
ACCESS_TOKEN_LIFETIME=604800     # 7 days
REFRESH_TOKEN_LIFETIME=2592000   # 30 days

# CORS & CSRF
CSRF_TRUSTED_ORIGINS=https://yourdomain.com
CSRF_ALLOW_ORIGINS=https://yourdomain.com

# Backend Base URL
BACKEND_URI=https://yourdomain.com


```

---

## 📡 API Overview

All endpoints return a consistent JSON envelope:
```json
{
  "status": 200,
  "success": true,
  "message": "...",
  "data": { ... }
}
```

JWT token must be included in the `Authorization` header:
```
Authorization: Bearer <access_token>
```

---

### Authentication (`/auth/api/v1/`)

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | `/register/` | Register a new user | ❌ |
| POST | `/login/` | Login and get JWT tokens | ❌ |
| POST | `/otp/verify/` | Verify OTP for email confirmation | ❌ |
| POST | `/otp/resend/` | Resend OTP | ❌ |
| GET | `/profile/` | Get current user profile | ✅ |
| PUT/PATCH | `/profile/update/` | Update profile | ✅ |
| POST | `/document/upload/` | Upload identity documents | ✅ |
| GET | `/document/list/` | List uploaded documents | ✅ |

---

### Property (`/property/api/v1/`)

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/list/` | List all verified properties | ❌ |
| GET | `/detail/<id>/` | Property detail with all fields | ❌ |
| POST | `/create/` | Create a new property (owner) | ✅ |
| PUT/PATCH | `/update/<id>/` | Update property | ✅ |
| DELETE | `/delete/<id>/` | Delete property | ✅ |
| GET | `/owner/list/` | Owner's own property listings | ✅ |
| POST | `/review/create/` | Submit a review | ✅ |
| GET | `/review/list/<id>/` | List reviews for a property | ❌ |
| POST | `/favourite/toggle/` | Toggle favourite | ✅ |
| GET | `/favourite/list/` | List favourited properties | ✅ |
| POST | `/report/` | Report a property | ✅ |

#### Property Pricing Fields (set by owner)

| Field | Type | Description |
|---|---|---|
| `price_daily` | Decimal (USD) | Per-day base price |
| `price_monthly` | Decimal (USD) | Per-month base price |
| `discount` | Integer | Discount % on base price |
| `rating_threshold` | Decimal | Min avg rating to apply surcharge |
| `rating_surcharge_percent` | Decimal | Extra % charged when rating threshold is met |
| Other Charges | Flat USD amount | e.g. Cleaning, Service Fee |
| Add-ons | Flat USD amount | Optional guest-selected services |
| Vacation Surcharge | % of base price | Applied for specific months |
| Weekend Surcharge | % of base price | Applied for specific days of week |

---

### Booking (`/booking/api/v1/`)

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/guest/booking/calculate-price/` | Preview price breakdown before booking | ❌ |
| POST | `/guest/booking/` | Create a new booking | ✅ |
| GET | `/guest/booking/` | List guest's own bookings | ✅ |
| GET | `/guest/booking/<id>/` | Booking detail with full price breakdown | ✅ |
| GET | `/owner/booking/` | List bookings for owner's properties | ✅ |
| POST | `/owner/booking/<id>/confirm/` | Confirm a booking | ✅ |
| POST | `/owner/booking/<id>/decline/` | Decline a booking | ✅ |

#### Calculate Price API

```
GET /booking/api/v1/guest/booking/calculate-price/
    ?property_id=<uuid>
    &price_type=daily          # or monthly
    &start_date=2026-08-01
    &end_date=2026-08-05
    &selected_addon_ids=79,80  # comma-separated, or [79,80]
```

**Response:**
```json
{
  "success": true,
  "price_type": "daily",
  "total_duration": 4,
  "base_unit_price": 100.08,
  "breakdown": {
    "base_price_total": 400.32,
    "other_charges": [
      { "name": "sea_view", "amount": 10.11, "total_amount": 40.44 }
    ],
    "other_charges_total": 40.44,
    "add_ons": [
      { "name": "Wifi Premium", "amount": 5.06, "total_amount": 20.24 }
    ],
    "add_ons_total": 20.24,
    "vacation_surcharge_total": 0.0,
    "weekend_surcharge_total": 0.0,
    "rating_surcharge_total": 15.01,
    "discount_total": 40.03,
    "total_amount_before_discount": 475.77
  },
  "unit_price_after_discount": 108.94,
  "total_price": 435.74,
  "currency_code": "EGP",
  "currency_symbol": "E£"
}
```

#### Create Booking API

**JSON format:**
```json
{
  "property": "7de71e0e-8785-44f2-9ca1-99e8a67872d3",
  "name": "John Doe",
  "phone": "01700000000",
  "email": "guest@example.com",
  "guest_count": 2,
  "check_in": "2026-08-01",
  "check_out": "2026-08-05",
  "price_type": "daily",
  "selected_addon_ids": [79, 80]
}
```

> **Note for Flutter Devs:** `selected_addon_ids` accepts any of these formats: `[79,80]` (array), `"79,80"` (string), or `"[79, 80]"` (JSON string). All are handled correctly by the backend.

---

### Notifications (`/notify/api/v1/`)

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | `/device-token/register/` | Register FCM device token | ✅ |
| GET | `/list/` | List user notifications | ✅ |
| POST | `/mark-read/<id>/` | Mark notification as read | ✅ |
| GET/PUT | `/settings/` | Get/update notification preferences | ✅ |

---

### Others (`/others/api/v1/`)

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/currencies/` | List available currencies | ❌ |
| GET | `/languages/` | List available languages | ❌ |
| GET/PUT | `/preference/` | Get/set user currency & language | ✅ |
| GET | `/visited-places/` | List popular places | ❌ |

---

## 💰 Pricing Engine

All pricing logic lives in `apps/booking/utils.py`. The calculation order is:

```
Base Price (USD)
  + Other Charges (flat USD amounts, always applied)
  + Selected Add-ons (flat USD amounts, guest-selected)
  + Vacation Surcharge (% of base, for specific months)
  + Weekend Surcharge (% of base, for specific days — daily only)
  + Rating Surcharge (% of base, when avg rating ≥ threshold)
  = Total Before Discount
  − Discount (% of base price)
  = Final Unit Price (USD)
  × Exchange Rate
  = Total in User Currency × Duration
```

**Key rules:**
- `OtherCharges` and `AddOnsPrice` are **flat USD amounts** (not percentages)
- `Vacation.price` and `Weekend.price` are **percentage values** (e.g., `20` = 20%)
- `discount` is a **percentage of the base price** only
- Prices are stored in **USD** and converted dynamically on every API response

---

## 🌍 Multi-Currency System

- **Storage:** All property prices are stored in USD in the database
- **Conversion:** On every API response, prices are multiplied by the user's currency `exchange_rate`
- **Currency Selection:** Users set their preferred currency via `PUT /others/api/v1/preference/`
- **Exchange Rates:** Managed in the `Currency` model (admin-configurable)

To add currencies or update rates, go to the admin panel → **Others → Currencies**.

---

## 🔔 Push Notifications

Firebase Cloud Messaging (FCM) is used for push notifications.

**Setup:**
1. Create a Firebase project at [console.firebase.google.com](https://console.firebase.google.com)
2. Generate a service account key (JSON)
3. Save it as `firebase-key.json` in the project root

**Notification Events:**
- Booking created (guest)
- Booking confirmed/declined (guest)
- Check-in reminder
- Announcements (broadcast to all/owners/guests)

**Flutter integration:**
```dart
// Register device token after login
POST /notify/api/v1/device-token/register/
{ "token": "<fcm_token>" }
```

---

## 🖥 Admin Panel

Access the admin panel at `/admin/` with your superuser credentials.

The admin uses **Unfold** for a modern UI. Key admin sections:

| Section | What you can manage |
|---|---|
| **Properties** | Listings, charges, add-ons, vacations, weekends |
| **Bookings** | View/manage bookings, confirm/decline |
| **Auth** | Users, documents, OTP |
| **Notifications** | Send announcements, view logs |
| **Others** | Currencies, exchange rates, languages |

---

## 📖 API Documentation

Interactive API docs are auto-generated via `drf-spectacular`:

| URL | Description |
|---|---|
| `/api/docs/` | Swagger UI |
| `/api/redoc/` | ReDoc |
| `/api/schema/` | Raw OpenAPI schema (YAML) |

---

## 🗂 Booking Status Flow

```
PENDING  →  CONFIRMED  →  CHECKED_IN  →  CHECKED_OUT
    ↓             ↓
DECLINED      CANCELLED
```

- **PENDING** — Booking submitted, awaiting host review
- **CONFIRMED** — Host approved the booking
- **CHECKED_IN** — Guest has checked in
- **CHECKED_OUT** — Stay completed
- **DECLINED** — Host rejected the booking
- **CANCELLED** — Guest or host cancelled

---

## 📄 License

This project is proprietary. All rights reserved.
