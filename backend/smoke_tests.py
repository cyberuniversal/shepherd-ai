import asyncio

from backend.controller import SwarmManager
from backend.action_script import synthesize_action_script
from backend.brain import MissionParser
from backend.mission_program import compile_mission_program
from backend.safety import ForbiddenZone, validate_mission_program, validate_route_leg
from backend.spatial import resolve_relative_target
from hardware_bridge.facade import FacadeCommandRejected, MAVSDKFacade


class FakeAction:
    def __init__(self):
        self.calls = []

    async def arm(self):
        self.calls.append(("arm",))

    async def set_takeoff_altitude(self, altitude):
        self.calls.append(("set_takeoff_altitude", altitude))

    async def takeoff(self):
        self.calls.append(("takeoff",))

    async def goto_location(self, lat, lng, alt, yaw):
        self.calls.append(("goto_location", lat, lng, alt, yaw))

    async def return_to_launch(self):
        self.calls.append(("return_to_launch",))

    async def land(self):
        self.calls.append(("land",))


class FakeSystem:
    def __init__(self):
        self.action = FakeAction()


class FakeBridge:
    def status(self):
        return {
            "mavsdk_available": True,
            "connected_count": 1,
            "connected_drones": [{"drone_id": "alpha-1", "address": "udp://:14540"}],
        }

    async def get_all_telemetry(self):
        return {
            "alpha-1": {
                "telemetry_ok": True,
                "drone_id": "alpha-1",
                "address": "udp://:14540",
                "lat": 24.7201,
                "lng": 46.6812,
                "alt": 17.5,
                "battery_percent": 88.0,
                "flight_mode": "HOLD",
                "updated_at": 123.0,
            }
        }


def test_relative_target_resolution():
    target = resolve_relative_target(
        (24.7136, 46.6753),
        330,
        {
            "kafd": (24.7610, 46.6402),
            "masmak": (24.6312, 46.7133),
        },
        direction="front",
        cone_deg=90,
    )
    assert target is not None
    assert target["name"] == "kafd"


def test_geometric_sandbox_blocks_forbidden_polygon():
    zone = ForbiddenZone(
        "test_square",
        [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0)],
        "test_zone",
    )
    blocked = validate_route_leg("alpha-1", (0.5, -1.0), (0.5, 2.0), 10.0, forbidden_zones=[zone])
    assert not blocked["passed"]
    clear = validate_route_leg("alpha-1", (24.70, 46.60), (24.71, 46.61), 10.0, forbidden_zones=[zone])
    assert clear["passed"], clear["issues"]


def test_mission_program_safety_passes_normal_riyadh_route():
    swarm = SwarmManager()
    assigned, _ = swarm.allocate_task(24.7610, 46.6402, required_drones=1)
    drones = [swarm.fleet[drone_id] for drone_id in assigned]
    program = compile_mission_program(
        "send one drone to kafd",
        {"action": "scout", "target_zone": "kafd", "pattern": "perimeter"},
        {"lat": 24.7610, "lng": 46.6402},
        drones,
        live_mode=False,
    )
    safety = validate_mission_program(program, {drone.id: (drone.lat, drone.lng) for drone in drones})
    assert safety["passed"], safety["issues"]


def test_action_script_has_no_artificial_route_events():
    swarm = SwarmManager()
    assigned, _ = swarm.allocate_task(24.7610, 46.6402, required_drones=1)
    drones = [swarm.fleet[drone_id] for drone_id in assigned]
    program = compile_mission_program(
        "send one drone to kafd",
        {"action": "scout", "target_zone": "kafd", "pattern": "perimeter"},
        {"lat": 24.7610, "lng": 46.6402},
        drones,
        live_mode=False,
    )
    script = synthesize_action_script(program)
    assert script["sensor_events"] == []
    assert script["route_patches"] == []
    assert "ooda_events" not in script
    assert "reroute" not in script["script"].lower()


async def test_facade_allows_only_safe_ops():
    system = FakeSystem()
    facade = MAVSDKFacade({"alpha-1": system})
    result = await facade.execute_steps(
        "alpha-1",
        [
            {"op": "ARM"},
            {"op": "TAKEOFF", "altitude_m": 10},
            {"op": "GOTO", "lat": 24.7610, "lng": 46.6402, "altitude_m": 10},
            {"op": "RTL"},
        ],
    )
    assert result["executed"]

    try:
        await facade.execute_steps("alpha-1", [{"op": "KILL"}])
    except FacadeCommandRejected:
        return
    raise AssertionError("KILL operation should be rejected by facade")


async def test_live_telemetry_sync_updates_digital_twin():
    swarm = SwarmManager()
    swarm.live_mode = True
    swarm.bridge = FakeBridge()
    swarm.mark_live_connected("alpha-1", "udp://:14540")
    swarm.fleet["alpha-1"].status = "assigned"
    swarm.fleet["alpha-1"].target = (24.9000, 46.9000)

    result = await swarm.sync_live_telemetry()
    drone = swarm.fleet["alpha-1"]
    assert result["synced"]
    assert drone.live_connected
    assert drone.lat == 24.7201
    assert drone.lng == 46.6812
    assert drone.altitude_m == 17.5
    assert drone.battery == 88.0
    assert drone.nav_state.position_source == "mavsdk_telemetry"

    swarm.step_simulation()
    assert drone.lat == 24.7201
    assert drone.lng == 46.6812


async def test_operator_reference_command_parse():
    parser = MissionParser()
    parser._ollama_available = False
    intent = await parser.parse_intent("Bring two drones to me")
    assert intent["drone_count"] == 2
    assert intent["target_reference"] == "operator"
    assert intent["target_zone"] == "operator_current_position"
    assert intent["action"] == "rendezvous"

    al_nada_intent = await parser.parse_intent("Bring two drones to Al Nada")
    assert al_nada_intent["drone_count"] == 2
    assert al_nada_intent["target_zone"] == "al nada"


async def test_mission_plan_preview_does_not_move_real_swarm():
    from backend import main as backend_main

    backend_main.parser._ollama_available = False
    backend_main.PENDING_MISSION_PLANS.clear()
    real_statuses = {drone_id: drone.status for drone_id, drone in backend_main.swarm.fleet.items()}

    response = await backend_main.create_mission_plan(
        backend_main.CommandInput(command="Send two drones to Al Nada", selected_drones=[])
    )

    assert response["plan_id"] in backend_main.PENDING_MISSION_PLANS
    assert response["status"] == "pending_confirmation"
    assert response["plan_summary"]["confirmable"]
    assert response["execution_results"][0]["mode"] == "pending_confirmation"
    assert {drone_id: drone.status for drone_id, drone in backend_main.swarm.fleet.items()} == real_statuses

    cancelled = await backend_main.cancel_mission_plan(backend_main.MissionPlanRef(plan_id=response["plan_id"]))
    assert cancelled["cancelled"]


def main():
    test_relative_target_resolution()
    test_geometric_sandbox_blocks_forbidden_polygon()
    test_mission_program_safety_passes_normal_riyadh_route()
    test_action_script_has_no_artificial_route_events()
    asyncio.run(test_facade_allows_only_safe_ops())
    asyncio.run(test_live_telemetry_sync_updates_digital_twin())
    asyncio.run(test_operator_reference_command_parse())
    asyncio.run(test_mission_plan_preview_does_not_move_real_swarm())
    print("backend smoke tests passed")


if __name__ == "__main__":
    main()
