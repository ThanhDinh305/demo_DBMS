# Hệ Thống Modern GIS Dashboard

Hệ thống cung cấp giải pháp nhập dữ liệu địa lý hình học (shapefile) vào cơ sở dữ liệu không gian PostgreSQL/PostGIS và hiển thị trực quan thông qua bản đồ web.

## Cấu Trúc Dự Án
- `main.py`: Khởi tạo REST API bằng FastAPI và phục vụ giao diện trực tiếp (port 3000).
- `import_data.py`: Đọc dữ liệu từ folder `data/`, đồng bộ hệ quy chiếu VN-2000 về WGS84, thêm khóa chính (Primary Key) và tự động insert vào database PostGIS.
- `index.html`: Giao diện tương tác GIS phía client (Leaflet).
- `data/`: Thư mục lưu trữ tập tin Shapefile đầu vào (`.shp`).
- `requirements.txt`: Các thư viện phụ thuộc.

## Hướng Dẫn Cài Đặt và Khởi Chạy

### 1. Chuẩn bị Cơ Sở Dữ Liệu
Tạo database tên `demo` thông qua PostgreSQL và kích hoạt extension không gian:
```sql
CREATE EXTENSION postgis;
```

### 2. Thiết Lập Môi Trường
Tiến hành cài đặt thư viện tại Terminal/CMD:
```bash
pip install -r requirements.txt
```

### 3. Nạp Dữ Liệu (Import Data)
Thực thi lệnh nhập shapefile tự động vào cơ sở dữ liệu:
```bash
python import_data.py
```

### 4. Vận Hành Khởi Chạy (Run Server)
Mở một cửa sổ Terminal mới và kích hoạt máy chủ kết nối:
```bash
python main.py
```
> Truy cập `http://localhost:3000` trên trình duyệt để sử dụng ứng dụng. Tại đây bạn có thể thao tác lọc lớp dữ liệu (Building, Road, Garbage) và xóa đối tượng động (CRUD).