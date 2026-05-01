import asyncio
from typing import Dict, List


class FacadeCommandRejected(RuntimeError):
    pass


class MAVSDKFacade:
    """High-level live-flight command facade.

    The rest of the system can ask for safe mission operations, but it never
    receives the raw MAVSDK System object or direct actuator primitives.
    """

    ALLOWED_OPS = {"ARM", "TAKEOFF", "GOTO", "HOLD", "RTL", "LAND"}
    MAX_ALTITUDE_M = 120.0
    MIN_ALTITUDE_M = 1.0

    def __init__(self, systems: Dict[str, object]):
        self._systems = systems

    def _system(self, drone_id: str):
        if drone_id not in self._systems:
            raise FacadeCommandRejected(f"{drone_id} is not connected")
        return self._systems[drone_id]

    def _validate_altitude(self, altitude_m: float):
        altitude = float(altitude_m)
        if altitude < self.MIN_ALTITUDE_M or altitude > self.MAX_ALTITUDE_M:
            raise FacadeCommandRejected(f"altitude {altitude:.1f}m outside safe envelope")
        return altitude

    def _validate_coordinate(self, lat: float, lng: float):
        lat = float(lat)
        lng = float(lng)
        if not -90.0 <= lat <= 90.0:
            raise FacadeCommandRejected("latitude out of bounds")
        if not -180.0 <= lng <= 180.0:
            raise FacadeCommandRejected("longitude out of bounds")
        return lat, lng

    async def arm(self, drone_id: str):
        await self._system(drone_id).action.arm()

    async def takeoff(self, drone_id: str, altitude_m: float = 10.0):
        altitude = self._validate_altitude(altitude_m)
        drone = self._system(drone_id)
        await drone.action.set_takeoff_altitude(altitude)
        await drone.action.takeoff()

    async def goto(self, drone_id: str, lat: float, lng: float, altitude_m: float = 10.0):
        lat, lng = self._validate_coordinate(lat, lng)
        altitude = self._validate_altitude(altitude_m)
        await self._system(drone_id).action.goto_location(lat, lng, altitude, 0.0)

    async def hold(self, duration_s: float = 1.0):
        await asyncio.sleep(max(0.0, float(duration_s)))

    async def rtl(self, drone_id: str):
        await self._system(drone_id).action.return_to_launch()

    async def land(self, drone_id: str):
        await self._system(drone_id).action.land()

    async def execute_steps(self, drone_id: str, steps: List[Dict]):
        for step in steps:
            op = step.get("op")
            if op not in self.ALLOWED_OPS:
                raise FacadeCommandRejected(f"operation {op} is not allowed by MAVSDKFacade")

            if op == "ARM":
                await self.arm(drone_id)
            elif op == "TAKEOFF":
                await self.takeoff(drone_id, step.get("altitude_m", 10.0))
            elif op == "GOTO":
                await self.goto(drone_id, step["lat"], step["lng"], step.get("altitude_m", 10.0))
            elif op == "HOLD":
                await self.hold(step.get("duration_s", 1.0))
            elif op == "RTL":
                await self.rtl(drone_id)
            elif op == "LAND":
                await self.land(drone_id)

        return {"executed": True, "facade": "MAVSDKFacade", "allowed_ops": sorted(self.ALLOWED_OPS)}
