# 🗺️ Kazakhstan Tourism Routing API

Backend MVP API for calculating optimal routes from Almaty to tourist destinations in Southern Kazakhstan using multi-criteria optimization.

## 📋 Overview

This API helps tourists plan trips by calculating the best route from transportation hubs to tourist attractions. The system uses a **Multi-Criteria Dijkstra Algorithm** with **Pareto Weights** to balance:

- ⏱️ **Time** - Travel duration
- 💰 **Cost** - Price in KZT (Kazakhstan Tenge)
- 🛋️ **Comfort** - Journey quality
- 🌱 **CO2** - Environmental impact

## 🏗️ Architecture

### Core Principles

1. **Separation of Concerns**: Routing logic is completely separate from tourism content
2. **Graph-Based Routing**: Only `Node` + `TransportSegment` are used in pathfinding
3. **Last-Mile Integration**: Tourist points connect via `PointNode` (applied AFTER route calculation)

### Domain Models

```
Region                    → Groups tourist points by area
TouristPointCategory      → Hierarchical categorization (e.g., Nature > Canyon)
Node                      → Transportation location (city, station, airport)
TransportSegment          → Direct connection between nodes (ROUTING GRAPH EDGE)
TouristPoint              → Tourist destination (NOT part of routing graph)
PointNode                 → Last-mile access from node to tourist point
```

### Transportation Modes

- ✈️ Plane
- 🚂 Train  
- 🚌 Bus
- 🚖 Taxi
- 🚐 Marshrutka (shared minibus)

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- pip or uv

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/DanKair/travel-nomad-kz.git
   ```

2. **Create virtual environment** (optional but recommended)
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Mac/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment** (optional)
   ```bash
   copy .env.example .env
   # Edit .env if you want to customize settings
   ```

5. **Seed the database** with sample data
   ```bash
   python scripts/seed_data.py
   ```

6. **Run the server**
   ```bash
   uvicorn app.main:app --reload
   ```

7. **Access the API**
   - API: http://localhost:8000
   - Interactive Docs: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## 📚 API Examples

### Calculate Route

```http
GET /routes?from_node=almaty&to_tourist_point=mausoleum-yasawi
```

**Response:**
```json
{
  "from_node": "almaty",
  "to_tourist_point": "mausoleum-yasawi",
  "route_steps": [
    {
      "from_node_name": "Almaty",
      "to_node_name": "Shymkent",
      "transport_mode": "bus",
      "distance_km": 690,
      "time_minutes": 720,
      "cost": 4000,
      "comfort_score": 5.0,
      "co2_kg": 25.0
    },
    {
      "from_node_name": "Shymkent",
      "to_node_name": "Turkestan",
      "transport_mode": "bus",
      "distance_km": 180,
      "time_minutes": 120,
      "cost": 1500,
      "comfort_score": 6.0,
      "co2_kg": 8.0
    }
  ],
  "last_mile_access": {
    "from_node_name": "Turkestan",
    "access_type": "taxi",
    "distance_km": 2.3,
    "time_minutes": 7,
    "cost": 500,
    "description": "Short taxi ride from Turkestan city center..."
  },
  "total_distance_km": 872.3,
  "total_time_minutes": 847,
  "total_cost": 6000,
  "total_co2_kg": 33.0,
  "average_comfort": 5.5,
  "optimization_score": 0.3245
}
```

### Custom Weights

Prioritize cheaper routes over faster ones:

```http
GET /routes?from_node=almaty&to_tourist_point=mausoleum-yasawi&time_weight=0.2&cost_weight=0.6&comfort_weight=0.1&co2_weight=0.1
```

### List Tourist Points

```http
GET /tourist-points
GET /tourist-points?region_id=1
GET /tourist-points?category_id=2
```

### Manage Regions

```http
GET /regions
POST /regions
PATCH /regions/1
```

## 🧪 Sample Data

The seed script creates:

- **Regions**: Almaty Region, Turkestan Region
- **Cities**: Almaty, Shymkent, Turkestan, Taraz
- **Tourist Points**:
  - Charyn Canyon (Nature)
  - Mausoleum of Khoja Ahmed Yasawi (Culture)
  - Aksu-Zhabagly Nature Reserve (Nature)
- **Transport Routes**: Bus and train connections between cities

## 🧮 Algorithm Explained (For Beginners)

### What is Dijkstra's Algorithm?

Dijkstra's algorithm finds the shortest path in a graph. Imagine it like this:

1. Start at your origin city
2. Check all places you can go directly
3. Pick the "cheapest" one to explore
4. Repeat until you reach your destination

### Multi-Criteria Optimization

Instead of just minimizing ONE thing (like time), we balance MULTIPLE factors:

```python
score = (time × 0.4) + (cost × 0.3) + (comfort × 0.2) + (co2 × 0.1)
```

The algorithm finds the route with the **lowest combined score**.

### Normalization

Since time is in minutes, cost in KZT, and CO2 in kg, we normalize all values to a 0-1 scale so they can be fairly combined.

### Detailed Comments in Code

Check `app/services/routing.py` for extensive line-by-line explanations!

## 📁 Project Structure

```
fastapi-basic-projects/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration settings
│   ├── database.py          # Database setup and session management
│   ├── enums.py             # Domain enumerations
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── api/
│   │   ├── regions.py       # Region endpoints
│   │   ├── tourist_points.py # Tourist point endpoints
│   │   └── routing.py       # Route calculation endpoint
│   └── services/
│       └── routing.py       # Multi-criteria Dijkstra algorithm
├── scripts/
│   └── seed_data.py         # Database seeding script
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## 🔧 Configuration

