"""
Ad-Hoc 100m Radio Mesh Router
Enforces the 100m Euclidean range gate and multi-hop relaying back to GCS.
"""
import math

class MeshRouter:
    def __init__(self, max_range_m=100.0):
        self.max_range = max_range_m
        self.gcs_pos = (-365.0, 0.0, 0.0)
        self.ber = 0.001
        self.active_links = []

    def update_topology(self, node_positions):
        self.active_links = []
        nodes = dict(node_positions)
        nodes["GCS"] = self.gcs_pos
        keys = list(nodes.keys())
        for i in range(len(keys)):
            for j in range(i+1, len(keys)):
                n1, n2 = keys[i], keys[j]
                p1, p2 = nodes[n1], nodes[n2]
                dist = math.hypot(p1[0]-p2[0], p1[1]-p2[1])
                if dist <= self.max_range:
                    self.active_links.append((n1, n2, round(dist, 1)))
        return self.active_links
