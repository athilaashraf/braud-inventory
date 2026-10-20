# 👕 Braud Clothing: Stock & Billing Manager

A web app for a clothing shop to track shirt stock by size, create bills with PDF invoices, and see what is running low, all from one login-protected dashboard.

![Python](https://img.shields.io/badge/Python-3.x-blue)
![Flask](https://img.shields.io/badge/Flask-web%20app-lightgrey)
![SQLite](https://img.shields.io/badge/Database-SQLite-green)
![Status](https://img.shields.io/badge/Status-Ready%20for%20use-brightgreen)

## 📑 Quick links
[Features](#-features) · [Screenshots](#-screenshots) · [Setup](#-setup) · [How to use](#-how-to-use) · [Design decisions](#-design-decisions) · [Project structure](#-project-structure) · [Security](#-security-notes) · [Troubleshooting](#-troubleshooting) · [Support](#-support)

---

## ✨ Features

- 🔐 **Secure login**: admin username and hashed password; every page is protected
- 🏠 **Home dashboard**: total shirts in stock, low/out-of-stock models, today's sales and bill count
- 📦 **Add Stock by sets**: one set adds 1 piece each of S, M, L, XL
- 📊 **Stock Status**: see what is left per model and size, marked **OK / Low / Out**
- 👕 **Products**: add models with a price and a low-stock warning limit, and edit them later
- 🧾 **Billing**: multi-item bills, stock check before saving, percent or fixed discount
- 📄 **PDF invoices**: download a bill as PDF (`INV-0001`, `INV-0002`, ...)
- ❌ **Cancel bills**: cancel with a reason, and stock is added back automatically
- 🛠️ **Correct Stock**: fix a wrong stock number with a reason, and every change is logged

## 📸 Screenshots

| Login | Home dashboard |
|---|---|
| <img src="screenshots/login.png" alt="Login page" height="300"> | <img src="screenshots/home.png" alt="Home dashboard" height="300"> |

| Billing | Invoices |
|---|---|
| <img src="screenshots/bill.png" alt="Billing page" height="300"> | <img src="screenshots/invoices.png" alt="Invoices page" height="300"> |

*Screenshots use sample data.*

---

## 🚀 Setup

<details>
<summary><b>Step 1: Install (click to expand)</b></summary>

Requirements: Python 3.9 or newer.

```powershell
git clone https://github.com/athilaashraf/braud-inventory.git
cd braud-inventory
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
</details>

<details>
<summary><b>Step 2: Create your .env file</b></summary>

```powershell
copy .env.example .env
```

| Variable | What it is |
|---|---|
| `SECRET_KEY` | Random key Flask uses to protect login sessions |
| `ADMIN_USER` | Username for logging in |
| `ADMIN_HASH` | Hashed (scrambled) version of the admin password |

**Generate a secret key:**
```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

**Generate the password hash** (it asks you to type the password):