Edit `.env` to customize:

```env
DATABASE_URL=sqlite:///./kazakhstan_routes.db
DEFAULT_TIME_WEIGHT=0.4
DEFAULT_COST_WEIGHT=0.3
DEFAULT_COMFORT_WEIGHT=0.2
DEFAULT_CO2_WEIGHT=0.1
```

## 🎓 Learning Resources

### For Junior Developers

This codebase is heavily documented for learning! Key files to study:

1. **app/models.py** - SQLAlchemy 2.x models with relationships
2. **app/services/routing.py** - Multi-criteria Dijkstra with detailed comments
3. **scripts/seed_data.py** - Database population patterns

### Key Concepts

- **SQLAlchemy 2.x**: Modern ORM with `Mapped` type hints
- **Pydantic v2**: Data validation and serialization
- **FastAPI**: Modern async web framework
- **Graph Algorithms**: Dijkstra's shortest path
- **Multi-Objective Optimization**: Pareto weights

## 🛠️ Development

### Admin workflow: adding a destination via the API

All write endpoints need the `X-API-Key` header. Only the fields shown are
required — distance, travel time, price, CO2 and comfort are estimated
automatically and any value you supply overrides the estimate.

```bash
API=http://localhost:8000/api
KEY="X-API-Key: $TEAM_API_KEY"
JSON="Content-Type: application/json"

# 1. A transport node (coordinates are geocoded from the name if omitted)
curl -X POST $API/transport-nodes -H "$KEY" -H "$JSON" \
  -d '{"name": "Saty", "node_type": "village"}'

# 2. Preview a segment, then create it in both directions
curl -X POST $API/transport-segments/estimate -H "$KEY" -H "$JSON" \
  -d '{"from_node_id": 1, "to_node_id": 10, "transport_mode": "marshrutka"}'
curl -X POST $API/transport-segments -H "$KEY" -H "$JSON" \
  -d '{"from_node_id": 1, "to_node_id": 10, "transport_mode": "marshrutka", "create_reverse": true}'

# 3. The tourist point, then link it to its nearest node(s)
curl -X POST $API/tourist-points -H "$KEY" -H "$JSON" \
  -d '{"name": "Kolsai Lakes", "region_id": 1, "category_id": 1}'
curl -X POST $API/point-nodes/auto-connect -H "$KEY" -H "$JSON" \
  -d '{"tourist_point_id": 8}'

# 4. It is routable
curl "$API/routes/alternatives?from_node=almaty&to_tourist_point=kolsai-lakes"
```

### Price checking

```bash
# Segments whose stored price is >30% away from the tariff model
curl "$API/transport-segments/price-check?threshold_pct=30" -H "$KEY"

# Accept the model's value for one segment (only the listed fields change)
curl -X POST $API/transport-segments/5/recalculate -H "$KEY" -H "$JSON" \
  -d '{"fields": ["cost"]}'
```

The tariff model (`base fare + per-km rate`, in `app/constants.py`) is an
**estimate fitted to the seed data, not a live price feed**. Use it for
defaults and for spotting typos or stale fares; re-tune the constants when
real prices move.

`distance_strategy: "haversine_fallback"` in a response means the road-routing
service (OSRM) was unreachable and the distance is a straight-line
approximation — re-run `/recalculate` with `["distance_km", "time_minutes"]`
later. Set `OSRM_BASE_URL` to a self-hosted instance for production.

### Tests

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest
```

The suite uses a temporary SQLite database and fake OSRM/Nominatim servers, so
it needs no network, Postgres or Redis.

## 🚧 Future Enhancements (Not in MVP)

- ❌ Frontend with interactive map
- ❌ Real-time traffic data
- ❌ Advanced heuristics (A* algorithm)
- ❌ Graph databases
- ❌ User authentication
- ❌ Route preferences/favorites

## 📄 License

MIT License - Feel free to use this for learning and development!

## 🙋 Questions?

This project was built as an educational MVP for learning FastAPI, SQLAlchemy, and graph algorithms. All code includes extensive comments to help junior developers understand routing algorithms and backend architecture.

---

**Built with ❤️ for Kazakhstan tourism and Python learning**
