from flask import Flask, jsonify, request
from flask_cors import CORS
from sqlalchemy import create_engine, text
from flasgger import Swagger
import json

app = Flask(__name__)
CORS(app)

swagger = Swagger(app, template={
    "swagger": "2.0",
    "info": {
        "title": "GIS API",
        "description": "API CRUD dữ liệu GeoJSON từ PostGIS",
        "version": "2.0.0"
    }
})

engine = create_engine('postgresql://postgres:123456@localhost:5432/demo')

ALLOWED_TABLES = ['bounds', 'building', 'road', 'garbadge', 'instruction-generated']

def validate_table(table):
    return table in ALLOWED_TABLES

def get_primary_key(conn, table):
    """Tự động lấy tên primary key của bảng"""
    result = conn.execute(text("""
        SELECT kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        WHERE tc.constraint_type = 'PRIMARY KEY'
          AND tc.table_schema = 'public'
          AND tc.table_name = :tbl
        LIMIT 1;
    """), {"tbl": table}).fetchone()
    return result[0] if result else "id"

def get_table_columns(conn, table):
    """Lấy danh sách cột (trừ geom và primary key)"""
    pk = get_primary_key(conn, table)
    result = conn.execute(text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = :tbl
          AND column_name NOT IN ('geom')
          AND column_name != :pk
        ORDER BY ordinal_position;
    """), {"tbl": table, "pk": pk}).fetchall()
    return pk, [r[0] for r in result]


# ─── GET ALL ───────────────────────────────────────────────────────────────────
@app.route('/api/<table>', methods=['GET'])
def get_geojson(table):
    """
    Lấy toàn bộ features dạng GeoJSON
    ---
    parameters:
      - name: table
        in: path
        type: string
        required: true
        enum: ['bounds', 'building', 'road', 'garbadge', 'instruction-generated']
    responses:
      200:
        description: Thành công
      404:
        description: Không tìm thấy bảng
    """
    if not validate_table(table):
        return jsonify({"error": "Bảng không hợp lệ"}), 404

    try:
        with engine.connect() as conn:
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
        return jsonify({"error": str(e)}), 500


# ─── GET ONE ───────────────────────────────────────────────────────────────────
@app.route('/api/<table>/<int:fid>', methods=['GET'])
def get_feature(table, fid):
    """
    Lấy 1 feature theo ID
    ---
    parameters:
      - name: table
        in: path
        type: string
        required: true
        enum: ['bounds', 'building', 'road', 'garbadge', 'instruction-generated']
      - name: fid
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Thành công
      404:
        description: Không tìm thấy
    """
    if not validate_table(table):
        return jsonify({"error": "Bảng không hợp lệ"}), 404

    try:
        with engine.connect() as conn:
            pk = get_primary_key(conn, table)
            query = text(f"""
                SELECT jsonb_build_object(
                    'type', 'Feature',
                    'geometry', ST_AsGeoJSON(ST_Transform(ST_SetSRID(t.geom, 3405), 4326))::jsonb,
                    'properties', to_jsonb(t) - 'geom'
                )
                FROM public."{table}" AS t
                WHERE t."{pk}" = :fid;
            """)
            result = conn.execute(query, {"fid": fid}).fetchone()
            if not result or not result[0]:
                return jsonify({"error": "Không tìm thấy feature"}), 404
            return jsonify(result[0])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── CREATE ────────────────────────────────────────────────────────────────────
@app.route('/api/<table>', methods=['POST'])
def create_feature(table):
    """
    Thêm 1 feature mới
    ---
    parameters:
      - name: table
        in: path
        type: string
        required: true
        enum: ['bounds', 'building', 'road', 'garbadge', 'instruction-generated']
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            geometry:
              type: object
            properties:
              type: object
    responses:
      201:
        description: Tạo thành công
      400:
        description: Dữ liệu không hợp lệ
    """
    if not validate_table(table):
        return jsonify({"error": "Bảng không hợp lệ"}), 404

    data = request.get_json()
    if not data or 'geometry' not in data:
        return jsonify({"error": "Thiếu trường 'geometry'"}), 400

    geometry = json.dumps(data['geometry'])
    properties = data.get('properties', {})

    try:
        with engine.begin() as conn:
            pk, cols = get_table_columns(conn, table)
            valid_props = {k: v for k, v in properties.items() if k in cols}

            if valid_props:
                col_names = ', '.join(f'"{c}"' for c in valid_props)
                col_placeholders = ', '.join(f':{c}' for c in valid_props)
                insert_sql = text(f"""
                    INSERT INTO public."{table}" (geom, {col_names})
                    VALUES (
                        ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326), 3405),
                        {col_placeholders}
                    )
                    RETURNING "{pk}";
                """)
                params = {"geom": geometry, **valid_props}
            else:
                insert_sql = text(f"""
                    INSERT INTO public."{table}" (geom)
                    VALUES (ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326), 3405))
                    RETURNING "{pk}";
                """)
                params = {"geom": geometry}

            result = conn.execute(insert_sql, params).fetchone()
            return jsonify({"message": "Tạo thành công", "id": result[0], "pk_column": pk}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── UPDATE ────────────────────────────────────────────────────────────────────
@app.route('/api/<table>/<int:fid>', methods=['PUT'])
def update_feature(table, fid):
    """
    Cập nhật feature theo ID
    ---
    parameters:
      - name: table
        in: path
        type: string
        required: true
        enum: ['bounds', 'building', 'road', 'garbadge', 'instruction-generated']
      - name: fid
        in: path
        type: integer
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            geometry:
              type: object
            properties:
              type: object
    responses:
      200:
        description: Cập nhật thành công
      404:
        description: Không tìm thấy
    """
    if not validate_table(table):
        return jsonify({"error": "Bảng không hợp lệ"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Không có dữ liệu"}), 400

    try:
        with engine.begin() as conn:
            pk, cols = get_table_columns(conn, table)

            # Kiểm tra tồn tại
            exists = conn.execute(
                text(f'SELECT 1 FROM public."{table}" WHERE "{pk}" = :fid'),
                {"fid": fid}
            ).fetchone()
            if not exists:
                return jsonify({"error": f"Không tìm thấy feature {pk}={fid}"}), 404

            set_clauses = []
            params = {"fid": fid}

            if 'geometry' in data:
                set_clauses.append(
                    "geom = ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326), 3405)"
                )
                params["geom"] = json.dumps(data['geometry'])

            if 'properties' in data:
                for k, v in data['properties'].items():
                    if k in cols:
                        set_clauses.append(f'"{k}" = :{k}')
                        params[k] = v

            if not set_clauses:
                return jsonify({"error": "Không có trường hợp lệ để cập nhật"}), 400

            update_sql = text(f"""
                UPDATE public."{table}"
                SET {', '.join(set_clauses)}
                WHERE "{pk}" = :fid;
            """)
            conn.execute(update_sql, params)
            return jsonify({"message": f"Cập nhật thành công {pk}={fid}"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── DELETE ────────────────────────────────────────────────────────────────────
@app.route('/api/<table>/<int:fid>', methods=['DELETE'])
def delete_feature(table, fid):
    """
    Xóa feature theo ID
    ---
    parameters:
      - name: table
        in: path
        type: string
        required: true
        enum: ['bounds', 'building', 'road', 'garbadge', 'instruction-generated']
      - name: fid
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Xóa thành công
      404:
        description: Không tìm thấy
    """
    if not validate_table(table):
        return jsonify({"error": "Bảng không hợp lệ"}), 404

    try:
        with engine.begin() as conn:
            pk = get_primary_key(conn, table)

            exists = conn.execute(
                text(f'SELECT 1 FROM public."{table}" WHERE "{pk}" = :fid'),
                {"fid": fid}
            ).fetchone()
            if not exists:
                return jsonify({"error": f"Không tìm thấy feature {pk}={fid}"}), 404

            conn.execute(
                text(f'DELETE FROM public."{table}" WHERE "{pk}" = :fid'),
                {"fid": fid}
            )
            return jsonify({"message": f"Đã xóa thành công {pk}={fid}"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(port=3000, debug=True)