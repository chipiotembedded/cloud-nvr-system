"""
zones.py — polygon zones + entry/exit transitions.
A track is "in" a zone when its bottom-center point is inside the polygon.
We track previous zone per track_id so we can emit ENTER events.
"""
from shapely.geometry import Polygon, Point


class ZoneManager:
    def __init__(self, cam_config):
        """
        cam_config: the per-camera dict from config.yaml (may have 'zones' key)
        """
        self.zones = {}
        for zname, zdef in cam_config.get('zones', {}).items():
            self.zones[zname] = {
                'polygon': Polygon(zdef['polygon']),
                'restricted': zdef.get('restricted', False),
                'capacity': zdef.get('capacity', 999),
            }
        # track_id -> {zone_name -> entered_at_ts}
        self._track_state = {}

    def has_zones(self):
        return len(self.zones) > 0

    def _bottom_center(self, bbox):
        """bbox = (x1, y1, x2, y2). Return point at feet."""
        x1, y1, x2, y2 = bbox
        return Point((x1 + x2) / 2.0, y2)

    def zones_for_point(self, bbox):
        pt = self._bottom_center(bbox)
        return [name for name, z in self.zones.items()
                if z['polygon'].contains(pt)]

    def update(self, track_id, bbox, now_ts):
        """
        Returns list of events for this track this frame:
          [{'event': 'enter'|'exit', 'zone': name, 'restricted': bool}]
        """
        current = set(self.zones_for_point(bbox))
        prev = set(self._track_state.get(track_id, {}).keys())
        events = []

        for entered in current - prev:
            events.append({
                'event': 'enter',
                'zone': entered,
                'restricted': self.zones[entered]['restricted'],
            })
        for exited in prev - current:
            events.append({
                'event': 'exit',
                'zone': exited,
                'restricted': self.zones[exited]['restricted'],
            })

        # Update state
        new_state = {}
        for zname in current:
            new_state[zname] = self._track_state.get(track_id, {}).get(zname, now_ts)
        self._track_state[track_id] = new_state

        return events

    def occupancy(self, track_id_to_bbox):
        """Given {track_id: bbox} for active tracks, return {zone: count}."""
        counts = {z: 0 for z in self.zones}
        for tid, bbox in track_id_to_bbox.items():
            for z in self.zones_for_point(bbox):
                counts[z] += 1
        return counts

    def forget(self, track_id):
        self._track_state.pop(track_id, None)
