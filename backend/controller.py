import math
import random
import sys
import time
from typing import List, Dict, Optional, Tuple

try:
    from backend.drone_bridge import DroneBridge
    from backend.mesh import MeshManager
    from backend.protocol import ProtocolSequencer
    from backend.mission_program import compile_mission_program
except ImportError:
    try:
        from drone_bridge import DroneBridge
        from mesh import MeshManager
        from protocol import ProtocolSequencer
        from mission_program import compile_mission_program
    except ImportError:
        DroneBridge = None
        MeshManager = None
        ProtocolSequencer = None
        compile_mission_program = None


class NavigationState:
    def __init__(self):
        self.gps_available = True
        self.position_source = "gps"
        self.position_confidence = 1.0
        self.drift_accumulated_m = 0.0


class EnergyModel:
    HOVER_DRAIN_PER_SECOND = 0.03
    CRUISE_DRAIN_PER_METER = 0.0002
    PAYLOAD_PENALTY = 1.15

    def estimate_drain(self, distance_m: float, speed_ms: float, wind_speed_ms: float, wind_dir_deg: float, heading_deg: float) -> float:
        if distance_m <= 0:
            return self.HOVER_DRAIN_PER_SECOND

        safe_speed = max(speed_ms, 1.0)
        wind_angle = abs((wind_dir_deg - heading_deg + 180) % 360 - 180)
        wind_factor = 1.0 + (wind_speed_ms / safe_speed) * math.cos(math.radians(wind_angle))
        wind_factor = max(0.5, min(wind_factor, 1.8))
        return distance_m * self.CRUISE_DRAIN_PER_METER * wind_factor

    def required_battery(self, distance_m: float, wind_speed_ms: float, wind_dir_deg: float, heading_deg: float) -> float:
        return self.estimate_drain(distance_m, 12.0, wind_speed_ms, wind_dir_deg, heading_deg) + 10.0

class Drone:
    def __init__(self, id: str, lat: float, lng: float, battery: float):
        self.id = id
        self.lat = lat
        self.lng = lng
        self.battery = battery
        self.status = "idle"  # idle, assigned, on_station, returning, offline
        self.target = None
        self.waypoints: List[Tuple[float, float]] = []
        self._waypoint_index = 0
        self.mission_target = None
        self.altitude_m = 10.0
        self.current_priority = "medium"
        self.mission_start_time = None
        self.nav_state = NavigationState()
        self.nav_hold = False
        self._nav_hold_logged = False
        self._nav_rtb_logged = False
        self.comms_status = "connected"
        self.mesh_route: List[str] = []
        self.signal_strength = 100.0
        self.rotor_speed = 100.0  # percentage
        self.home = (lat, lng)    # Remember spawn point for RTB
        
