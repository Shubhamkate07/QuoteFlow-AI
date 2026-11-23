# QuoteFlow AI — Autonomous Procurement Decision-Support & Quotation Evaluation Platform

QuoteFlow AI transforms messy, unstructured supplier quotations (PDFs, Excel spreadsheets, scanned estimates) into verifiable procurement comparisons, deterministic audit trails, and multi-criteria award recommendations.

---

## Key Features

* **Multimodal Document Extraction (Gemini 2.0 Flash)**: Parses complex vendor quotes, multi-tier tables, tax terms, delivery schedules, and technical specifications with confidence scoring.
* **Deterministic Arithmetic Validation**: Verifies line item extensions, subtotals, tax rates, shipping, and currency conversions against strict zero-drift rules.
* **Multi-Criteria Supplier Scoring**:
  * Price Competitiveness (40%)
  * Specification Compliance & Tolerance Matching (30%)
  * Delivery Schedule & Lead Time (15%)
  * Commercial Payment Terms (10%)
  * Warranty Coverage (5%)
* **Side-by-Side Comparison Matrix**: Item-by-item schedule comparing unit prices, lead times, and variances against baseline target budgets.
* **Executive Reports**: Instant one-click export to formatted Excel (`.xlsx`) and PDF evaluation reports.
* **Human-in-the-Loop Sign-off**: Enforces review and sign-off guardrails before quotations are factored into official awards.

---

## Tech Stack

* **Frontend**: React 19, TypeScript, Vite, Tailwind CSS, TanStack React Query, Lucide Icons, Axios.
* **Backend**: Python 3.11, Django 5.1, Django REST Framework, SimpleJWT, WhiteNoise, Gunicorn.
* **Database**: PostgreSQL with connection pooling.
* **Document Processing**: PyMuPDF (`fitz`), `openpyxl`, `reportlab`.
* **AI Extraction Engine**: Google Gemini 2.0 Flash API (`google-genai`).

---

## Project Structure

```text
QuoteFlow AI/
├── client/                 # React 19 + TypeScript SPA
│   ├── src/
│   │   ├── features/       # Feature modules (rfq, quotations, comparison, reports, dashboard)
│   │   ├── components/     # Reusable UI component library
│   │   ├── pages/          # Application routes and views
│   │   └── lib/            # Axios API client and auth storage
│   ├── public/             # Static assets & Netlify _redirects
│   └── package.json
├── server/                 # Django REST Framework Backend
│   ├── core/               # Health probe, API root & live dashboard metrics
│   ├── rfqs/               # RFQs and line items management
│   ├── quotations/         # Quotation uploads, physical file serving, document parsing
│   ├── comparisons/        # Multi-criteria scoring, specification engine, snapshots
│   ├── reports/            # PDF and Excel export views
│   ├── suppliers/          # Vendor directory
│   ├── config/             # Django settings (base, development, production)
│   └── requirements.txt
├── netlify.toml            # Netlify deployment configuration
├── render.yaml             # Render infrastructure blueprint
└── README.md
```

---

## Getting Started Locally

### 1. Prerequisites
* Python 3.11+
* Node.js 18+ and npm
* PostgreSQL database

### 2. Backend Setup
```bash
cd server
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

### 3. Frontend Setup
```bash
cd client
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## Deployment

### Frontend (Netlify)
1. Import the repository into [Netlify](https://netlify.com).
2. Base directory: `client`
3. Build command: `npm run build`
4. Publish directory: `client/dist`
5. Environment variable: `VITE_API_BASE_URL = https://<your-render-backend>.onrender.com/api`

### Backend (Render)
1. Import the repository as a **Web Service** on [Render](https://render.com).
2. Root directory: `server`
3. Build command: `pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput`
4. Start command: `gunicorn config.wsgi:application`
5. Create a free **PostgreSQL Database** on Render and link via `DATABASE_URL`.
6. Add `GEMINI_API_KEY`, `DJANGO_ENV=production`, `DEBUG=False`, `ALLOWED_HOSTS=.onrender.com`, `CORS_ALLOWED_ORIGINS=https://<your-netlify-app>.netlify.app`.

---

## License
MIT License.
