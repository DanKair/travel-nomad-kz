"""
Seed Data Script

Populates the database with sample data for Kazakhstan tourism routing.

This includes:
- Regions (Almaty Region, Turkestan Region, etc.)
- Tourist point categories (Nature, Culture, etc.)
- Nodes (cities, stations, airports)
- Transport segments (routes between nodes)
- Tourist points (destinations)
- Point nodes (last-mile access)

Run this after database initialization to get a working demo.
"""

import sys
from pathlib import Path

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal, init_db
from app.models import (
    Region,
    TouristPointCategory,
    Node,
    TransportSegment,
    TouristPoint,
    PointNode
)
from app.enums import NodeType, TransportMode, AccessType


def seed_database():
    """
    Populate database with sample data for Southern Kazakhstan tourism.
    """
    print("🌱 Seeding database with sample data...")
    
    # Initialize database first
    init_db()
    
    # Get database session
    db = SessionLocal()
    
    try:
        # Helper function to prevent duplicates
        def get_or_create(session, model, **kwargs):
            # Filter by unique fields if present, otherwise all kwargs
            # For this specific script, we can assume 'slug' is unique for Node/Point
            # and 'name' for Region/Category.
            # But let's be generic: lookup by all kwargs first? 
            # Or better, just use the kwargs passed, assuming the caller knows unique constraints.
            
            # Special handling for "defaults" if we want to create with more data than we filter by
            defaults = kwargs.pop('defaults', {})
            
            instance = session.query(model).filter_by(**kwargs).first()
            if instance:
                return instance, False
            else:
                params = {**kwargs, **defaults}
                instance = model(**params)
                session.add(instance)
                session.commit()
                return instance, True

        # =====================================================================
        # 1. CREATE REGIONS
        # =====================================================================
        print("📍 Creating/Checking regions...")
        
        almaty_region, _ = get_or_create(db, Region, name="Алматинская Область", defaults={
            "description": "Largest region in Kazakhstan, home to Almaty city and stunning natural attractions"
        })
        
        turkestan_region, _ = get_or_create(db, Region, name="Туркестанская Область", defaults={
            "description": "Historical region with ancient cities and cultural heritage sites"
        })

        zhambyl_region, _ = get_or_create(db, Region, name="Жамбылская Область", defaults={
            "description": "Historical region with ancient cities and cultural heritage sites"
        })

        kyzylorda_region, _ = get_or_create(db, Region, name="Кызылординская Область", defaults={
            "description": "Historical region with ancient cities and cultural heritage sites"
        })

        print(f"   ✓ Checked/Created regions")
        
        # =====================================================================
        # 2. CREATE TOURIST POINT CATEGORIES
        # =====================================================================
        print("🏷️  Creating/Checking categories...")
        
        # Top-level categories
        nature_category, _ = get_or_create(db, TouristPointCategory, name="Природа", defaults={"parent_id": None})
        culture_category, _ = get_or_create(db, TouristPointCategory, name="Культура & История", defaults={"parent_id": None})
        
        # Sub-categories
        canyon_category, _ = get_or_create(db, TouristPointCategory, name="Каньон", defaults={"parent_id": nature_category.id})
        reserve_category, _ = get_or_create(db, TouristPointCategory, name="Заповедник", defaults={"parent_id": nature_category.id})
        lake_category, _ = get_or_create(db, TouristPointCategory, name="Озеро", defaults={"parent_id": nature_category.id})
        park_category, _ = get_or_create(db, TouristPointCategory, name="Парк", defaults={"parent_id": nature_category.id})
        waterfall_category, _ = get_or_create(db, TouristPointCategory, name="Водопад", defaults={"parent_id": nature_category.id})
        mountain_category, _ = get_or_create(db, TouristPointCategory, name="Горы", defaults={"parent_id": nature_category.id})
        museum_category, _ = get_or_create(db, TouristPointCategory, name="Музей", defaults={"parent_id": culture_category.id})
        monument_category, _ = get_or_create(db, TouristPointCategory, name="Исторический памятник", defaults={"parent_id": culture_category.id})
        sacred_category, _ = get_or_create(db, TouristPointCategory, name="Священное место", defaults={"parent_id": culture_category.id})
        fortress_category, _ = get_or_create(db, TouristPointCategory, name="Крепость", defaults={"parent_id": culture_category.id})
        
        print(f"   ✓ Checked/Created categories")
        
        # =====================================================================
        # 3. CREATE NODES (Transportation locations)
        # =====================================================================
        print("🚉 Creating/Checking transportation nodes...")
        
        # Almaty
        almaty_city, _ = get_or_create(db, Node, slug="almaty", defaults={
            "name": "Almaty",
            "latitude": 43.233503,
            "longitude": 76.921767,
            "node_type": NodeType.CITY
        })
        
        almaty_railway, _ = get_or_create(db, Node, slug="almaty-railway", defaults={
            "name": "Almaty-2 Railway Station",
            "latitude": 43.2566,
            "longitude": 76.9286,
            "node_type": NodeType.STATION
        })

        almaty_airport, created = get_or_create(db, Node, slug="almaty-airport", defaults={
            "name": "Almaty International Airport",
            "latitude": 43.3521, 
            "longitude": 77.0405,
            "node_type": NodeType.AIRPORT
        })
        if created: print("   + Created Almaty Airport")
        
        # Shymkent
        shymkent_city, _ = get_or_create(db, Node, slug="shymkent", defaults={
            "name": "Shymkent",
            "latitude": 42.3143,
            "longitude": 69.5960,
            "node_type": NodeType.CITY
        })

        shymkent_airport, created = get_or_create(db, Node, slug="shymkent-airport", defaults={
            "name": "Shymkent International Airport",
            "latitude": 42.3642,
            "longitude": 69.4811,
            "node_type": NodeType.AIRPORT
        })
        if created: print("   + Created Shymkent Airport")
        
        # Turkestan
        turkestan_city, _ = get_or_create(db, Node, slug="turkestan", defaults={
            "name": "Turkestan",
            "latitude": 43.2983,
            "longitude": 68.2517,
            "node_type": NodeType.CITY
        })
        
        # Taraz
        taraz_city, _ = get_or_create(db, Node, slug="taraz", defaults={
            "name": "Taraz",
            "latitude": 42.9000,
            "longitude": 71.3667,
            "node_type": NodeType.CITY
        })

        taraz_airport, created = get_or_create(db, Node, slug="taraz-airport", defaults={
            "name": "Taraz Airport",
            "latitude": 42.8530,
            "longitude": 71.2954,
            "node_type": NodeType.AIRPORT
        })
        if created: print("   + Created Taraz Airport")

        # Konayev (for Tamgaly Tas)
        konayev_city, created = get_or_create(db, Node, slug="konayev", defaults={
            "name": "Konayev",
            "latitude": 43.8767,
            "longitude": 77.0653,
            "node_type": NodeType.CITY
        })
        if created: print("   + Created Konayev City")
        
        print(f"   ✓ Checked/Created transportation nodes")
        
        # =====================================================================
        # 4. CREATE TRANSPORT SEGMENTS (Routes between nodes)
        # =====================================================================
        print("🚂 Creating/Checking transport segments...")
        
        def add_segment_if_not_exists(from_node, to_node, mode, **kwargs):
            exists = db.query(TransportSegment).filter_by(
                from_node_id=from_node.id,
                to_node_id=to_node.id,
                transport_mode=mode
            ).first()
            if not exists:
                segment = TransportSegment(
                    from_node_id=from_node.id,
                    to_node_id=to_node.id,
                    transport_mode=mode,
                    **kwargs
                )
                db.add(segment)
                db.commit()

        # Existing Segments (Almaty -> Shymkent)
        add_segment_if_not_exists(almaty_railway, shymkent_city, TransportMode.TRAIN, distance_km=1082, time_minutes=840, cost=6000, comfort_score=7.0, co2_kg=45.0)
        add_segment_if_not_exists(almaty_city, shymkent_city, TransportMode.BUS, distance_km=690, time_minutes=720, cost=4000, comfort_score=5.0, co2_kg=25.0)
        
        # Shymkent -> Turkestan
        add_segment_if_not_exists(shymkent_city, turkestan_city, TransportMode.BUS, distance_km=180, time_minutes=120, cost=1500, comfort_score=6.0, co2_kg=8.0)
        add_segment_if_not_exists(shymkent_city, turkestan_city, TransportMode.MARSHRUTKA, distance_km=180, time_minutes=100, cost=1200, comfort_score=4.0, co2_kg=12.0)
        
        # Shymkent -> Taraz
        add_segment_if_not_exists(shymkent_city, taraz_city, TransportMode.BUS, distance_km=280, time_minutes=210, cost=2000, comfort_score=6.0, co2_kg=15.0)
        
        # Almaty -> Taraz
        add_segment_if_not_exists(almaty_city, taraz_city, TransportMode.BUS, distance_km=450, time_minutes=360, cost=3000, comfort_score=6.5, co2_kg=18.0)

        # --- NEW SEGMENTS FROM DOC ---
        
        # Almaty Airport -> Shymkent Airport (Plane) - "Самолет – 20К тенге 1.5 ч."
        add_segment_if_not_exists(almaty_airport, shymkent_airport, TransportMode.PLANE, distance_km=610, time_minutes=90, cost=20000, comfort_score=9.0, co2_kg=80.0)
        
        # Almaty Airport -> Taraz Airport (Plane) - "Самолет от Алматы до Тараза. Цена – 19К." (Time approx 1h 10m)
        add_segment_if_not_exists(almaty_airport, taraz_airport, TransportMode.PLANE, distance_km=460, time_minutes=70, cost=19000, comfort_score=9.0, co2_kg=70.0)

        # Almaty -> Konayev (Train/Taxi/Bus) for Tamgaly Tas
        # "автобус с сайрана цена 5000 тг до Конаева" (Bus Almaty -> Konayev)
        # Distance Almaty (Sayran) -> Konayev ~70km. Time ~1-1.5h.
        add_segment_if_not_exists(almaty_city, konayev_city, TransportMode.BUS, distance_km=75, time_minutes=90, cost=5000, comfort_score=6.0, co2_kg=5.0)
        
        # "поезд до Конаева" (Train Almaty -> Konayev)
        # Assuming from Almaty-1/2. Distance ~70km.
        add_segment_if_not_exists(almaty_railway, konayev_city, TransportMode.TRAIN, distance_km=70, time_minutes=120, cost=2000, comfort_score=7.0, co2_kg=8.0)
        
        # "На машине (бензин) 1ч. 30м / Такси 10К тг 1ч.30м" (Almaty -> Tamgaly Tas direct is PointNode, but let's add Almaty->Konayev taxi segment too)
        add_segment_if_not_exists(almaty_city, konayev_city, TransportMode.TAXI, distance_km=75, time_minutes=80, cost=10000, comfort_score=8.0, co2_kg=15.0)

        # --- AIRPORT TRANSFERS (Critical for routing) ---
        # Almaty Airport <-> Almaty City
        add_segment_if_not_exists(almaty_airport, almaty_city, TransportMode.TAXI, distance_km=15, time_minutes=30, cost=3000, comfort_score=8.0, co2_kg=5.0)
        add_segment_if_not_exists(almaty_city, almaty_airport, TransportMode.TAXI, distance_km=15, time_minutes=30, cost=3000, comfort_score=8.0, co2_kg=5.0) # Bidirectional? Graph is directed? Routing service builds graph from segments. If segments are one-way in DB, we need both.
        # Check routing.py: _build_graph does `graph[segment.from_node_id].append`. So yes, directed.
        
        # Shymkent Airport <-> Shymkent City
        add_segment_if_not_exists(shymkent_airport, shymkent_city, TransportMode.TAXI, distance_km=12, time_minutes=20, cost=2000, comfort_score=8.0, co2_kg=4.0)
        add_segment_if_not_exists(shymkent_city, shymkent_airport, TransportMode.TAXI, distance_km=12, time_minutes=20, cost=2000, comfort_score=8.0, co2_kg=4.0)
        
        # Taraz Airport <-> Taraz City
        add_segment_if_not_exists(taraz_airport, taraz_city, TransportMode.TAXI, distance_km=10, time_minutes=15, cost=1500, comfort_score=8.0, co2_kg=3.0)
        add_segment_if_not_exists(taraz_city, taraz_airport, TransportMode.TAXI, distance_km=10, time_minutes=15, cost=1500, comfort_score=8.0, co2_kg=3.0)

        print(f"   ✓ Checked/Created transport segments")
        
        # =====================================================================
        # 5. CREATE TOURIST POINTS (Destinations)
        # =====================================================================
        print("🏛️  Creating/Checking tourist points...")
        
        # Charyn Canyon
        charyn_canyon, _ = get_or_create(db, TouristPoint, slug="charyn-canyon", defaults={
            "name": "Charyn Canyon",
            "description": "Breathtaking canyon with unique rock formations, often called Kazakhstan's Grand Canyon.",
            "image_url": "https://i.natgeofe.com/n/65b5d84b-c44e-41d0-8ee9-5295e1e6eba5/silkroad_shutterstock_1236828025_HR.jpg",
            "latitude": 43.3500,
            "longitude": 79.0833,
            "region_id": almaty_region.id,
            "category_id": canyon_category.id,
            "elevation_m": 850,
            "best_season": "Apr - Oct",
            "accessibility": "Open Daily, 4WD Recommended"
        })

        # Kolsai Lake
        kolsai_lake, _ = get_or_create(db, TouristPoint, slug="kolsai-lake", defaults={
            "name": "Кольсайские Озера",
            "description": "Одно из самых потрясающих природных чудес Казахстана, расположенное в самом сердце Тянь-Шаня.",
            "image_url": "https://img1.wsimg.com/isteam/ip/54df45e4-dabc-47fa-93b4-6fad1ac0fd0f/E6A7CDFF-427E-499F-B530-9CD07318FD1E.jpeg",
            "latitude": 42.98443,
            "longitude": 78.32479,
            "region_id": almaty_region.id,
            "category_id": lake_category.id,
            "best_season": "May - September",
        })
        
        # Mausoleum of Khoja Ahmed Yasawi
        mausoleum_yasawi, _ = get_or_create(db, TouristPoint, slug="mausoleum-yasawi", defaults={
            "name": "Мавзолей Хожаи Ахмед Ясави",
            "description": "Мавзолей Хожаи Ахмед Ясави - это исторический памятник, расположенный в городе Туракстан, Казахстане.",
            "image_url": "https://ticketon.kz/files/media/mavzoley_hodzhi_ahmeda_yasavi_4.jpg",
            "latitude": 43.297636,
            "longitude": 68.271044,
            "region_id": turkestan_region.id,
            "category_id": monument_category.id,
            "elevation_m": 160,
            "best_season": "Year-round",
            "accessibility": "Open Daily (UNESCO Site)"
        })
        
        # Aksu-Zhabagly Nature Reserve
        aksu_zhabagly, _ = get_or_create(db, TouristPoint, slug="aksu-zhabagly", defaults={
            "name": "Аксу-Жабаглы",
            "description": "Аксу-Жабаглы - это национальный парк, расположенный в Казахстане.",
            "image_url": "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800",
            "latitude": 42.5167,
            "longitude": 70.5333,
            "region_id": turkestan_region.id,
            "category_id": reserve_category.id,
            "elevation_m": 2700,
            "best_season": "May - Sep",
            "accessibility": "Permit Required"
        })

        # --- NEW POINTS FROM DOC ---

        # Shymbulak
        shymbulak, created = get_or_create(db, TouristPoint, slug="shymbulak", defaults={
            "name": "Шымбулак (Shymbulak)",
            "description": "Популярный горнолыжный курорт в Алматы. Расположен в живописном ущелье Заилийского Алатау.",
            "image_url": "https://shymbulak.com/assets/images/about/offer.jpg",
            "latitude": 43.1250,
            "longitude": 77.0805,
            "region_id": almaty_region.id,
            "category_id": mountain_category.id,
            "elevation_m": 2260,
            "best_season": "Nov - Mar (Ski), May - Oct (Hike)",
            "accessibility": "Cable Car from Medeu"
        })
        if created: print("   + Created Shymbulak")

        # Tanbaly Tas (Using user provided data/slug)
        tanbaly_tas, created = get_or_create(db, TouristPoint, slug="tanbaly-tas", defaults={
            "name": "Танбалы Тас",
            "description": "Урочище у реки Или в 120 км к северу от города Алматы, где на скалах сохранилось множество петроглифов.",
            "image_url": "https://sxodim.com/uploads/posts/2023/06/21/optimized/b9539d8a934f5e3f73c3abb5d1121caa_1400x790-q-85.jpg",
            "latitude": 44.09287445555237,
            "longitude": 76.99232934719822,
            "region_id": almaty_region.id,
            "category_id": monument_category.id
        })
        if created: print("   + Created Tanbaly Tas")

        # Shymkent Fortress
        shymkent_fortress, created = get_or_create(db, TouristPoint, slug="shymkent-fortress", defaults={
            "name": "Шымкенсткая Крепость (Цитадель)",
            "description": "Историко-культурный комплекс «Цитадель Шымкала» — главная достопримечательность, расположенная в старой части города Шымкент.",
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/Citadel_Shymkent.jpg/800px-Citadel_Shymkent.jpg",
            "latitude": 42.306443, 
            "longitude": 69.594719,
            "region_id": turkestan_region.id,
            "category_id": fortress_category.id,
            "best_season": "Year-round",
            "accessibility": "Open Daily (UNESCO Site)"
        })
        if created: print("   + Created Shymkent Fortress")

        print(f"   ✓ Checked/Created tourist points")
        
        # =====================================================================
        # 6. CREATE POINT NODES (Last-mile access)
        # =====================================================================
        print("🚶 Creating/Checking last-mile access points...")
        
        def add_point_node_if_not_exists(tourist_point_id, node_id, access_type, **kwargs):
            exists = db.query(PointNode).filter_by(
                tourist_point_id=tourist_point_id,
                node_id=node_id,
                access_type=access_type
            ).first()
            if not exists:
                pn = PointNode(
                    tourist_point_id=tourist_point_id,
                    node_id=node_id,
                    access_type=access_type,
                    **kwargs
                )
                db.add(pn)
                db.commit()

        # Charyn Canyon - accessible from Almaty
        add_point_node_if_not_exists(charyn_canyon.id, almaty_city.id, AccessType.CAR, distance_km=215, time_minutes=180, cost=8000, description="Drive or take organized tour from Almaty. Best visited as day trip.")
        
        # Mausoleum - accessible from Turkestan city center
        add_point_node_if_not_exists(mausoleum_yasawi.id, turkestan_city.id, AccessType.TAXI, distance_km=2.3, time_minutes=7, cost=500, description="Short taxi ride from Turkestan city center.")
        add_point_node_if_not_exists(mausoleum_yasawi.id, turkestan_city.id, AccessType.WALK, distance_km=2.0, time_minutes=25, cost=0, description="Pleasant walk from city center.")
        
        # Aksu-Zhabagly
        # From Taraz
        add_point_node_if_not_exists(aksu_zhabagly.id, taraz_city.id, AccessType.CAR, distance_km=85, time_minutes=90, cost=5000, description="Drive from Taraz.")
        # From Shymkent (existing was Shymkent City)
        add_point_node_if_not_exists(aksu_zhabagly.id, shymkent_city.id, AccessType.CAR, distance_km=100, time_minutes=105, cost=6000, description="Alternative access from Shymkent.")
        
        # --- NEW POINT NODES FROM DOC ---

        # 1) Kolsai (Adding if missing)
        add_point_node_if_not_exists(kolsai_lake.id, almaty_city.id, AccessType.TAXI, distance_km=300, time_minutes=240, cost=25000, description="Taxi from Almaty (Kolsai).")

        # 2) Shymbulak
        add_point_node_if_not_exists(shymbulak.id, almaty_city.id, AccessType.BUS, distance_km=25, time_minutes=60, cost=600, description="Bus #12 from Kazakhstan Hotel to Medeu, then Cable Car.")
        add_point_node_if_not_exists(shymbulak.id, almaty_city.id, AccessType.TAXI, distance_km=25, time_minutes=40, cost=3000, description="Taxi to Medeu/Shymbulak.")

        # 3) Tanbaly Tas
        # Konayev -> Tanbaly Tas (Taxi)
        add_point_node_if_not_exists(tanbaly_tas.id, konayev_city.id, AccessType.TAXI, distance_km=50, time_minutes=40, cost=5000, description="Taxi from Konayev to Tanbaly Tas.")
        # Direct from Almaty (Taxi)
        add_point_node_if_not_exists(tanbaly_tas.id, almaty_city.id, AccessType.TAXI, distance_km=120, time_minutes=90, cost=10000, description="Direct Taxi from Almaty to Tanbaly Tas.")

        # 4) Shymkent Fortress
        add_point_node_if_not_exists(shymkent_fortress.id, shymkent_city.id, AccessType.BUS, distance_km=5, time_minutes=20, cost=100, description="Local city bus to Ordabasy square.")
        add_point_node_if_not_exists(shymkent_fortress.id, shymkent_city.id, AccessType.WALK, distance_km=3, time_minutes=40, cost=0, description="Walkable from city center.")

        print(f"   ✓ Checked/Created last-mile access points")
        
        # =====================================================================
        # SUMMARY
        # =====================================================================
        print("\n" + "="*70)
        print("✅ Database seeding/update completed successfully!")
        print("="*70)
    
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        db.rollback()
        raise
    
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
