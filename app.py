from flask import Flask, jsonify
from flask_cors import CORS
from sqlalchemy import create_engine, text
app = Flask(__name__)
CORS(app) 
engine = create_engine('postgresql://postgres:123456@localhost:5432/demo')

@app.route('/api/<table>', methods=['GET'])
def get_geojson(table):
    allowed_tables = ['bounds', 'building', 'road', 'garbadge', 'instruction-generated']
    if table not in allowed_tables:
        return jsonify({"error": "Bảng không hợp lệ"}), 404

    try:
        with engine.connect() as conn:
            # Ép kiểu dữ liệu về VN-2000 (3405) sau đó dịch sang WGS84 (4326)
            query = text(f"""
                SELECT jsonb_build_object(
                    'type', 'FeatureCollection',
                    'features', COALESCE(jsonb_agg(
                        jsonb_build_object(
                            'type', 'Feature',
                            'geometry', ST_AsGeoJSON(ST_Transform(ST_SetSRID(t.geom, 3405), 4326))::jsonb,
                            'properties', to_jsonb(t) - 'geom'
                        )
                    ), '[]'::jsonb)
                )
                FROM public."{table}" AS t;
            """)
            result = conn.execute(query).fetchone()
            return jsonify(result[0] if result[0] else {"type": "FeatureCollection", "features": []})
            
    except Exception as e:
        print(f"Lỗi: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("Backend đang chạy tại: http://localhost:3000")
    app.run(port=3000, debug=True)