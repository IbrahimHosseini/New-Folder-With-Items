
import matplotlib.pyplot as plt
from shapely.geometry import Polygon, LineString
from shapely.ops import split
from xml.dom import minidom
import contextily as ctx

# === Step 1: Load KML file ===
kml_file = "file.kml"  # Replace with your actual file name

doc = minidom.parse(kml_file)
coords = doc.getElementsByTagName("coordinates")[0].firstChild.data.strip()
coord_pairs = coords.split()
polygon_coords = [(float(lon), float(lat)) for lon, lat, *_ in (coord.split(',') for coord in coord_pairs)]

# === Step 2: Create Polygon and Split ===
polygon = Polygon(polygon_coords)
centroid = polygon.centroid

minx, miny, maxx, maxy = polygon.bounds
h_line = LineString([(minx, centroid.y), (maxx, centroid.y)])
v_line = LineString([(centroid.x, miny), (centroid.x, maxy)])

split1 = split(polygon, h_line)
quarters = []
for part in split1.geoms:
    split2 = split(part, v_line)
    quarters.extend(split2.geoms)

# === Step 3: Plot with Satellite Map ===
fig, ax = plt.subplots(figsize=(10, 10))

# Try to add satellite imagery background
satellite_loaded = False
satellite_providers = [
    ("Esri World Imagery", ctx.providers.Esri.WorldImagery),
    ("Esri World Physical", ctx.providers.Esri.WorldPhysical),
    ("Esri World Terrain", ctx.providers.Esri.WorldTerrain),
    ("OpenStreetMap", ctx.providers.OpenStreetMap.Mapnik)  # Fallback
]

for provider_name, provider in satellite_providers:
    try:
        print(f"🔄 Trying to load {provider_name}...")
        ctx.add_basemap(ax, crs="EPSG:4326", source=provider)
        print(f"✅ {provider_name} loaded successfully!")
        satellite_loaded = True
        if "Imagery" in provider_name or "Physical" in provider_name or "Terrain" in provider_name:
            print("🛰️  Satellite/Imagery background loaded!")
        break
    except Exception as e:
        print(f"❌ Failed to load {provider_name}: {str(e)[:100]}...")
        continue

if not satellite_loaded:
    print("⚠️  Could not load any satellite imagery. Proceeding with basic plot...")

# Plot the divided quarters
for i, poly in enumerate(quarters):
    x, y = poly.exterior.xy
    ax.fill(x, y, edgecolor='red', facecolor='none', linewidth=2, label=f'Quarter {i+1}')

# Mark the centroid
ax.plot(centroid.x, centroid.y, 'bo', markersize=8, label='Centroid')

# Set map limits
ax.set_xlim(minx - 0.0005, maxx + 0.0005)
ax.set_ylim(miny - 0.0005, maxy + 0.0005)

# Add legend and labels
ax.legend()
ax.set_title('Land Divided into Quarters - Satellite View', fontsize=14, fontweight='bold')
ax.set_xlabel('Longitude')
ax.set_ylabel('Latitude')

# Save output
ax.axis('off')
plt.savefig("divided_land_satellite.png", dpi=300, bbox_inches='tight')
print("✅ Output saved as: divided_land_satellite.png")
