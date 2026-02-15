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

from app.database import SessionLocal, init_db
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
        # =====================================================================
        # 1. CREATE REGIONS
        # =====================================================================
        print("📍 Creating regions...")
        
        almaty_region = Region(
            name="Алматинская Область",
            description="Largest region in Kazakhstan, home to Almaty city and stunning natural attractions"
        )
        
        turkestan_region = Region(
            name="Туркестанская Область",
            description="Historical region with ancient cities and cultural heritage sites"
        )

        zhambyl_region = Region(
            name="Жамбылская Область",
            description="Historical region with ancient cities and cultural heritage sites"
        )

        kyzylorda_region = Region(
            name="Кызылординская Область",
            description="Historical region with ancient cities and cultural heritage sites"
        )

        
        
        db.add_all([almaty_region, turkestan_region, zhambyl_region, kyzylorda_region])
        db.commit()
        print(f"   ✓ Created 4 regions")
        
        # =====================================================================
        # 2. CREATE TOURIST POINT CATEGORIES
        # =====================================================================
        print("🏷️  Creating categories...")
        
        # Top-level categories
        nature_category = TouristPointCategory(name="Природа", parent_id=None)
        culture_category = TouristPointCategory(name="Культура & История", parent_id=None)
        
        db.add_all([nature_category, culture_category])
        db.commit()
        
        # Sub-categories
        canyon_category = TouristPointCategory(name="Каньон", parent_id=nature_category.id)
        reserve_category = TouristPointCategory(name="Заповедник", parent_id=nature_category.id)
        lake_category = TouristPointCategory(name="Озеро", parent_id=nature_category.id)
        park_category = TouristPointCategory(name="Парк", parent_id=nature_category.id)
        waterfall_category = TouristPointCategory(name="Водопад", parent_id=nature_category.id)
        museum_category = TouristPointCategory(name="Музей", parent_id=culture_category.id)
        monument_category = TouristPointCategory(name="Исторический памятник", parent_id=culture_category.id)
        sacred_category = TouristPointCategory(name="Священное место", parent_id=culture_category.id)
        
        db.add_all([canyon_category, lake_category, park_category, waterfall_category, museum_category, monument_category, reserve_category, sacred_category])
        db.commit()
        print(f"   ✓ Created 7 categories (2 parent, 5 child)")
        
        # =====================================================================
        # 3. CREATE NODES (Transportation locations)
        # =====================================================================
        print("🚉 Creating transportation nodes...")
        
        # Almaty
        almaty_city = Node(
            name="Almaty",
            slug="almaty",
            latitude=43.233503,
            longitude=76.921767,
            node_type=NodeType.CITY
        )
        
        almaty_railway = Node(
            name="Almaty-2 Railway Station",
            slug="almaty-railway",
            latitude=43.2566,
            longitude=76.9286,
            node_type=NodeType.STATION
        )
        
        # Shymkent
        shymkent_city = Node(
            name="Shymkent",
            slug="shymkent",
            latitude=42.3000,
            longitude=69.6000,
            node_type=NodeType.CITY
        )
        
        # Turkestan
        turkestan_city = Node(
            name="Turkestan",
            slug="turkestan",
            latitude=43.2983,
            longitude=68.2517,
            node_type=NodeType.CITY
        )
        
        # Taraz
        taraz_city = Node(
            name="Taraz",
            slug="taraz",
            latitude=42.9000,
            longitude=71.3667,
            node_type=NodeType.CITY
        )
        
        db.add_all([almaty_city, almaty_railway, shymkent_city, turkestan_city, taraz_city])
        db.commit()
        print(f"   ✓ Created 5 transportation nodes")
        
        # =====================================================================
        # 4. CREATE TRANSPORT SEGMENTS (Routes between nodes)
        # =====================================================================
        print("🚂 Creating transport segments...")
        
        segments = []
        
        # Almaty → Shymkent (Train)
        segments.append(TransportSegment(
            from_node_id=almaty_railway.id,
            to_node_id=shymkent_city.id,
            transport_mode=TransportMode.TRAIN,
            distance_km=1082,
            time_minutes=840,  # 14 hours
            cost=6000,  # KZT
            comfort_score=7.0,
            co2_kg=45.0
        ))
        
        # Almaty → Shymkent (Bus)
        segments.append(TransportSegment(
            from_node_id=almaty_city.id,
            to_node_id=shymkent_city.id,
            transport_mode=TransportMode.BUS,
            distance_km=690,
            time_minutes=720,  # 12 hours
            cost=4000,  # KZT
            comfort_score=5.0,
            co2_kg=25.0
        ))
        
        # Shymkent → Turkestan (Bus)
        segments.append(TransportSegment(
            from_node_id=shymkent_city.id,
            to_node_id=turkestan_city.id,
            transport_mode=TransportMode.BUS,
            distance_km=180,
            time_minutes=120,  # 2 hours
            cost=1500,  # KZT
            comfort_score=6.0,
            co2_kg=8.0
        ))
        
        # Shymkent → Turkestan (Marshrutka - faster but less comfortable)
        segments.append(TransportSegment(
            from_node_id=shymkent_city.id,
            to_node_id=turkestan_city.id,
            transport_mode=TransportMode.MARSHRUTKA,
            distance_km=180,
            time_minutes=100,  # 1h 40min
            cost=1200,  # KZT
            comfort_score=4.0,
            co2_kg=12.0
        ))
        
        # Shymkent → Taraz (Bus)
        segments.append(TransportSegment(
            from_node_id=shymkent_city.id,
            to_node_id=taraz_city.id,
            transport_mode=TransportMode.BUS,
            distance_km=280,
            time_minutes=210,  # 3.5 hours
            cost=2000,  # KZT
            comfort_score=6.0,
            co2_kg=15.0
        ))
        
        # Almaty → Taraz (Bus)
        segments.append(TransportSegment(
            from_node_id=almaty_city.id,
            to_node_id=taraz_city.id,
            transport_mode=TransportMode.BUS,
            distance_km=450,
            time_minutes=360,  # 6 hours
            cost=3000,  # KZT
            comfort_score=6.5,
            co2_kg=18.0
        ))
        
        db.add_all(segments)
        db.commit()
        print(f"   ✓ Created {len(segments)} transport segments")
        
        # =====================================================================
        # 5. CREATE TOURIST POINTS (Destinations)
        # =====================================================================
        print("🏛️  Creating tourist points...")
        
        # Charyn Canyon
        charyn_canyon = TouristPoint(
            name="Charyn Canyon",
            slug="charyn-canyon",
            description="Breathtaking canyon with unique rock formations, often called Kazakhstan's Grand Canyon. The canyon stretches for 154 kilometers along the Charyn River gorge in northern Tian Shan. Wind and water erosion have created spectacular rock formations including the famous Valley of Castles.",
            image_url="https://i.natgeofe.com/n/65b5d84b-c44e-41d0-8ee9-5295e1e6eba5/silkroad_shutterstock_1236828025_HR.jpg",
            latitude=43.3500,
            longitude=79.0833,
            region_id=almaty_region.id,
            category_id=canyon_category.id,
            elevation_m=850,
            best_season="Apr - Oct",
            accessibility="Open Daily, 4WD Recommended"
        )

        # Kolsai Lake
        kolsai_lake = TouristPoint(
            name="Кольсайские Озера",
            slug="kolsai-lake",
            description="Одно из самых потрясающих природных чудес Казахстана, расположенное в самом сердце Тянь-Шаня. Озеро окружено высокими вершинами и открывает захватывающие виды на окружающий ландшафт. Это популярное место для пеших прогулок, пикников и наблюдения за дикой природой.",
            image_url="https://img1.wsimg.com/isteam/ip/54df45e4-dabc-47fa-93b4-6fad1ac0fd0f/E6A7CDFF-427E-499F-B530-9CD07318FD1E.jpeg",
            latitude=42.98443,
            longitude=78.32479,
            region_id=almaty_region.id,
            category_id=lake_category.id,
            best_season="May - September",
        )
        
        # Mausoleum of Khoja Ahmed Yasawi
        mausoleum_yasawi = TouristPoint(
            name="Мавзолей Хожаи Ахмед Ясави",
            slug="mausoleum-yasawi",
            description="Мавзолей Хожаи Ахмед Ясави - это исторический памятник, расположенный в городе Туракстан, Казахстане. Это место имеет большое культурное значение и является одним из самых популярных туристических объектов региона.",
            image_url="https://ticketon.kz/files/media/mavzoley_hodzhi_ahmeda_yasavi_4.jpg",
            latitude=43.2967,
            longitude=68.2608,
            region_id=turkestan_region.id,
            category_id=monument_category.id,
            elevation_m=160,
            best_season="Year-round",
            accessibility="Open Daily (UNESCO Site)"
        )
        
        # Aksu-Zhabagly Nature Reserve
        aksu_zhabagly = TouristPoint(
            name="Аксу-Жабаглы",
            slug="aksu-zhabagly",
            description="Аксу-Жабаглы - это национальный парк, расположенный в Казахстане. Это место имеет большое культурное значение и является одним из самых популярных туристических объектов региона.",
            image_url="https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800",
            latitude=42.5167,
            longitude=70.5333,
            region_id=turkestan_region.id,
            category_id=reserve_category.id,
            elevation_m=2700,
            best_season="May - Sep",
            accessibility="Permit Required"
        )
        
        db.add_all([charyn_canyon, mausoleum_yasawi, aksu_zhabagly])
        db.commit()
        print(f"   ✓ Created 3 tourist points")
        
        # =====================================================================
        # 6. CREATE POINT NODES (Last-mile access)
        # =====================================================================
        print("🚶 Creating last-mile access points...")
        
        point_nodes = []
        
        # Charyn Canyon - accessible from Almaty
        point_nodes.append(PointNode(
            tourist_point_id=charyn_canyon.id,
            node_id=almaty_city.id,
            access_type=AccessType.CAR,
            distance_km=215,
            time_minutes=180,  # 3 hours by car
            cost=8000,  # Car rental/taxi cost
            description="Drive or take organized tour from Almaty. Best visited as day trip."
        ))
        
        # Mausoleum - accessible from Turkestan city center
        point_nodes.append(PointNode(
            tourist_point_id=mausoleum_yasawi.id,
            node_id=turkestan_city.id,
            access_type=AccessType.TAXI,
            distance_km=2.3,
            time_minutes=7,
            cost=500,  # Local taxi
            description="Short taxi ride from Turkestan city center. Also walkable in 25 minutes."
        ))
        
        point_nodes.append(PointNode(
            tourist_point_id=mausoleum_yasawi.id,
            node_id=turkestan_city.id,
            access_type=AccessType.WALK,
            distance_km=2.0,
            time_minutes=25,
            cost=0,
            description="Pleasant walk from city center through historical district."
        ))
        
        # Aksu-Zhabagly - accessible from Taraz
        point_nodes.append(PointNode(
            tourist_point_id=aksu_zhabagly.id,
            node_id=taraz_city.id,
            access_type=AccessType.CAR,
            distance_km=85,
            time_minutes=90,
            cost=5000,  # Car/taxi cost
            description="Drive from Taraz. Reserve entrance requires advance booking."
        ))
        
        # Aksu-Zhabagly - also accessible from Shymkent
        point_nodes.append(PointNode(
            tourist_point_id=aksu_zhabagly.id,
            node_id=shymkent_city.id,
            access_type=AccessType.CAR,
            distance_km=100,
            time_minutes=105,
            cost=6000,
            description="Alternative access from Shymkent. Slightly longer but better road."
        ))
        
        db.add_all(point_nodes)
        db.commit()
        print(f"   ✓ Created {len(point_nodes)} last-mile access points")
        
        # =====================================================================
        # SUMMARY
        # =====================================================================
        print("\n" + "="*70)
        print("✅ Database seeding completed successfully!")
        print("="*70)
        print(f"📊 Summary:")
        print(f"   • Regions: 2")
        print(f"   • Categories: 5 (2 parent, 3 child)")
        print(f"   • Transportation Nodes: 5")
        print(f"   • Transport Segments: {len(segments)}")
        print(f"   • Tourist Points: 3")
        print(f"   • Last-Mile Access Points: {len(point_nodes)}")
        print("\n💡 Try example route queries:")
        print("   GET /routes?from_node=almaty&to_tourist_point=mausoleum-yasawi")
        print("   GET /routes?from_node=almaty&to_tourist_point=charyn-canyon")
        print("   GET /routes?from_node=shymkent&to_tourist_point=aksu-zhabagly")
        print("="*70 + "\n")
    
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        db.rollback()
        raise
    
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
