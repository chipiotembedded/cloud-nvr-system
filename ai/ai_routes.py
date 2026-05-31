"""
ai_routes.py — Flask blueprint to add to your existing playback_server.py.

Wire-up in playback_server.py (add 3 lines):

    from ai.ai_routes import ai_bp
    app.register_blueprint(ai_bp)

Routes added under /ai/*:
  GET  /ai                      — dashboard page (HTML)
  GET  /ai/alerts               — JSON list of alerts (paginated, filterable)
  GET  /ai/alert/<id>           — single alert detail
  POST /ai/alert/<id>/ack       — mark alert acknowledged
  GET  /ai/snapshot/<filename>  — serve snapshot JPG
  GET  /ai/stats                — counts per cam/type/day
  GET  /ai/zones/<camera>       — current zone polygons (for overlay tools)
"""
import os
import sqlite3
from flask import Blueprint, jsonify, request, send_from_directory, render_template

# Edit these two if your install paths differ
AI_DB_PATH = '/var/www/ai/alerts.db'
AI_SNAPSHOT_DIR = '/var/www/ai/snapshots'
AI_CONFIG_PATH = '/home/cloud/cloud-nvr-system/ai/config.yaml'

ai_bp = Blueprint('ai', __name__, template_folder='/home/cloud/cloud-nvr-system/templates')


def _q(sql, params=()):
    conn = sqlite3.connect(AI_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def _exec(sql, params=()):
    conn = sqlite3.connect(AI_DB_PATH)
    try:
        conn.execute(sql, params)
        conn.commit()
    finally:
        conn.close()


@ai_bp.route('/ai')
def ai_dashboard():
    return render_template('ai_dashboard.html')


@ai_bp.route('/ai/alerts')
def ai_alerts():
    camera = request.args.get('camera')
    alert_type = request.args.get('type')
    acked = request.args.get('acked')          # '0', '1', or None
    limit = min(int(request.args.get('limit', 50)), 500)
    offset = int(request.args.get('offset', 0))

    where, params = [], []
    if camera:
        where.append('camera = ?')
        params.append(camera)
    if alert_type:
        where.append('alert_type = ?')
        params.append(alert_type)
    if acked in ('0', '1'):
        where.append('acked = ?')
        params.append(int(acked))
    wsql = ('WHERE ' + ' AND '.join(where)) if where else ''

    rows = _q(
        f"""SELECT id, ts, ts_iso, camera, alert_type, track_id, class_name,
                   zone, message, snapshot, acked
            FROM alerts {wsql}
            ORDER BY ts DESC LIMIT ? OFFSET ?""",
        (*params, limit, offset)
    )
    return jsonify({'alerts': [dict(r) for r in rows], 'count': len(rows)})


@ai_bp.route('/ai/alert/<int:alert_id>')
def ai_alert_detail(alert_id):
    rows = _q("SELECT * FROM alerts WHERE id = ?", (alert_id,))
    if not rows:
        return jsonify({'error': 'not found'}), 404
    return jsonify(dict(rows[0]))


@ai_bp.route('/ai/alert/<int:alert_id>/ack', methods=['POST'])
def ai_alert_ack(alert_id):
    _exec("UPDATE alerts SET acked = 1 WHERE id = ?", (alert_id,))
    return jsonify({'ok': True})


@ai_bp.route('/ai/snapshot/<path:filename>')
def ai_snapshot(filename):
    return send_from_directory(AI_SNAPSHOT_DIR, filename)


@ai_bp.route('/ai/stats')
def ai_stats():
    by_type = _q(
        """SELECT alert_type, camera, COUNT(*) as n
           FROM alerts
           WHERE ts > strftime('%s', 'now', '-7 days')
           GROUP BY alert_type, camera"""
    )
    today = _q(
        """SELECT COUNT(*) as n FROM alerts
           WHERE ts > strftime('%s', 'now', 'start of day')"""
    )[0]['n']
    unacked = _q("SELECT COUNT(*) as n FROM alerts WHERE acked = 0")[0]['n']
    by_day = _q(
        """SELECT date(ts, 'unixepoch') as day, COUNT(*) as n
           FROM alerts
           WHERE ts > strftime('%s', 'now', '-14 days')
           GROUP BY day ORDER BY day"""
    )
    return jsonify({
        'today': today,
        'unacked': unacked,
        'by_type_7d': [dict(r) for r in by_type],
        'by_day_14d': [dict(r) for r in by_day],
    })


@ai_bp.route('/ai/zones/<camera>')
def ai_zones(camera):
    import yaml
    try:
        with open(AI_CONFIG_PATH) as f:
            cfg = yaml.safe_load(f)
        cam = cfg['cameras'].get(camera, {})
        return jsonify({'camera': camera, 'zones': cam.get('zones', {})})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
