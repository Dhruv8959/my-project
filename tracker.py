import math


class CentroidTracker:
    """
    Simple centroid-based object tracker.
    Assigns stable IDs to objects across frames.
    Prevents double-counting bags that stay in frame.
    """

    def __init__(self, max_distance=60, max_disappeared=10):
        self.objects = {}          # id -> centroid (cx, cy)
        self.disappeared = {}      # id -> frames missing
        self.next_id = 0
        self.max_distance = max_distance
        self.max_disappeared = max_disappeared
        self.counted_ids = set()   # unique bag IDs seen so far

    def _centroid(self, bbox):
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) // 2, (y1 + y2) // 2)

    def update(self, detections):
        """
        Update tracker with new detections.
        Returns current active objects: {id: (cx, cy)}
        """
        centroids = [self._centroid(d["bbox"]) for d in detections]

        if len(self.objects) == 0:
            for c in centroids:
                self._register(c)
        else:
            ids = list(self.objects.keys())
            existing = list(self.objects.values())

            matched_existing = set()
            matched_new = set()

            for ni, nc in enumerate(centroids):
                best_dist = float("inf")
                best_eid = None
                for ei, eid in enumerate(ids):
                    d = math.hypot(nc[0] - existing[ei][0], nc[1] - existing[ei][1])
                    if d < best_dist:
                        best_dist = d
                        best_eid = eid
                        best_ei = ei

                if best_dist <= self.max_distance and best_eid not in matched_existing:
                    self.objects[best_eid] = nc
                    self.disappeared[best_eid] = 0
                    matched_existing.add(best_eid)
                    matched_new.add(ni)

            for ni, nc in enumerate(centroids):
                if ni not in matched_new:
                    self._register(nc)

            for eid in ids:
                if eid not in matched_existing:
                    self.disappeared[eid] += 1
                    if self.disappeared[eid] > self.max_disappeared:
                        self._deregister(eid)

        # Update unique count
        for oid in self.objects:
            self.counted_ids.add(oid)

        return dict(self.objects)

    def _register(self, centroid):
        self.objects[self.next_id] = centroid
        self.disappeared[self.next_id] = 0
        self.counted_ids.add(self.next_id)
        self.next_id += 1

    def _deregister(self, oid):
        del self.objects[oid]
        del self.disappeared[oid]

    @property
    def unique_count(self):
        """Total unique bags ever tracked."""
        return len(self.counted_ids)
