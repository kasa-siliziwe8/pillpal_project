# Pill Pal — Medication Adherence System
### HCI / ICT Electives II — NHCI62110 / NITE63410
**Sol Plaatje University, Northern Cape, South Africa**

---

## Overview

Pill Pal is a multi-channel medication adherence platform designed for South Africa's public healthcare system. It supports patients, caregivers, and clinic administrators via SMS, voice call, and a mobile-friendly web application.

---

## Quick Start

### 1. Requirements
```
Python 3.10+
Django 6.x
```

### 2. Install
```bash
pip install django
```

### 3. Set up database & seed demo data
```bash
python manage.py migrate
python manage.py seed_data
```

### 4. Run
```bash
python manage.py runserver
```
Open: **http://127.0.0.1:8000**

---

## Demo Accounts

| Role | Username | Password | Access |
|---|---|---|---|
| Patient | `thabo` | `demo1234` | Dashboard, Medications, Reports, SMS/Voice |
| Caregiver | `nomsa` | `demo1234` | Patient overview, adherence tracking |
| Clinic Admin | `sister_pk` | `demo1234` | Clinic dashboard, at-risk patients |

---

## Project Structure

```
pillpal_project/
├── pillpal_project/          # Project settings & root URLs
│   ├── settings.py
│   └── urls.py
├── core/                     # Landing, dashboard, SMS/voice views
│   ├── models.py             # Clinic model
│   ├── views.py              # Main views + API endpoints
│   ├── urls.py
│   ├── templates/core/       # All HTML templates
│   │   ├── base.html         # Base layout with sidebar + topbar
│   │   ├── landing.html      # Public landing page
│   │   ├── dashboard.html    # Role-based dashboard
│   │   ├── medications.html  # Medication info + accordion
│   │   ├── schedule_list.html # Schedule management
│   │   ├── dose_history.html # Full dose log
│   │   ├── reports.html      # Chart.js adherence reports
│   │   ├── sms_simulator.html # Interactive SMS phone mockup
│   │   ├── voice_channel.html # Interactive voice dialpad
│   │   ├── notifications.html # Notification inbox
│   │   ├── caregiver_management.html # Caregiver linking
│   │   ├── profile.html
│   │   ├── settings.html
│   │   ├── change_password.html
│   │   ├── 404.html
│   │   └── 500.html
│   ├── static/js/pillpal.js  # Global JavaScript
│   └── management/commands/
│       └── seed_data.py      # Demo data seeder
├── accounts/                 # Custom User model, auth views
│   ├── models.py             # User + CaregiverPatient
│   ├── views.py              # Login, register, settings, caregiver mgmt
│   └── urls.py
├── medications/              # Medication & schedule models
│   ├── models.py             # Medication, MedicationSchedule, DoseLog
│   ├── views.py              # Schedule CRUD, dose history, confirm API
│   └── urls.py
├── reports/                  # Adherence reporting
│   ├── views.py              # Chart.js data, per-medication stats
│   └── urls.py
└── notifications/            # Notification & escalation models
    ├── models.py             # Notification, Escalation
    ├── views.py              # Inbox, mark read, unread count API
    └── urls.py
```

---

## URL Reference

| URL | View | Description |
|---|---|---|
| `/` | `landing` | Public landing page |
| `/dashboard/` | `dashboard` | Role-based main dashboard |
| `/medications/` | `medication_list` | Medication info browser |
| `/medications/schedules/` | `schedule_list` | Manage schedules |
| `/medications/history/` | `dose_history` | Full dose log |
| `/medications/api/confirm/` | `api_dose_confirm` | AJAX dose confirmation |
| `/reports/` | `reports_view` | Adherence reports + charts |
| `/sms/` | `sms_simulator` | Interactive SMS simulator |
| `/voice/` | `voice_channel` | Interactive voice simulator |
| `/notifications/` | `notification_list` | Notification inbox |
| `/accounts/login/` | `login_view` | Sign in |
| `/accounts/register/` | `register_view` | Create account |
| `/accounts/settings/` | `settings_view` | User settings |
| `/accounts/change-password/` | `change_password` | Change password |
| `/accounts/caregivers/` | `caregiver_management` | Link/remove caregivers |
| `/accounts/profile/` | `profile_view` | Profile overview |
| `/api/confirm-dose/` | `api_confirm_dose` | Dashboard dose confirm |
| `/api/sms-respond/` | `api_sms_respond` | SMS simulator backend |
| `/admin/` | Django Admin | Full data management |

---

## Key Models

### `accounts.User` (extends AbstractUser)
- `role`: patient / caregiver / clinic_admin / chw
- `channel_preference`: sms / voice / app
- `language_preference`: en / zu / xh / st / tn
- `clinic`: FK → Clinic
- `notif_*`: Boolean notification preferences

### `medications.MedicationSchedule`
- `patient`, `medication`, `dosage`, `frequency`
- `scheduled_time_1`, `scheduled_time_2` (for twice-daily)
- `is_active`, `supply_days`

### `medications.DoseLog`
- `status`: confirmed / missed / pending
- `confirmation_method`: sms / voice / app / manual
- `confirmed_at`: timestamp

### `notifications.Notification`
- `notification_type`: reminder / escalation / refill / broadcast / confirmation / info
- `channel`, `status`, `read`

---

## HCI Design Principles Applied

| Principle | Implementation |
|---|---|
| **Cognitive Load Reduction** (Sweller) | Single action card, one CTA at a time |
| **Error Prevention** (Norman) | Dose confirmation greyed after tap, duplicate guard |
| **Universal Design** (ISO 9241-171) | SMS + voice for non-smartphone users |
| **Accessibility** | No data needed for SMS/voice channels |
| **Learnability** | Onboarding flow; zero-training SMS confirmation |

---

## Academic Context

- **Module**: Human Computer Interaction / ICT Electives II
- **Code**: NHCI62110 / NITE63410
- **Institution**: Sol Plaatje University
- **Year**: 2026
