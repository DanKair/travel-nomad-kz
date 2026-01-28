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
            name="Almaty Region",
            description="Largest region in Kazakhstan, home to Almaty city and stunning natural attractions"
        )
        
        turkestan_region = Region(
            name="Turkestan Region",
            description="Historical region with ancient cities and cultural heritage sites"
        )
        
        db.add_all([almaty_region, turkestan_region])
        db.commit()
        print(f"   ✓ Created {len([almaty_region, turkestan_region])} regions")
        
        # =====================================================================
        # 2. CREATE TOURIST POINT CATEGORIES
        # =====================================================================
        print("🏷️  Creating categories...")
        
        # Top-level categories
        nature_category = TouristPointCategory(name="Nature", parent_id=None)
        culture_category = TouristPointCategory(name="Culture & History", parent_id=None)
        
        db.add_all([nature_category, culture_category])
        db.commit()
        
        # Sub-categories
        canyon_category = TouristPointCategory(name="Canyon", parent_id=nature_category.id)
        reserve_category = TouristPointCategory(name="Nature Reserve", parent_id=nature_category.id)
        monument_category = TouristPointCategory(name="Historical Monument", parent_id=culture_category.id)
        
        db.add_all([canyon_category, reserve_category, monument_category])
        db.commit()
        print(f"   ✓ Created 5 categories (2 parent, 3 child)")
        
        # =====================================================================
        # 3. CREATE NODES (Transportation locations)
        # =====================================================================
        print("🚉 Creating transportation nodes...")
        
        # Almaty
        almaty_city = Node(
            name="Almaty",
            slug="almaty",
            latitude=43.2220,
            longitude=76.8512,
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
            image_url="https://images.unsplash.com/photo-1559827260-dc66d52bef19?w=800",
            latitude=43.3500,
            longitude=79.0833,
            region_id=almaty_region.id,
            category_id=canyon_category.id
        )
        
        # Mausoleum of Khoja Ahmed Yasawi
        mausoleum_yasawi = TouristPoint(
            name="Mausoleum of Khoja Ahmed Yasawi",
            slug="mausoleum-yasawi",
            description="UNESCO World Heritage Site, masterpiece of medieval architecture built by Timur (Tamerlane) in the late 14th century. The mausoleum features a stunning turquoise dome and represents the finest example of Timurid architecture. It was one of the most important pilgrimage sites for Central Asian Muslims.",
            image_url="https://images.unsplash.com/photo-1588239034647-25783cbfb8b1?w=800",
            latitude=43.2967,
            longitude=68.2608,
            region_id=turkestan_region.id,
            category_id=monument_category.id
        )
        
        # Aksu-Zhabagly Nature Reserve
        aksu_zhabagly = TouristPoint(
            name="Aksu-Zhabagly Nature Reserve",
            slug="aksu-zhabagly",
            description="Oldest nature reserve in Central Asia with diverse flora and fauna, established in 1926. Home to over 1,300 plant species, 267 bird species, and rare animals like snow leopards and bears. The reserve spans mountain ranges from 1,200 to 4,280 meters elevation.",
            image_url="https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800",
            latitude=42.5167,
            longitude=70.5333,
            region_id=turkestan_region.id,
            category_id=reserve_category.id
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
