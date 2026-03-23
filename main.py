from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
import os

app = FastAPI(
    title="Modern GIS API",
    description="API xử lý dữ liệu PostGIS tích hợp bản đồ",
    version="1.0.0"
)

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cấu hình Database
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:123456@localhost:5432/demo"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency để lấy DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Danh sách bảng cho phép truy cập
ALLOWED_TABLES = ["bounds", "building", "road", "garbadge", "instruction_generated"]

@app.get("/")
def read_root():
    """
    Trả về giao diện bản đồ index.html trực tiếp từ Server
    """
    return FileResponse("index.html")

from typing import Optional

@app.get("/api/{table}")
def get_geojson(table: str, nature: Optional[str] = None, nblanes: Optional[int] = None, db: Session = Depends(get_db)):
    """
    Lấy toàn bộ dữ liệu của một bảng dưới dạng GeoJSON FeatureCollection, hỗ trợ lọc (filter)
    """
    if table not in ALLOWED_TABLES:
        raise HTTPException(status_code=404, detail="Bảng không hợp lệ")

    try:
        # Detect the geometry column name
        col_query = text(f"""
            SELECT f_geometry_column 
            FROM geometry_columns 
            WHERE f_table_schema = 'public' AND f_table_name = :table_name
            LIMIT 1;
        """)
        col_result = db.execute(col_query, {"table_name": table}).fetchone()
        geom_col = col_result[0] if col_result else "geometry"

        # Build dynamic WHERE clause based on filters
        where_clauses = []
        params = {}
        
        if table == "building" and nature:
            where_clauses.append('t."NATURE" = :nature')
            params["nature"] = nature
            
        if table == "road" and nblanes is not None:
            where_clauses.append('t."nbLanes" = :nblanes')
            params["nblanes"] = nblanes
            
        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        query = text(f"""
            SELECT jsonb_build_object(
                'type', 'FeatureCollection',
                'features', COALESCE(jsonb_agg(
                    jsonb_build_object(
                        'type', 'Feature',
                        'geometry', ST_AsGeoJSON(ST_Transform(t."{geom_col}", 4326))::jsonb,
                        'properties', to_jsonb(t) - '{geom_col}'
                    )
                ), '[]'::jsonb)
            )
            FROM public.{table} AS t
            {where_sql};
        """)
        
        result = db.execute(query, params).fetchone()
        return result[0] if result and result[0] else {"type": "FeatureCollection", "features": []}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/{table}/all")
def delete_all_features(table: str, db: Session = Depends(get_db)):
    """
    Xóa toàn bộ dữ liệu trong một bảng
    """
    if table not in ALLOWED_TABLES:
        raise HTTPException(status_code=404, detail="Bảng không hợp lệ")

    try:
        delete_query = text(f'DELETE FROM public.{table}')
        result = db.execute(delete_query)
        db.commit()
        return {"message": f"Đã xóa toàn bộ {result.rowcount} đối tượng khỏi bảng {table}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/{table}/{fid}")
def delete_feature(table: str, fid: int, db: Session = Depends(get_db)):
    """
    Xóa 1 đối tượng khỏi bản đồ theo gid
    """
    if table not in ALLOWED_TABLES:
        raise HTTPException(status_code=404, detail="Bảng không hợp lệ")

    try:
        delete_query = text(f'DELETE FROM public.{table} WHERE gid = :fid')
        result = db.execute(delete_query, {"fid": fid})
        db.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy đối tượng gid={fid}")
        return {"message": f"Đã xóa thành công đối tượng {fid} khỏi bảng {table}"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
