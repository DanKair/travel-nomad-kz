# 🚀 Quick Start Guide - Full Stack Application

## Running Both Frontend and Backend

This project has two separate servers that need to run simultaneously:
1. **Backend API** (FastAPI on port 8000)
2. **Frontend UI** (React + Vite on port 5173/5174)

### Terminal 1: Backend API

```bash
# From project root
cd d:\Programming\Python_Projects\Antigravity\fastapi-basic-projects

# Make sure dependencies are installed
pip install -r requirements.txt

# Seed the database (only needed once)
python -m scripts.seed_data

# Start backend server
uvicorn app.main:app --reload
```

Backend will run on: **http://localhost:8000**
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### Terminal 2: Frontend UI

```bash
# From project root, navigate to frontend
cd d:\Programming\Python_Projects\Antigravity\fastapi-basic-projects\frontend

# Make sure dependencies are installed (only needed once)
npm install

# Start frontend dev server
npm run dev
```

Frontend will run on: **http://localhost:5173** or **http://localhost:5174**

## 🎯 Using the Application

1. **Open your browser** to http://localhost:5173 (or the port shown in terminal)

2. **Select a Region** from the left sidebar:
   - Click on "Almaty Region" or "Turkestan Region"
   - The map will show markers for tourist points in that region

3. **Choose a Tourist Point** from the dropdown list:
   - Click on a tourist point (e.g., "Charyn Canyon" or "Mausoleum of Yasawi")
   - The map will highlight the selected point
   - A detail card will appear at the bottom

4. **View Details**:
   - Location and coordinates
   - Description
   - Category (Nature, Culture, etc.)

5. **Calculate Route**:
   - Click the "🧭 Calculate Route from Almaty" button
   - The system will show:
     - Transport segments (bus, train, etc.)
     - Last-mile access (taxi, walking, car)
     - Total time, cost, distance, and comfort score

## 🔧 Troubleshooting

### "npm run dev" Error in Root Directory
**Problem:** Running `npm run dev` from `fastapi-basic-projects` directory
**Solution:** Always run it from `frontend` subdirectory:
```bash
cd frontend
npm run dev
```

### Backend Not Responding
**Problem:** API calls fail
**Solution:** Make sure backend is running on port 8000:
```bash
uvicorn app.main:app --reload
```

### CORS Errors
**Problem:** Frontend can't access backend
**Solution:** Backend already has CORS enabled for all origins in development

### Port Already in Use
**Problem:** Vite says "Port 5173 is in use"
**Solution:** Vite will automatically try the next port (5174, 5175, etc.). Just use the URL shown in the terminal.

## 📁 Project Structure

```
fastapi-basic-projects/
├── app/                    # Backend (Python/FastAPI)
│   ├── main.py
│   ├── models.py
│   ├── services/
│   └── api/
├── frontend/               # Frontend (React/Vite)
│   ├── src/
│   │   ├── App.jsx        # Main component
│   │   └── App.css        # Styles
│   └── package.json
├── scripts/
│   └── seed_data.py       # Sample data
└── requirements.txt       # Python dependencies
```

## 🎨 Features

- **Interactive Leaflet Map** showing regions and tourist points
- **Region-based filtering** of tourist destinations
- **Detailed tourist point cards** with descriptions
- **Multi-criteria route calculation** (time, cost, comfort, CO2)
- **Minimalistic, modern UI** inspired by Rome2Rio
- **Hover zoom effects** on regions and tourist points
- **Responsive design** for different screen sizes

## 🧪 Test Data

The application comes with sample data:
- **2 Regions**: Almaty Region, Turkestan Region
- **3 Tourist Points**:
  - Charyn Canyon (Nature)
  - Mausoleum of Khoja Ahmed Yasawi (Culture)
  - Aksu-Zhabagly Nature Reserve (Nature)
- **Multiple transport routes** between cities

## 📝 API Endpoints Used by Frontend

- `GET /regions` - Fetch all regions
- `GET /tourist-points?region_id={id}` - Filter tourist points by region
- `GET /routes?from_node=almaty&to_tourist_point={slug}` - Calculate route

---

**Need Help?** Check the main README.md for detailed documentation.
