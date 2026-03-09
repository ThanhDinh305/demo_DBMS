# Báo cáo demo DB

## 1. Cấu trúc thư mục
- `db.sql`: File backup database
- `data/`: Chứa các file Shapefile gốc .shp dùng để import vào database.
- `app.py`: Code API backend bằng Python.
- `index.html`: Giao diện web.
- `requirements.txt`: Các thư viện Python cần thiết để chạy code.

## 2. Các bước cài đặt và chạy code

### Bước 1: Chuẩn bị Database (PostgreSQL + PostGIS)
1. Tạo một database mới .
2. Chạy câu lệnh sql sau để bật extension GIS: `CREATE EXTENSION postgis;`
3. Dùng tool **PostGIS Shapefile Import/Export Manager** (có sẵn khi cài PostGIS) để import file trong thư mục `data/` vào.

### Bước 2: Chạy Backend (Python)
1. Mở Terminal / CMD ở thư mục code, chạy lệnh cài thư viện:
   `pip install -r requirements.txt`
2. Mở file `app.py` lên và chạy backend bằng lệnh: 
   `python app.py`
3. Nếu thấy báo chạy ở `http://localhost:3000` là ok.

### Bước 3: Chạy Frontend (Web)
Chỉ cần nhấp đúp mở trực tiếp file `index.html` bằng trình duyệt (Chrome, Edge) là bản đồ sẽ load lên. 