class SwarmManager:
    # Riyadh geo-constants for meter-to-degree conversion
    METERS_PER_LAT_DEG = 111320.0
    METERS_PER_LNG_DEG = 101100.0  # approximate at 24.7°N
    FORMATION_RADIUS_M = 50.0      # meters
    
    # Operational thresholds
    BATTERY_MIN_FOR_ASSIGNMENT = 15.0  # Don't assign drones below this %
    BATTERY_AUTO_RETURN = 20.0         # Auto-recall drones at this %
    SAFETY_RADIUS_M = 5.0

    def __init__(self):
        # Digital Twin of the fleet — expanded to 13 drones
        self.fleet: Dict[str, Drone] = {
            # Alpha Squadron — Primary assault/scout
            "alpha-1": Drone("alpha-1", 24.7136, 46.6753, 100.0),
            "alpha-2": Drone("alpha-2", 24.7140, 46.6760, 95.0),
            "alpha-3": Drone("alpha-3", 24.7130, 46.6740, 88.0),
            "alpha-4": Drone("alpha-4", 24.7145, 46.6748, 92.0),
            "alpha-5": Drone("alpha-5", 24.7132, 46.6765, 85.0),
            # Beta Squadron — Heavy / long-range
            "beta-1":  Drone("beta-1",  24.7150, 46.6770, 78.0),
            "beta-2":  Drone("beta-2",  24.7155, 46.6745, 90.0),
            "beta-3":  Drone("beta-3",  24.7148, 46.6738, 82.0),
            # Gamma Squadron — Reserve / rapid response
            "gamma-1": Drone("gamma-1", 24.7160, 46.6755, 100.0),
            "gamma-2": Drone("gamma-2", 24.7158, 46.6762, 100.0),
            "gamma-3": Drone("gamma-3", 24.7162, 46.6750, 100.0),
            # Delta Squadron — Recon specialists
            "delta-1": Drone("delta-1", 24.7138, 46.6735, 96.0),
            "delta-2": Drone("delta-2", 24.7142, 46.6730, 91.0),
        }
        self.ambient_temp = 30.0  # Celsius
        self.ambient_temp_source = "default"
        self.ambient_temp_updated_at = None
        self.wind_speed_ms = 0.0
        self.wind_direction_deg = 0.0
        self.gps_denied = False
        self.live_mode = False
        self.bridge = DroneBridge() if DroneBridge else None
        self.mesh = MeshManager(command_station=(24.7136, 46.6753)) if MeshManager else None
        self.energy_model = EnergyModel()
        self.protocol = ProtocolSequencer() if ProtocolSequencer else None
        self._thinking_log: List[Dict] = []
        self._max_log_size = 200
        self._collision_alerts: Dict[str, float] = {}
        
    # ─── Thinking Log ─────────────────────────────────────────────────────────

    def _think(self, message: str, category: str = "info"):
        """Record an AI decision with timestamp."""
        entry = {
            "time": time.time(),
            "timestamp": time.strftime("%H:%M:%S"),
            "message": message,
            "category": category  # info, warning, critical, decision
        }
        self._thinking_log.append(entry)
        # Cap log size
        if len(self._thinking_log) > self._max_log_size:
            self._thinking_log = self._thinking_log[-self._max_log_size:]

        encoding = sys.stdout.encoding or "utf-8"
        safe_message = message.encode(encoding, errors="replace").decode(encoding, errors="replace")
        print(f"[THINK] {safe_message}")
        
    def get_thinking_log(self, last_n: int = 50) -> List[Dict]:
        """Return the last N thinking log entries."""
        return self._thinking_log[-last_n:]
        
    # ─── Thermal Management ──────────────────────────────────────────────────

    def set_ambient_temp(self, temp: float, source: str = "manual") -> List[str]:
        old_temp = self.ambient_temp
        old_source = self.ambient_temp_source
        self.ambient_temp = round(float(temp), 1)
        self.ambient_temp_source = source
        self.ambient_temp_updated_at = time.time()

        if source == "riyadh_live" and (old_source != "riyadh_live" or abs(self.ambient_temp - old_temp) >= 0.5):
            self._think(
                f"Riyadh live temperature synced: {self.ambient_temp}°C.",
                "info"
            )
        
        if self.ambient_temp > 45.0 and old_temp <= 45.0:
            self._think(
                f"⚠ THERMAL ALERT: Ambient temperature {self.ambient_temp}°C exceeds safe threshold (45°C). "
                f"Capping all rotor speeds to 70% to prevent motor burnout.",
                "warning"
            )
        elif self.ambient_temp <= 45.0 and old_temp > 45.0:
            self._think(
                f"✓ Temperature normalized to {self.ambient_temp}°C. Restoring full rotor capability.",
                "info"
            )
            
        self._apply_thermal_throttling()
        return self.get_thinking_log(last_n=5)

    def set_weather(self, temp: float, wind_speed_ms: float = 0.0, wind_direction_deg: float = 0.0, source: str = "manual") -> List[Dict]:
        self.wind_speed_ms = max(0.0, float(wind_speed_ms))
        self.wind_direction_deg = float(wind_direction_deg) % 360
        return self.set_ambient_temp(temp, source=source)
        
    def _apply_thermal_throttling(self):
        """If temp > 45C, cap rotor speeds to 70%. If temp drops, restore to 100%."""
        if self.ambient_temp > 45.0:
            for drone in self.fleet.values():
                if drone.status != "offline":
                    drone.rotor_speed = min(drone.rotor_speed, 70.0)
        else:
            # Restore rotor speeds when temperature normalizes
            for drone in self.fleet.values():
                if drone.status != "offline":
                    drone.rotor_speed = 100.0

    def set_gps_denied(self, enabled: bool) -> List[Dict]:
        self.gps_denied = enabled
        if enabled:
            self._think(
                "GPS-DENIED simulation enabled. Swarm switching to inertial dead-reckoning fallback.",
                "warning"
            )
        else:
            for drone in self.fleet.values():
                drone.nav_state.gps_available = True
                drone.nav_state.position_source = "gps"
                drone.nav_state.position_confidence = 1.0
                drone.nav_state.drift_accumulated_m = 0.0
                drone.nav_hold = False
                drone._nav_hold_logged = False
                drone._nav_rtb_logged = False
            self._think("GPS restored. Swarm navigation fused back to normal telemetry.", "info")
        return self.get_thinking_log(last_n=5)
                
    # ─── Fleet State ──────────────────────────────────────────────────────────

    def get_fleet_state(self) -> Dict:
        drones = [
            {
                "id": d.id,
                "lat": d.lat,
                "lng": d.lng,
                "battery": d.battery,
                "status": d.status,
                "rotor_speed": d.rotor_speed,
                "target_lat": d.target[0] if d.target else None,
                "target_lng": d.target[1] if d.target else None,
                "mission_target_lat": d.mission_target[0] if d.mission_target else None,
                "mission_target_lng": d.mission_target[1] if d.mission_target else None,
                "waypoint_index": d._waypoint_index,
                "waypoints": [(w[0], w[1]) for w in d.waypoints],
                "altitude_m": d.altitude_m,
                "current_priority": d.current_priority,
                "mission_duration_s": round(time.time() - d.mission_start_time) if d.mission_start_time else 0,
                "nav_source": d.nav_state.position_source,
                "nav_confidence": round(d.nav_state.position_confidence, 2),
                "nav_drift_m": round(d.nav_state.drift_accumulated_m, 1),
                "nav_hold": d.nav_hold,
                "comms_status": d.comms_status,
                "mesh_route": d.mesh_route,
                "signal_strength": round(d.signal_strength, 1),
            }
            for d in self.fleet.values()
        ]
        # Fleet-level statistics
        online_drones = [d for d in self.fleet.values() if d.status != "offline"]
        return {
            "drones": drones,
            "stats": {
                "total": len(self.fleet),
                "online": len(online_drones),
                "assigned": sum(1 for d in online_drones if d.status in ("assigned", "on_station")),
                "idle": sum(1 for d in online_drones if d.status == "idle"),
                "returning": sum(1 for d in online_drones if d.status == "returning"),
                "offline": sum(1 for d in self.fleet.values() if d.status == "offline"),
                "avg_battery": round(
                    sum(d.battery for d in online_drones) / max(len(online_drones), 1), 1
                ),
                "ambient_temp": self.ambient_temp,
                "ambient_temp_source": self.ambient_temp_source,
                "ambient_temp_updated_at": self.ambient_temp_updated_at,
                "wind_speed_ms": round(self.wind_speed_ms, 1),
                "wind_direction_deg": round(self.wind_direction_deg, 0),
                "gps_denied": self.gps_denied,
                "live_mode": self.live_mode,
                "fleet_health": self._fleet_health_score(online_drones),
            }
        }

    def _fleet_health_score(self, online_drones: List[Drone]) -> int:
        if not self.fleet:
            return 0
        online_score = (len(online_drones) / len(self.fleet)) * 45
        avg_battery = sum(d.battery for d in online_drones) / max(len(online_drones), 1)
        battery_score = avg_battery * 0.4
        available_score = (sum(1 for d in online_drones if d.status == "idle") / max(len(online_drones), 1)) * 15
        return round(min(100, online_score + battery_score + available_score))

    def _distance(self, lat1, lng1, lat2, lng2):
        return math.sqrt((lat1 - lat2)**2 + (lng1 - lng2)**2)

    def _distance_meters(self, lat1, lng1, lat2, lng2):
        """Approximate distance in meters for Riyadh area."""
        dlat = (lat1 - lat2) * self.METERS_PER_LAT_DEG
        dlng = (lng1 - lng2) * self.METERS_PER_LNG_DEG
        return math.sqrt(dlat**2 + dlng**2)

    # ─── Formation Logic ──────────────────────────────────────────────────────

    def _set_drone_path(
        self,
        drone: Drone,
        waypoints: List[Tuple[float, float]],
        mission_target: Tuple[float, float],
        priority: str = "medium",
    ):
        drone.status = "assigned"
        drone.waypoints = waypoints
        drone._waypoint_index = 0
        drone.target = waypoints[0] if waypoints else mission_target
        drone.mission_target = mission_target
        drone.current_priority = priority
        drone.mission_start_time = time.time()
        drone.nav_hold = False

        if self.protocol:
            self.protocol.next_message(
                "COMMAND",
                "command",
                drone.id,
                {
                    "action": "follow_waypoints",
                    "waypoints": [(lat, lng, drone.altitude_m) for lat, lng in waypoints],
                    "priority": priority,
                },
            )

    def _dispatch_live_waypoints(self, drone: Drone):
        try:
            import asyncio
            loop = asyncio.get_running_loop()
            waypoints = [(lat, lng, drone.altitude_m) for lat, lng in drone.waypoints]
            loop.create_task(self.bridge.follow_waypoints(drone.id, waypoints))
            self._think(f"LIVE MODE: waypoint mission queued for {drone.id.upper()} via MAVLink bridge.", "decision")
        except RuntimeError:
            self._think(f"LIVE MODE: no running event loop; {drone.id.upper()} command queued only in digital twin.", "warning")

    async def execute_mission_program(self, program: Dict) -> Dict:
        if not self.live_mode:
            return {"executed": False, "mode": "digital_twin_simulation"}
        if not self.bridge:
            return {"executed": False, "mode": "live_mavlink", "reason": "bridge_unavailable"}
        result = await self.bridge.execute_program(program)
        self._think("LIVE MODE: SHEPHERD-IR program dispatched to MAVSDK/MAVLink bridge.", "decision")
        return {"executed": True, "mode": "live_mavlink", "result": result}

    def _perimeter_pattern(self, target_lat: float, target_lng: float, drones: List[Drone], priority: str = "medium") -> List[str]:
        """
        Distributes drones in a circular perimeter formation around the target.
        Single drone goes to exact coordinates. Multiple drones fan out in a circle.
        """
        n = len(drones)
        assigned = []
        for i, drone in enumerate(drones):
            if n > 1:
                angle = (2 * math.pi * i) / n
                lat_offset = (self.FORMATION_RADIUS_M / self.METERS_PER_LAT_DEG) * math.cos(angle)
                lng_offset = (self.FORMATION_RADIUS_M / self.METERS_PER_LNG_DEG) * math.sin(angle)
                waypoint = (target_lat + lat_offset, target_lng + lng_offset)
            else:
                waypoint = (target_lat, target_lng)
            self._set_drone_path(drone, [waypoint], (target_lat, target_lng), priority=priority)
            assigned.append(drone.id)
        return assigned

    def _lawn_mower_pattern(
        self, target_lat: float, target_lng: float, drones: List[Drone], area_size_m: float = 200.0, priority: str = "medium"
    ) -> List[str]:
        """Distributes drones into parallel north-south search strips."""
        n = len(drones)
        if n == 0:
            return []

        half_lat = (area_size_m / 2) / self.METERS_PER_LAT_DEG
        half_lng = (area_size_m / 2) / self.METERS_PER_LNG_DEG
        strip_width = (2 * half_lng) / n

        assigned = []
        for i, drone in enumerate(drones):
            lng_pos = (target_lng - half_lng) + (strip_width * i) + (strip_width / 2)
            steps = 6
            waypoints = []
            for row in range(steps):
                lat_pos = target_lat - half_lat + (2 * half_lat * row / (steps - 1))
                waypoints.append((lat_pos, lng_pos))
            if i % 2 == 1:
                waypoints.reverse()

            self._set_drone_path(drone, waypoints, (target_lat, target_lng), priority=priority)
            assigned.append(drone.id)

        self._think(
            f"Lawn-mower pattern deployed: {n} strips, {area_size_m:.0f}m coverage area.",
            "decision"
        )
        return assigned

    def _spiral_pattern(
        self, target_lat: float, target_lng: float, drones: List[Drone], radius_m: float = 150.0, priority: str = "medium"
    ) -> List[str]:
        """Distributes drones on inward spiral paths converging on the target."""
        n = len(drones)
        if n == 0:
            return []

        assigned = []
        steps = 12
        for i, drone in enumerate(drones):
            start_angle = (2 * math.pi * i) / n
            waypoints = []
            for step in range(steps):
                progress = step / (steps - 1)
                radius = radius_m * (1 - progress)
                angle = start_angle + (progress * 4 * math.pi)
                lat = target_lat + (radius / self.METERS_PER_LAT_DEG) * math.cos(angle)
                lng = target_lng + (radius / self.METERS_PER_LNG_DEG) * math.sin(angle)
                waypoints.append((lat, lng))

            self._set_drone_path(drone, waypoints, (target_lat, target_lng), priority=priority)
            assigned.append(drone.id)

        self._think(
            f"Spiral pattern deployed: {n} drones, {radius_m:.0f}m convergence radius.",
            "decision"
        )
        return assigned

    def _apply_formation(
        self,
        target_lat: float,
        target_lng: float,
        drones: List[Drone],
        pattern: str = "perimeter",
        area_size_m: float = 200.0,
        priority: str = "medium",
    ) -> List[str]:
        if pattern == "lawn_mower":
            assigned = self._lawn_mower_pattern(target_lat, target_lng, drones, area_size_m=area_size_m, priority=priority)
        elif pattern == "spiral":
            assigned = self._spiral_pattern(target_lat, target_lng, drones, radius_m=area_size_m / 2, priority=priority)
        else:
            assigned = self._perimeter_pattern(target_lat, target_lng, drones, priority=priority)

        self._deconflict_paths(drones)
        for drone in drones:
            drone.current_priority = priority
        return assigned

    def _deconflict_paths(self, drones: List[Drone]):
        adjusted = set()
        for i, drone_a in enumerate(drones):
            for drone_b in drones[i + 1:]:
                min_len = min(len(drone_a.waypoints), len(drone_b.waypoints))
                for waypoint_index in range(min_len):
                    a = drone_a.waypoints[waypoint_index]
                    b = drone_b.waypoints[waypoint_index]
                    if self._distance_meters(a[0], a[1], b[0], b[1]) < self.SAFETY_RADIUS_M * 2:
                        drone_b.altitude_m += 5.0
                        adjusted.add((drone_b.id, waypoint_index + 1, drone_a.id, drone_b.altitude_m))
                        break

        for drone_id, waypoint_index, other_id, altitude in adjusted:
            self._think(
                f"DECONFLICT: {drone_id.upper()} assigned {altitude:.0f}m altitude near waypoint {waypoint_index} to avoid {other_id.upper()}.",
                "decision"
            )

    def _mission_required_battery(self, drone: Drone, target_lat: float, target_lng: float, pattern: str, area_size_m: float) -> float:
        outbound_m = self._distance_meters(drone.lat, drone.lng, target_lat, target_lng)
        rtb_m = self._distance_meters(target_lat, target_lng, drone.home[0], drone.home[1])
        coverage_m = 0.0
        if pattern == "lawn_mower":
            coverage_m = area_size_m * 1.2
        elif pattern == "spiral":
            coverage_m = math.pi * (area_size_m / 2)

        heading = math.degrees(math.atan2(target_lng - drone.lng, target_lat - drone.lat)) % 360
        return self.energy_model.required_battery(outbound_m + rtb_m + coverage_m, self.wind_speed_ms, self.wind_direction_deg, heading)

    # ─── Task Allocation ──────────────────────────────────────────────────────

    def allocate_task(
        self, target_lat: float, target_lng: float,
        required_drones: int = 1,
        specific_drones: List[str] = None,
        pattern: str = "perimeter",
        priority: str = "medium",
        area_size_m: float = 200.0,
    ) -> Tuple[List[str], List[Dict]]:
        """
        Allocation Algorithm: sorts by (Battery % - Distance) unless specific drones requested.
        Returns (assigned_drone_ids, thinking_log_entries).
        """
        
        if pattern not in ("perimeter", "lawn_mower", "spiral"):
            pattern = "perimeter"

        # If specific drones are requested, assign them directly
        if specific_drones:
            valid_drones = []
            for d_id in specific_drones:
                if d_id not in self.fleet:
                    self._think(f"✗ {d_id.upper()} not found in fleet registry.", "warning")
                    continue
                drone = self.fleet[d_id]
                if drone.status == "offline":
                    self._think(f"✗ {d_id.upper()} is OFFLINE — cannot assign.", "warning")
                    continue
                if drone.battery < self.BATTERY_MIN_FOR_ASSIGNMENT:
                    self._think(
                        f"✗ {d_id.upper()} battery critically low ({drone.battery:.1f}%) — "
                        f"below safe threshold ({self.BATTERY_MIN_FOR_ASSIGNMENT}%). Skipping.",
                        "warning"
                    )
                    continue
                required_battery = self._mission_required_battery(drone, target_lat, target_lng, pattern, area_size_m)
                if drone.battery < required_battery:
                    self._think(
                        f"ENERGY: {d_id.upper()} has insufficient battery ({drone.battery:.1f}%) for mission "
                        f"estimated at {required_battery:.1f}% including RTB reserve. Skipping.",
                        "warning"
                    )
                    continue
                valid_drones.append(drone)
                
            if not valid_drones:
                self._think("✗ No valid drones from the requested set. Assignment failed.", "critical")
                return [], self.get_thinking_log(last_n=5)
                
            self._think(
                f"✓ Direct assignment: {', '.join(d.id.upper() for d in valid_drones)} "
                f"tasked to target ({target_lat:.4f}, {target_lng:.4f}) using {pattern} pattern.",
                "decision"
            )
            assigned = self._apply_formation(
                target_lat, target_lng, valid_drones, pattern=pattern, area_size_m=area_size_m, priority=priority
            )
            return assigned, self.get_thinking_log(last_n=5)
                
        # Auto-allocate based on heuristics
        available_drones = [
            d for d in self.fleet.values() 
            if d.status == "idle" and d.battery >= self.BATTERY_MIN_FOR_ASSIGNMENT
        ]
        
        # Log skipped drones
        low_battery_drones = [
            d for d in self.fleet.values()
            if d.status == "idle" and d.battery < self.BATTERY_MIN_FOR_ASSIGNMENT
        ]
        for d in low_battery_drones:
            self._think(
                f"✗ {d.id.upper()} skipped: battery {d.battery:.1f}% below minimum ({self.BATTERY_MIN_FOR_ASSIGNMENT}%).",
                "info"
            )
        
        if not available_drones:
            if priority == "high":
                preemptable = [
                    d for d in self.fleet.values()
                    if d.status in ("assigned", "on_station") and d.current_priority in ("low", "medium")
                ]
                preemptable.sort(key=lambda d: (d.current_priority == "low", d.battery), reverse=True)
                available_drones = preemptable[:required_drones]
                for d in available_drones:
                    self._think(f"PRE-EMPT: {d.id.upper()} reassigned from {d.current_priority} mission to high-priority task.", "warning")
            if not available_drones:
                self._think(
                    f"✗ No idle drones with sufficient battery (>{self.BATTERY_MIN_FOR_ASSIGNMENT}%) available for tasking.",
                    "critical"
                )
                return [], self.get_thinking_log(last_n=5)

        energy_ready = []
        for d in available_drones:
            required_battery = self._mission_required_battery(d, target_lat, target_lng, pattern, area_size_m)
            if d.battery >= required_battery:
                energy_ready.append(d)
            else:
                self._think(
                    f"ENERGY: {d.id.upper()} skipped: battery {d.battery:.1f}% below estimated mission need {required_battery:.1f}%.",
                    "info"
                )

        available_drones = energy_ready
        if not available_drones:
            self._think("✗ No drones can complete mission with RTB battery reserve.", "critical")
            return [], self.get_thinking_log(last_n=5)
            
        # Score = Battery - (Distance * Weight)
        def score_drone(d: Drone):
            dist_m = self._distance_meters(d.lat, d.lng, target_lat, target_lng)
            return d.battery - (dist_m / 100.0)  # 100m = 1 point penalty
            
        available_drones.sort(key=score_drone, reverse=True)
        selected = available_drones[:min(required_drones, len(available_drones))]
        
        # Log the selection reasoning
        for d in selected:
            dist_m = self._distance_meters(d.lat, d.lng, target_lat, target_lng)
            score = score_drone(d)
            self._think(
                f"✓ {d.id.upper()} selected — Battery: {d.battery:.1f}%, "
                f"Distance: {dist_m:.0f}m, Score: {score:.1f}",
                "decision"
            )
        
        # Log runners-up
        passed_over = available_drones[len(selected):len(selected)+3]
        for d in passed_over:
            dist_m = self._distance_meters(d.lat, d.lng, target_lat, target_lng)
            score = score_drone(d)
            self._think(
                f"  {d.id.upper()} standby — Battery: {d.battery:.1f}%, "
                f"Distance: {dist_m:.0f}m, Score: {score:.1f}",
                "info"
            )
            
        assigned = self._apply_formation(
            target_lat, target_lng, selected, pattern=pattern, area_size_m=area_size_m, priority=priority
        )
        return assigned, self.get_thinking_log(last_n=10)

    def recall_drones(self, drone_ids: Optional[List[str]] = None) -> Tuple[List[str], List[Dict]]:
        """Return selected or all online drones to their home coordinates."""
        requested = set(drone_ids or [])
        recalled = []

        for drone in self.fleet.values():
            if requested and drone.id not in requested:
                continue
            if drone.status == "offline":
                continue

            drone.status = "returning"
            drone.target = drone.home
            drone.waypoints = []
            drone._waypoint_index = 0
            drone.mission_target = None
            drone.mission_start_time = drone.mission_start_time or time.time()
            recalled.append(drone.id)

        if recalled:
            self._think(
                f"Recall command accepted: {', '.join(d.upper() for d in recalled)} returning to base.",
                "decision"
            )
        else:
            self._think("Recall command received, but no online drones matched the request.", "warning")

        return recalled, self.get_thinking_log(last_n=5)

    # ─── Crash & Recovery ─────────────────────────────────────────────────────

    def report_drone_lost(self, drone_id: str) -> Tuple[str, List[Dict]]:
        """Marks drone as offline and triggers dynamic re-tasking."""
        if drone_id in self.fleet:
            lost_drone = self.fleet[drone_id]
            lost_drone.status = "offline"
            lost_drone.rotor_speed = 0.0
            missed_target = lost_drone.target
            lost_drone.target = None
            lost_drone.waypoints = []
            lost_drone._waypoint_index = 0
            lost_drone.mission_target = None
            lost_drone.mission_start_time = None

            if self.live_mode and self.bridge:
                try:
                    import asyncio
                    asyncio.get_running_loop().create_task(self.bridge.emergency_stop(drone_id))
                except RuntimeError:
                    pass
            
            self._think(
                f"🔴 ALERT: {drone_id.upper()} reported LOST. "
                f"Status set to OFFLINE. Rotor speed zeroed.",
                "critical"
            )
            
            if missed_target:
                self._think(
                    f"  {drone_id.upper()} was on active mission to ({missed_target[0]:.4f}, {missed_target[1]:.4f}). "
                    f"Initiating fleet rebalance...",
                    "decision"
                )
                success = self._rebalance_fleet(missed_target)
                if success:
                    return (
                        f"Drone {drone_id} offline. Reserve unit launched to complete mission.",
                        self.get_thinking_log(last_n=5)
                    )
                else:
                    return (
                        f"Drone {drone_id} offline. CRITICAL: No reserves available for rebalancing.",
                        self.get_thinking_log(last_n=5)
                    )
            return (
                f"Drone {drone_id} taken offline while idle.",
                self.get_thinking_log(last_n=5)
            )
        return "Drone not found.", []

    def revive_drone(self, drone_id: str) -> Tuple[str, List[Dict]]:
        """Brings an offline drone back online at base coordinates."""
        if drone_id in self.fleet:
            drone = self.fleet[drone_id]
            if drone.status != "offline":
                return (
                    f"Drone {drone_id} is already online ({drone.status}).",
                    self.get_thinking_log(last_n=3)
                )
            drone.status = "idle"
            drone.battery = 100.0
            drone.rotor_speed = 100.0
            drone.lat = drone.home[0]
            drone.lng = drone.home[1]
            drone.target = None
            drone.waypoints = []
            drone._waypoint_index = 0
            drone.mission_target = None
            drone.mission_start_time = None
            drone.current_priority = "medium"
            drone.altitude_m = 10.0
            drone.nav_state = NavigationState()
            drone.nav_hold = False
            drone._nav_hold_logged = False
            drone._nav_rtb_logged = False
            self._apply_thermal_throttling()
            
            self._think(
                f"✓ {drone_id.upper()} REVIVED — returned to base "
                f"({drone.home[0]:.4f}, {drone.home[1]:.4f}) at full charge.",
                "info"
            )
            return (
                f"Drone {drone_id} revived and returned to base at full charge.",
                self.get_thinking_log(last_n=3)
            )
        return "Drone not found.", []
                
    def _rebalance_fleet(self, missed_target: tuple) -> bool:
        """Finds another drone to take over the missed target."""
        assigned, _ = self.allocate_task(missed_target[0], missed_target[1], 1)
        if not assigned:
            self._think(
                "✗ REBALANCE FAILED: No idle drones available. Mission target abandoned.",
                "critical"
            )
            return False
        self._think(
            f"✓ Rebalance successful: {assigned[0].upper()} dispatched to cover gap.",
            "decision"
        )
        return True

    def _update_navigation_state(self, drone: Drone):
        if drone.status == "offline":
            return

        if not self.gps_denied:
            drone.nav_state.gps_available = True
            drone.nav_state.position_source = "gps"
            drone.nav_state.position_confidence = 1.0
            drone.nav_hold = False
            drone._nav_hold_logged = False
            drone._nav_rtb_logged = False
            return

        drone.nav_state.gps_available = False
        drone.nav_state.position_source = "imu_dead_reckoning"
        drone.nav_state.position_confidence = max(0.0, drone.nav_state.position_confidence - 0.02)
        drone.nav_state.drift_accumulated_m += max(0.2, random.gauss(1.8, 0.8))

        if drone.nav_state.position_confidence < 0.1 and drone.status in ("assigned", "on_station"):
            drone.status = "returning"
            drone.target = drone.home
            drone.waypoints = []
            drone._waypoint_index = 0
            drone.mission_target = None
            drone.nav_hold = False
            if not drone._nav_rtb_logged:
                self._think(
                    f"NAV CRITICAL: {drone.id.upper()} confidence {drone.nav_state.position_confidence:.0%}. Autonomous RTB triggered.",
                    "critical"
                )
                drone._nav_rtb_logged = True
        elif drone.nav_state.position_confidence < 0.3 and drone.status == "assigned":
            drone.nav_hold = True
            if not drone._nav_hold_logged:
                self._think(
                    f"NAV DEGRADED: {drone.id.upper()} position confidence {drone.nav_state.position_confidence:.0%}. Holding position until GPS restored.",
                    "warning"
                )
                drone._nav_hold_logged = True

    def _apply_mesh_routing(self):
        if not self.mesh:
            return

        updates = self.mesh.update_routes(self.fleet.values())
        for drone_id, route_state in updates.items():
            drone = self.fleet[drone_id]
            previous = drone.comms_status
            drone.comms_status = route_state["status"]
            drone.mesh_route = route_state["route"]
            drone.signal_strength = route_state["signal_strength"]

            if previous != drone.comms_status:
                if drone.comms_status == "lost":
                    self._think(f"MESH: CRITICAL — {drone.id.upper()} has no command path. Autonomous RTB expected.", "critical")
                    if drone.status in ("assigned", "on_station"):
                        drone.status = "returning"
                        drone.target = drone.home
                        drone.waypoints = []
                        drone._waypoint_index = 0
                        drone.mission_target = None
                elif len(drone.mesh_route) > 2:
                    relays = " -> ".join(drone.mesh_route[1:-1]).upper()
                    self._think(f"MESH: {drone.id.upper()} now relaying through {relays}.", "warning")

    def _runtime_collision_check(self):
        moving = [d for d in self.fleet.values() if d.status in ("assigned", "returning")]
        now = time.time()
        for i, drone_a in enumerate(moving):
            for drone_b in moving[i + 1:]:
                distance_m = self._distance_meters(drone_a.lat, drone_a.lng, drone_b.lat, drone_b.lng)
                pair_key = ":".join(sorted([drone_a.id, drone_b.id]))
                if distance_m >= self.SAFETY_RADIUS_M * 2:
                    continue
                if now - self._collision_alerts.get(pair_key, 0) < 8:
                    continue

                lower_priority = drone_b if drone_a.current_priority == "high" else drone_a
                if distance_m < self.SAFETY_RADIUS_M:
                    lower_priority.lng += 10 / self.METERS_PER_LNG_DEG
                    lower_priority.altitude_m += 5.0
                    self._think(
                        f"COLLISION AVOIDANCE: {lower_priority.id.upper()} diverting +10m east and climbing to {lower_priority.altitude_m:.0f}m.",
                        "critical"
                    )
                else:
                    lower_priority.rotor_speed = min(lower_priority.rotor_speed, 60.0)
                    self._think(
                        f"PROXIMITY ALERT: {drone_a.id.upper()} and {drone_b.id.upper()} within {distance_m:.0f}m. {lower_priority.id.upper()} speed reduced.",
                        "warning"
                    )
                self._collision_alerts[pair_key] = now
        
    # ─── Simulation Tick ──────────────────────────────────────────────────────

    def step_simulation(self):
        """Moves drones towards targets for visualization in the Digital Twin."""
        self._apply_mesh_routing()

        for drone in self.fleet.values():
            self._update_navigation_state(drone)

            if drone.status == "idle" and drone.battery < 100.0:
                if self._distance_meters(drone.lat, drone.lng, drone.home[0], drone.home[1]) < 2:
                    drone.battery = min(100.0, drone.battery + 2.0)
                    drone.mission_start_time = None

            # ── Auto-return on low battery ────────────────────────────────
            if (drone.status in ("assigned", "on_station") and 
                drone.battery <= self.BATTERY_AUTO_RETURN and
                drone.target != drone.home):
                
                self._think(
                    f"⚠ {drone.id.upper()} battery critical ({drone.battery:.1f}%). "
                    f"AUTO-RECALL initiated — returning to base.",
                    "warning"
                )
                drone.status = "returning"
                drone.target = drone.home
                drone.waypoints = []
                drone._waypoint_index = 0
                drone.mission_target = None

            if drone.nav_hold:
                continue
             
            # ── Movement logic ────────────────────────────────────────────
            if drone.status in ("assigned", "returning") and drone.target:
                lat_diff = drone.target[0] - drone.lat
                lng_diff = drone.target[1] - drone.lng
                dist = math.sqrt(lat_diff**2 + lng_diff**2)
                
                speed = 0.0005 * (drone.rotor_speed / 100.0)
                
                # Snap to target if within one tick of travel
                if dist <= speed:
                    drone.lat = drone.target[0]
                    drone.lng = drone.target[1]
                    
                    if drone.status == "returning":
                        drone.status = "idle"
                        drone.target = None
                        drone.waypoints = []
                        drone._waypoint_index = 0
                        drone.mission_target = None
                        drone.mission_start_time = None
                        drone.current_priority = "medium"
                        self._think(
                            f"✓ {drone.id.upper()} returned to base safely. Battery: {drone.battery:.1f}%",
                            "info"
                        )
                    elif drone.waypoints and drone._waypoint_index < len(drone.waypoints) - 1:
                        drone._waypoint_index += 1
                        drone.target = drone.waypoints[drone._waypoint_index]
                        self._think(
                            f"{drone.id.upper()} advancing to waypoint "
                            f"{drone._waypoint_index + 1}/{len(drone.waypoints)}.",
                            "info"
                        )
                    else:
                        drone.status = "on_station"
                        self._think(
                            f"✓ {drone.id.upper()} arrived ON STATION at "
                            f"({drone.lat:.4f}, {drone.lng:.4f}). Battery: {drone.battery:.1f}%",
                            "info"
                        )
                else:
                    old_lat, old_lng = drone.lat, drone.lng
                    drone.lat += (lat_diff / dist) * speed
                    drone.lng += (lng_diff / dist) * speed
                    moved_m = self._distance_meters(old_lat, old_lng, drone.lat, drone.lng)
                    heading = math.degrees(math.atan2(lng_diff, lat_diff)) % 360
                    drain = self.energy_model.estimate_drain(
                        moved_m, 12.0 * (drone.rotor_speed / 100.0), self.wind_speed_ms, self.wind_direction_deg, heading
                    )
                    drone.battery = max(drone.battery - drain, 0.0)

            if self.gps_denied and drone.status in ("assigned", "returning", "on_station"):
                drone.lat += random.gauss(0, 3 / self.METERS_PER_LAT_DEG)
                drone.lng += random.gauss(0, 3 / self.METERS_PER_LNG_DEG)

        self._runtime_collision_check()
