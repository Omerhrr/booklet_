# Booklet ERP - Modern Accounting & Business Management

A full-featured ERP system with separated Backend (FastAPI) and Frontend (Flask).

## Architecture

```
erp/
├── backend/                 # FastAPI Backend API
│   ├── app/
│   │   ├── api/v1/         # API Routes
│   │   ├── core/           # Core configuration
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic
│   │   └── main.py         # Application entry
│   ├── requirements.txt
│   └── run.py
│
└── frontend/               # Flask Frontend
    ├── app/
    │   ├── views/          # View controllers
    │   ├── templates/      # Jinja2 templates
    │   ├── static/         # CSS, JS, images
    │   └── __init__.py     # Flask app
    ├── requirements.txt
    └── run.py
```

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - ORM for database operations
- **Pydantic** - Data validation
- **JWT** - Authentication tokens
- **Bcrypt** - Password hashing

### Frontend
- **Flask** - Web framework
- **Jinja2** - Template engine
- **HTMX** - Dynamic content without full page reloads
- **Alpine.js** - Reactive components
- **Tailwind CSS** - Utility-first CSS
- **Flowbite** - UI components
- **ECharts** - Charts and visualizations

## Features

- **Dashboard** - Financial overview with charts
- **CRM** - Customer and vendor management
- **Inventory** - Products, categories, stock management
- **Sales** - Invoices, credit notes, payments
- **Purchases** - Bills, debit notes
- **Accounting** - Chart of accounts, journal entries, ledger
- **HR & Payroll** - Employees, payroll processing
- **Banking** - Bank accounts, transfers, reconciliation
- **Reports** - Financial reports and analytics
- **Settings** - Business, users, roles, permissions

## Setup

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
python run.py
```

Backend will run on http://localhost:8000

### Frontend Setup

```bash
cd frontend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
python run.py
```

Frontend will run on http://localhost:5000

## Environment Variables

### Backend (.env)
```
DATABASE_URL=sqlite:///./erp.db
SECRET_KEY=your-super-secret-key
CORS_ORIGINS=http://localhost:5000
```

### Frontend (.env)
```
BACKEND_URL=http://localhost:8000
SECRET_KEY=your-flask-secret-key
```

## Security Features

- JWT-based authentication
- CSRF protection
- Role-based access control (RBAC)
- Password hashing with bcrypt
- Secure cookie handling

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## License

MIT License
