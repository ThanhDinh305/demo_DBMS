import os
import geopandas as gpd
from sqlalchemy import create_engine
import shutil

# Cấu hình kết nối (Docker Postgres)
DB_USER = "postgres"
DB_PASS = "123456"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "demo"

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

DATA_DIR = "./data"

def import_shapefiles():
    if not os.path.exists(DATA_DIR):
        print(f"Lỗi: Không tìm thấy thư mục {DATA_DIR}")
        return

    for file in os.listdir(DATA_DIR):
        if file.endswith(".shp"):
            table_name = file.replace(".shp", "").replace("-", "_")
            file_path = os.path.join(DATA_DIR, file)
            
            print(f"Đang xử lý: {file} -> Bảng: {table_name}...")
            
            try:
                gdf = gpd.read_file(file_path)
                
                if gdf.crs is None:
                    print(f"  [INFO] Không có CRS, gán mặc định VN-2000 (EPSG:3405)")
                    gdf.set_crs(epsg=3405, inplace=True)
                
                # Chuyển đổi sang WGS84 (EPSG:4326) để hiển thị trên bản đồ
                gdf = gdf.to_crs(epsg=4326)
                
                # Thêm cột gid làm Primary Key
                gdf.insert(0, 'gid', range(1, len(gdf) + 1))
                gdf.to_postgis(table_name, engine, if_exists='replace', index=False)
                print(f"  [OK] Đã import xong bảng {table_name} ({len(gdf)} bản ghi)")
                
            except Exception as e:
                print(f"  [LỖI] Không thể import {file}: {e}")

if __name__ == "__main__":
    import_shapefiles()
    print("--- Hoàn tất! Dữ liệu đã sẵn sàng trong database 'demo' ---")
