import asyncio
import time
from typing import Dict, List, Tuple

try:
    from hardware_bridge.facade import FacadeCommandRejected, MAVSDKFacade
except ImportError:
    FacadeCommandRejected = RuntimeError
    MAVSDKFacade = None

try:
    from mavsdk import System
except ImportError:
    System = None


class DroneBridge:
    """Optional MAVSDK bridge for PX4/ArduPilot SITL or real autopilots."""

    def __init__(self):
        self.systems: Dict[str, object] = {}
        self.addresses: Dict[str, str] = {}
        self.last_telemetry: Dict[str, Dict] = {}
        self.last_errors: Dict[str, str] = {}
        self.connection_attempts: Dict[str, Dict] = {}
        self.facade = MAVSDKFacade(self.systems) if MAVSDKFacade else None

    def _require_mavsdk(self):
        if System is None:
            raise RuntimeError("mavsdk is not installed. Install backend requirements and enable live_mode before use.")

    async def _wait_connected(self, drone, timeout_s: float = 8.0):
        async def wait_loop():
            async for state in drone.core.connection_state():
                if state.is_connected:
                    return True

        return await asyncio.wait_for(wait_loop(), timeout=timeout_s)

    async def connect(self, drone_id: str, address: str):
        self._require_mavsdk()
        self.connection_attempts[drone_id] = {
            "address": address,
            "state": "connecting",
            "started_at": time.time(),
            "message": "Waiting for MAVLink heartbeat from PX4/ArduPilot.",
        }
        try:
            drone = System()
            await drone.connect(system_address=address)
            await self._wait_connected(drone)
            self.systems[drone_id] = drone
            self.addresses[drone_id] = address
            self.last_errors.pop(drone_id, None)
            self.connection_attempts[drone_id].update({
                "state": "connected",
                "connected_at": time.time(),
                "message": "MAVLink heartbeat received.",
            })
            return drone
        except Exception as exc:
            self.last_errors[drone_id] = str(exc)
            self.connection_attempts[drone_id].update({
                "state": "failed",
                "failed_at": time.time(),
                "message": str(exc) or "MAVLink connection failed.",
            })
            raise

    async def _first_telemetry_value(self, stream, timeout_s: float = 0.8):
        try:
            return await asyncio.wait_for(anext(stream), timeout=timeout_s)
        except Exception:
            return None

    async def arm_and_takeoff(self, drone_id: str, altitude_m: float = 10.0):
        await self.facade.arm(drone_id)
        await self.facade.takeoff(drone_id, altitude_m)

    async def goto_position(self, drone_id: str, lat: float, lng: float, alt: float):
        await self.facade.goto(drone_id, lat, lng, alt)

    async def follow_waypoints(self, drone_id: str, waypoints: List[Tuple[float, float, float]]):
        if drone_id not in self.systems:
            return {"queued": False, "reason": "not_connected"}
        try:
            for lat, lng, alt in waypoints:
                await self.goto_position(drone_id, lat, lng, alt)
            return {"queued": True, "facade": "MAVSDKFacade"}
        except FacadeCommandRejected as exc:
            return {"queued": False, "reason": str(exc), "facade": "MAVSDKFacade"}

    async def execute_steps(self, drone_id: str, steps: List[Dict]):
        """Execute SHEPHERD-IR steps against a MAVSDK System."""
        if drone_id not in self.systems:
            return {"executed": False, "reason": "not_connected"}

        try:
            return await self.facade.execute_steps(drone_id, steps)
        except FacadeCommandRejected as exc:
            return {"executed": False, "reason": str(exc), "facade": "MAVSDKFacade"}

    async def execute_program(self, program: Dict):
        results = {}
        for drone_program in program.get("drone_programs", []):
            results[drone_program["drone_id"]] = await self.execute_steps(
                drone_program["drone_id"],
                drone_program.get("steps", []),
            )
        return results

    async def return_to_launch(self, drone_id: str):
        drone = self.systems[drone_id]
        await drone.action.return_to_launch()

    async def get_telemetry(self, drone_id: str) -> Dict:
        if drone_id not in self.systems:
            return {"telemetry_ok": False, "reason": "not_connected"}

        drone = self.systems[drone_id]
        telemetry = drone.telemetry
        try:
            position = await self._first_telemetry_value(telemetry.position())
            battery = await self._first_telemetry_value(telemetry.battery(), timeout_s=0.5)
            in_air = await self._first_telemetry_value(telemetry.in_air(), timeout_s=0.5)
            flight_mode = await self._first_telemetry_value(telemetry.flight_mode(), timeout_s=0.5)

            data = {
                "telemetry_ok": position is not None,
                "drone_id": drone_id,
                "address": self.addresses.get(drone_id),
                "updated_at": time.time(),
                "in_air": bool(in_air) if in_air is not None else None,
                "flight_mode": str(flight_mode) if flight_mode is not None else None,
            }
            if position is not None:
                data.update({
                    "lat": position.latitude_deg,
                    "lng": position.longitude_deg,
                    "alt": position.relative_altitude_m,
                })
            if battery is not None and getattr(battery, "remaining_percent", None) is not None:
                data["battery_percent"] = max(0.0, min(float(battery.remaining_percent) * 100.0, 100.0))

            self.last_telemetry[drone_id] = data
            self.last_errors.pop(drone_id, None)
            return data
        except Exception as exc:
            self.last_errors[drone_id] = str(exc)
            return {"telemetry_ok": False, "drone_id": drone_id, "reason": str(exc), "updated_at": time.time()}

    async def get_all_telemetry(self) -> Dict[str, Dict]:
        results = await asyncio.gather(
            *(self.get_telemetry(drone_id) for drone_id in self.systems),
            return_exceptions=True,
        )
        telemetry = {}
        for drone_id, result in zip(self.systems.keys(), results):
            if isinstance(result, Exception):
                telemetry[drone_id] = {"telemetry_ok": False, "reason": str(result), "updated_at": time.time()}
            else:
                telemetry[drone_id] = result
        return telemetry

    def status(self) -> Dict:
        return {
            "mavsdk_available": System is not None,
            "expected_sitl_endpoint": "udp://:14540",
            "connected_count": len(self.systems),
            "connection_attempts": self.connection_attempts,
            "hint": "Start PX4 SITL first, then connect Shepherd-AI to udp://:14540." if System is not None else "Install backend requirements so mavsdk can be imported.",
            "connected_drones": [
                {
                    "drone_id": drone_id,
                    "address": self.addresses.get(drone_id),
                    "last_telemetry_at": self.last_telemetry.get(drone_id, {}).get("updated_at"),
                    "last_error": self.last_errors.get(drone_id),
                }
                for drone_id in self.systems
            ],
        }

    async def emergency_stop(self, drone_id: str):
        if drone_id in self.systems:
            await self.systems[drone_id].action.kill()

    async def listen_distance_sensor(self, drone_id: str, on_obstacle, threshold_m: float = 2.0):
        """Monitor MAVSDK distance telemetry and report close obstacles."""
        if drone_id not in self.systems:
            return {"listening": False, "reason": "not_connected"}

        telemetry = self.systems[drone_id].telemetry
        async for reading in telemetry.distance_sensor():
            distance_m = getattr(reading, "current_distance_m", None)
            if distance_m is not None and distance_m < threshold_m:
                await on_obstacle({"drone_id": drone_id, "distance_m": distance_m})
                await asyncio.sleep(0.5)

        return {"listening": True}
