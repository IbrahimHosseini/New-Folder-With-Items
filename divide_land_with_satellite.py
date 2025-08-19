import matplotlib.pyplot as plt
from shapely.geometry import Polygon, LineString
from shapely.ops import split
from xml.dom import minidom
import contextily as ctx
from pyproj import Transformer
import math

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

# === Step 3: Calculate Measurements ===
def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points using Haversine formula"""
    R = 6371000  # Earth's radius in meters
    
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

def calculate_quarter_measurements(quarter_poly):
    """Calculate area and perimeter of a quarter"""
    # Calculate area in square meters
    area_m2 = quarter_poly.area * 111320 * 111320 * math.cos(math.radians(quarter_poly.centroid.y))
    
    # Calculate perimeter in meters
    coords = list(quarter_poly.exterior.coords)
    perimeter_m = 0
    for i in range(len(coords) - 1):
        lat1, lon1 = coords[i][1], coords[i][0]
        lat2, lon2 = coords[i+1][1], coords[i+1][0]
        perimeter_m += haversine_distance(lat1, lon1, lat2, lon2)
    
    return area_m2, perimeter_m

# Calculate measurements for each quarter
quarter_measurements = []
total_area = 0
total_perimeter = 0

for i, quarter in enumerate(quarters):
    area, perimeter = calculate_quarter_measurements(quarter)
    quarter_measurements.append((area, perimeter))
    total_area += area
    total_perimeter += perimeter

# === Step 4: Plot with Satellite Map ===
fig, ax = plt.subplots(figsize=(14, 12))

# Try to add satellite imagery background
satellite_loaded = False
satellite_providers = [
    ("OpenStreetMap", ctx.providers.OpenStreetMap.Mapnik),  # More reliable
    ("Esri World Imagery", ctx.providers.Esri.WorldImagery),
    ("Esri World Physical", ctx.providers.Esri.WorldPhysical),
    ("Esri World Terrain", ctx.providers.Esri.WorldTerrain),
]

for provider_name, provider in satellite_providers:
    try:
        print(f"🔄 Trying to load {provider_name}...")
        # Use Web Mercator projection for better tile compatibility
        ctx.add_basemap(ax, crs="EPSG:3857", source=provider, zoom=12)
        print(f"✅ {provider_name} loaded successfully!")
        satellite_loaded = True
        if "Imagery" in provider_name or "Physical" in provider_name or "Terrain" in provider_name:
            print("🛰️  Satellite/Imagery background loaded!")
        else:
            print("🗺️  Map background loaded!")
        break
    except Exception as e:
        print(f"❌ Failed to load {provider_name}: {str(e)[:100]}...")
        continue

if not satellite_loaded:
    print("⚠️  Could not load any map background. Proceeding with basic plot...")

# Transform coordinates to Web Mercator for plotting
transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)

# ... existing code ...
# Plot the divided quarters with measurements
for i, (poly, (area, perimeter)) in enumerate(zip(quarters, quarter_measurements)):
    x, y = poly.exterior.xy
    # Transform coordinates
    x_transformed, y_transformed = transformer.transform(x, y)
    ax.fill(x_transformed, y_transformed, edgecolor='red', facecolor='none', linewidth=2, 
            label=f'Quarter {i+1}: {area:.0f} m², {perimeter:.0f} m')
    
    # Add area and perimeter text on each quarter
    quarter_centroid = poly.centroid
    quarter_centroid_transformed = transformer.transform(quarter_centroid.x, quarter_centroid.y)
    
    # Add area text
    ax.text(quarter_centroid_transformed[0], quarter_centroid_transformed[1] + 50, 
            f'Area: {area:.0f} m²\n({area/10000:.2f} ha)', 
            ha='center', va='center', fontsize=10, fontweight='bold',
            bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8, edgecolor='red'))
    
    # Add perimeter text below
    ax.text(quarter_centroid_transformed[0], quarter_centroid_transformed[1] - 50, 
            f'Perimeter: {perimeter:.0f} m', 
            ha='center', va='center', fontsize=9, fontweight='bold',
            bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.8, edgecolor='blue'))

# Mark the centroid
centroid_transformed = transformer.transform(centroid.x, centroid.y)
ax.plot(centroid_transformed[0], centroid_transformed[1], 'bo', markersize=8, label='Centroid')

# Add total area and perimeter info on the image
total_text = f'TOTAL AREA: {total_area:.0f} m² ({total_area/10000:.2f} ha)\nTOTAL PERIMETER: {total_perimeter:.0f} m'
ax.text(0.02, 0.98, total_text, transform=ax.transAxes, fontsize=12, fontweight='bold',
        verticalalignment='top', bbox=dict(boxstyle="round,pad=0.5", facecolor='yellow', alpha=0.9, edgecolor='black'))

# Set map limits with transformed coordinates
# Transform the four corner points individually
minx_trans, miny_trans = transformer.transform(minx, miny)
maxx_trans, maxy_trans = transformer.transform(maxx, maxy)
ax.set_xlim(minx_trans - 100, maxx_trans + 100)
ax.set_ylim(miny_trans - 100, maxy_trans + 100)

# Add legend and labels
ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
ax.set_title('Land Divided into Quarters - Satellite View\n' + 
             f'Total Area: {total_area:.0f} m² | Total Perimeter: {total_perimeter:.0f} m', 
             fontsize=14, fontweight='bold')


# Save output
ax.axis('off')
plt.tight_layout()
plt.savefig("divided_land_satellite.png", dpi=300, bbox_inches='tight')
print("✅ Output saved as: divided_land_satellite.png")

# Print detailed measurements
print("\n📏 **اندازه‌گیری قطعات زمین:**")
print("=" * 50)
for i, (area, perimeter) in enumerate(quarter_measurements):
    print(f"قطعه {i+1}:")
    print(f"  مساحت: {area:.0f} متر مربع ({area/10000:.2f} هکتار)")
    print(f"  محیط: {perimeter:.0f} متر")
    print()

print(f"📊 **کل زمین:**")
print(f"  مساحت کل: {total_area:.0f} متر مربع ({total_area/10000:.2f} هکتار)")
print(f"  محیط کل: {total_perimeter:.0f} متر")