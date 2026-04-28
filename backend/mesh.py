import heapq
import math
from typing import Dict, Iterable, Tuple


class MeshManager:
    def __init__(self, command_station: Tuple[float, float], max_link_m: float = 35000.0):
        self.command_station = command_station
        self.max_link_m = max_link_m
        self.connectivity: Dict[str, Dict[str, float]] = {}

    @staticmethod
    def _distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        dlat = (lat1 - lat2) * 111320.0
        dlng = (lng1 - lng2) * 101100.0
        return math.sqrt(dlat**2 + dlng**2)

    def _signal_from_distance(self, distance_m: float) -> float:
        if distance_m > self.max_link_m:
            return 0.0
        return max(0.0, 100.0 * (1.0 - (distance_m / self.max_link_m)))

    def update_routes(self, drones: Iterable) -> Dict[str, Dict]:
        online = [d for d in drones if d.status != "offline"]
        nodes = ["command", *[d.id for d in online]]
        positions = {"command": self.command_station}
        positions.update({d.id: (d.lat, d.lng) for d in online})

        self.connectivity = {node: {} for node in nodes}
        for i, node_a in enumerate(nodes):
            for node_b in nodes[i + 1:]:
                signal = self._signal_from_distance(
                    self._distance_m(positions[node_a][0], positions[node_a][1], positions[node_b][0], positions[node_b][1])
                )
                if signal > 0:
                    self.connectivity[node_a][node_b] = signal
                    self.connectivity[node_b][node_a] = signal

        return {drone.id: self._route_state(drone.id) for drone in online}

    def _route_state(self, drone_id: str) -> Dict:
        route, signal = self._shortest_path("command", drone_id)
        if not route:
            return {"status": "lost", "route": [], "signal_strength": 0.0}
        if signal < 25:
            status = "degraded"
        else:
            status = "connected"
        return {"status": status, "route": route, "signal_strength": signal}

    def _shortest_path(self, start: str, goal: str):
        queue = [(0.0, start, [start], 100.0)]
        visited = set()

        while queue:
            cost, node, path, path_signal = heapq.heappop(queue)
            if node in visited:
                continue
            visited.add(node)
            if node == goal:
                return path, path_signal

            for neighbor, signal in self.connectivity.get(node, {}).items():
                if neighbor in visited:
                    continue
                link_cost = 100.0 / max(signal, 1.0)
                heapq.heappush(queue, (cost + link_cost, neighbor, [*path, neighbor], min(path_signal, signal)))

        return [], 0.0
