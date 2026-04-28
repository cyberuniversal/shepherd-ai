import asyncio
from typing import Dict, List, Tuple

try:
    from mavsdk import System
except ImportError:
    System = None


class DroneBridge:
    """Optional MAVSDK bridge for PX4/ArduPilot SITL or real autopilots."""

    def __init__(self):
        self.systems: Dict[str, object] = {}

    def _require_mavsdk(self):
        if System is None:
            raise RuntimeError("mavsdk is not installed. Install backend requirements and enable live_mode before use.")

    async def connect(self, drone_id: str, address: str):
        self._require_mavsdk()
        drone = System()
        await drone.connect(system_address=address)
        self.systems[drone_id] = drone
        return drone

    async def arm_and_takeoff(self, drone_id: str, altitude_m: float = 10.0):
        drone = self.systems[drone_id]
        await drone.action.set_takeoff_altitude(altitude_m)
        await drone.action.arm()
        await drone.action.takeoff()

    async def goto_position(self, drone_id: str, lat: float, lng: float, alt: float):
        drone = self.systems[drone_id]
        await drone.action.goto_location(lat, lng, alt, 0.0)

    async def follow_waypoints(self, drone_id: str, waypoints: List[Tuple[float, float, float]]):
        if drone_id not in self.systems:
            return {"queued": False, "reason": "not_connected"}
        for lat, lng, alt in waypoints:
            await self.goto_position(drone_id, lat, lng, alt)
        return {"queued": True}

    async def execute_steps(self, drone_id: str, steps: List[Dict]):
        """Execute SHEPHERD-IR steps against a MAVSDK System."""
        if drone_id not in self.systems:
            return {"executed": False, "reason": "not_connected"}

        for step in steps:
            op = step.get("op")
            if op == "ARM":
                await self.systems[drone_id].action.arm()
            elif op == "TAKEOFF":
                await self.arm_and_takeoff(drone_id, step.get("altitude_m", 10.0))
            elif op == "GOTO":
                await self.goto_position(drone_id, step["lat"], step["lng"], step.get("altitude_m", 10.0))
            elif op == "HOLD":
                await asyncio.sleep(step.get("duration_s", 1))
            elif op == "RTL":
                await self.return_to_launch(drone_id)
            elif op == "LAND":
                await self.systems[drone_id].action.land()
            elif op == "KILL":
                await self.emergency_stop(drone_id)

        return {"executed": True}

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
        drone = self.systems[drone_id]
        async for position in drone.telemetry.position():
            return {
                "lat": position.latitude_deg,
                "lng": position.longitude_deg,
                "alt": position.relative_altitude_m,
            }

    async def emergency_stop(self, drone_id: str):
        if drone_id in self.systems:
            await self.systems[drone_id].action.kill()
