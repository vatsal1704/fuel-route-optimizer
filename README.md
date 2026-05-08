# Fuel Route Optimizer

A full-stack route planning application that calculates the most cost-effective fuel stops between two locations in the USA.

The system combines route optimization, fuel price analysis, and interactive map visualization to generate optimized fuel plans while minimizing external API calls.

---

# Features

* Calculate driving route between two USA locations
* Display optimized fuel stops based on fuel prices
* Supports multiple refueling stops for long routes
* Assumes:

  * Vehicle range = 500 miles
  * Fuel efficiency = 10 MPG
* Interactive map visualization
* Total estimated fuel cost calculation
* Greedy algorithm for fuel optimization
* Minimal external API usage for better performance
* Responsive React frontend
* Django REST API backend

---

# Tech Stack

## Backend

* Python
* Django 5
* Django REST Framework
* OSRM Routing API
* Pandas
* NumPy

## Frontend

* React
* Axios
* Leaflet Maps
* Tailwind CSS

## APIs & Services

* OSRM (Open Source Routing Machine)
* OpenStreetMap Tiles

---

# System Design

The application is designed to minimize routing API calls and improve performance.

## Optimization Strategy

* One primary route API call per request
* Fuel stations loaded into memory for fast access
* Route corridor filtering to reduce search space
* Greedy algorithm for selecting optimal fuel stops
* Distance and reachability constraints respected

---

# Project Structure

```text
fuel-route/
│
├── backend/
│   ├── routes/
│   ├── services/
│   ├── fuelroute/
│   ├── requirements.txt
│   └── manage.py
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── .env
│
└── README.md
```

---

# API Endpoint

## Plan Route

### Request

```http
POST /api/route/
```

### Example Request

```json
{
  "start": "Los Angeles, CA",
  "finish": "Houston, TX"
}
```

### Example Response

```json
{
  "route": {
    "distance_mi": 1547,
    "duration_s": 52800
  },
  "fuel_plan": {
    "total_cost_usd": 482.13,
    "total_gallons": 154.7,
    "stops": []
  }
}
```

---

# Installation Guide

## 1. Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/fuel-route-optimizer.git
cd fuel-route-optimizer
```

---

# Backend Setup

## 2. Navigate to Backend

```bash
cd backend
```

## 3. Create Virtual Environment

```bash
python -m venv venv
```

## 4. Activate Virtual Environment

### Windows

```bash
venv\Scripts\activate
```

### macOS/Linux

```bash
source venv/bin/activate
```

## 5. Install Dependencies

```bash
pip install -r requirements.txt
```

## 6. Run Backend Server

```bash
python manage.py runserver
```

Backend runs at:

```text
http://127.0.0.1:8000
```

---

# Frontend Setup

## 7. Open New Terminal

```bash
cd frontend
```

## 8. Install Dependencies

```bash
npm install
```

## 9. Create .env File

Create:

```text
frontend/.env
```

Add:

```env
REACT_APP_BACKEND_URL=http://127.0.0.1:8000
```

## 10. Start Frontend

```bash
npm start
```

Frontend runs at:

```text
http://localhost:3000
```

---



# Example Workflow

1. Enter start location
2. Enter destination
3. Click "Find optimal route"
4. System calculates:

   * route distance
   * fuel stops
   * total fuel usage
   * total fuel cost
5. Interactive map displays:

   * route
   * start marker
   * destination marker
   * fuel stop markers

---

# Performance Optimizations

* Reduced routing API calls
* In-memory fuel station processing
* Route point sampling
* Corridor-based station filtering
* Efficient greedy stop selection

---

# Future Improvements

* Real-time fuel prices
* EV charging station support
* Traffic-aware optimization
* User authentication
* Route caching
* Multi-vehicle support
* Advanced cost prediction

---

# Deployment

## Frontend

Deployed using:

* Vercel

## Backend

Deployed using:

* Render

---

# Demo
<img width="1920" height="763" alt="Screenshot (410)" src="https://github.com/user-attachments/assets/fee2f3e7-9729-4c35-bca9-d0ec5c84c893" />


---


<img width="1920" height="755" alt="Screenshot (411)" src="https://github.com/user-attachments/assets/64132c9c-4dc8-439f-8ca6-3c6557625795" />



---

# Screenshots

Add screenshots of:

* Homepage
* Route visualization
* Optimized fuel stops
* API response in Postman

Example:

```markdown
![App Screenshot](./screenshots/app.png)
```

---

# Author

Vatsal Gaur

---

# License

This project is built for technical assessment and educational purposes.
