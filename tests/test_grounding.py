import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import (  # noqa: E402
    ground_intent,
    ground_phrase,
    grounded_map_objects,
    load_map_locations,
    load_map_locations_geojson,
)
from shepherd_ai.intent import parse_intent  # noqa: E402


MAP_PATH = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"
GEOJSON_MAP_PATH = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.geojson"
GEOJSON_REGION_MAP_PATH = ROOT / "datasets" / "maps" / "shepherd_test_map_regions_v1.geojson"


class GroundingTests(unittest.TestCase):
    def test_load_map_locations_validates_development_map(self) -> None:
        locations = load_map_locations(MAP_PATH)

        ids = {location.id for location in locations}
        self.assertIn("loc_north_field", ids)
        self.assertIn("loc_irrigation_canal", ids)
        self.assertGreater(len(locations), 5)
        north_field = next(location for location in locations if location.id == "loc_north_field")
        self.assertEqual(north_field.geometry_type, "circle")
        self.assertEqual(north_field.map_role, "mission_area")
        self.assertTrue(north_field.flyable)
        self.assertFalse(north_field.requires_clearance)

    def test_load_map_locations_supports_geojson_point_features(self) -> None:
        locations = load_map_locations(GEOJSON_MAP_PATH)

        ids = {location.id for location in locations}
        self.assertEqual(ids, {"loc_north_field", "loc_irrigation_canal", "zone_maintenance_yard"})
        north_field = next(location for location in locations if location.id == "loc_north_field")
        self.assertEqual(north_field.latitude, 24.0)
        self.assertEqual(north_field.longitude, 46.0)
        self.assertIn("crops", north_field.aliases)

    def test_load_map_locations_supports_geojson_polygon_features(self) -> None:
        locations = load_map_locations(GEOJSON_REGION_MAP_PATH)

        polygon = next(location for location in locations if location.id == "poly_north_field")
        self.assertEqual(polygon.geometry_type, "polygon")
        self.assertEqual(len(polygon.boundary), 4)
        self.assertAlmostEqual(polygon.latitude, 24.0, places=4)
        self.assertAlmostEqual(polygon.longitude, 46.0, places=4)
        self.assertGreater(polygon.radius_m, 0)
        self.assertIn("north polygon", polygon.aliases)

    def test_geojson_loader_rejects_unsupported_geometry_features(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "map.geojson"
            path.write_text(
                json.dumps(
                    {
                        "type": "FeatureCollection",
                        "features": [
                            {
                                "type": "Feature",
                                "geometry": {
                                    "type": "LineString",
                                    "coordinates": [
                                        [0, 0],
                                        [1, 1],
                                    ],
                                },
                                "properties": {},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "Point or Polygon geometry"):
                load_map_locations_geojson(path)

    def test_ground_phrase_matches_exact_alias(self) -> None:
        locations = load_map_locations(MAP_PATH)

        result = ground_phrase("canal", locations, field_name="target")

        self.assertEqual(result.status, "grounded")
        self.assertEqual(result.location.id, "loc_irrigation_canal")
        self.assertEqual(result.confidence, 0.9)

    def test_ground_phrase_matches_name_with_article_removed(self) -> None:
        locations = load_map_locations(MAP_PATH)

        result = ground_phrase("the Greenhouse", locations, field_name="target")

        self.assertEqual(result.status, "grounded")
        self.assertEqual(result.location.id, "loc_greenhouse")
        self.assertEqual(result.confidence, 1.0)

    def test_ground_phrase_reports_unresolved_phrase(self) -> None:
        locations = load_map_locations(MAP_PATH)

        result = ground_phrase("stalled vehicles", locations, field_name="target")

        self.assertEqual(result.status, "unresolved")
        self.assertIsNone(result.location)
        self.assertEqual(result.candidates, ())

    def test_ground_phrase_reports_ambiguous_alias(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "map.csv"
            path.write_text(
                "\n".join(
                    [
                        "id,name,category,latitude,longitude,radius_m,geometry_type,map_role,flyable,requires_clearance,aliases,source,split",
                        "loc_a,Alpha Field,field,1,1,10,circle,mission_area,true,false,shared,unit_test,development",
                        "loc_b,Beta Field,field,2,2,10,circle,mission_area,true,false,shared,unit_test,development",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            locations = load_map_locations(path)

        result = ground_phrase("shared", locations)

        self.assertEqual(result.status, "ambiguous")
        self.assertEqual([candidate.id for candidate in result.candidates], ["loc_a", "loc_b"])

    def test_ground_phrase_matches_map_alias_inside_larger_phrase(self) -> None:
        locations = load_map_locations(MAP_PATH)

        result = ground_phrase("traffic on the main road", locations, field_name="target")

        self.assertEqual(result.status, "grounded")
        self.assertEqual(result.location.id, "loc_main_road")
        self.assertEqual(result.confidence, 0.75)

    def test_ground_phrase_reports_ambiguous_embedded_alias(self) -> None:
        locations = load_map_locations(MAP_PATH)

        result = ground_phrase("traffic on the road", locations, field_name="target")

        self.assertEqual(result.status, "ambiguous")
        self.assertEqual(
            {candidate.id for candidate in result.candidates},
            {"loc_service_road", "loc_main_road"},
        )

    def test_development_map_contains_ambiguous_road_alias(self) -> None:
        locations = load_map_locations(MAP_PATH)

        result = ground_phrase("road", locations)

        self.assertEqual(result.status, "ambiguous")
        self.assertEqual(
            {candidate.id for candidate in result.candidates},
            {"loc_service_road", "loc_main_road"},
        )

    def test_ground_intent_preserves_intent_and_ready_status(self) -> None:
        locations = load_map_locations(MAP_PATH)
        intent = parse_intent("Send two drones north and inspect the crops.")

        grounded = ground_intent(intent, locations)

        self.assertTrue(grounded.ready_for_planning)
        self.assertEqual(grounded.intent["parser"], "deterministic_v3")
        refs = {reference.field: reference for reference in grounded.references}
        self.assertEqual(refs["location"].location.id, "loc_north_field")
        self.assertEqual(refs["target"].location.id, "loc_north_field")
        self.assertEqual(grounded.issues, ())

        map_objects = grounded_map_objects(grounded)
        self.assertEqual([map_object.location_id for map_object in map_objects], ["loc_north_field", "loc_north_field"])
        self.assertEqual(map_objects[0].center, {"latitude": 24.0, "longitude": 46.0})
        self.assertEqual(map_objects[0].map_role, "mission_area")

    def test_ground_intent_keeps_unresolved_targets_as_issues(self) -> None:
        locations = load_map_locations(MAP_PATH)
        intent = parse_intent("Scan the service road for stalled vehicles.")

        grounded = ground_intent(intent, locations)

        self.assertTrue(grounded.ready_for_planning)
        self.assertIn("target_unresolved", grounded.issues)
        refs = {reference.field: reference for reference in grounded.references}
        self.assertEqual(refs["location"].location.id, "loc_service_road")
        self.assertEqual(refs["target"].status, "unresolved")

    def test_ground_intent_without_any_map_reference_is_not_ready(self) -> None:
        locations = load_map_locations(MAP_PATH)
        intent = parse_intent("Capture images of the red pickup truck.")

        grounded = ground_intent(intent, locations)

        self.assertFalse(grounded.ready_for_planning)
        self.assertIn("no_grounded_map_reference", grounded.issues)

    def test_restricted_area_metadata_is_reported_as_issues(self) -> None:
        locations = load_map_locations(MAP_PATH)
        intent = parse_intent("Inspect the restricted area.")

        grounded = ground_intent(intent, locations)

        self.assertIn("target_not_flyable", grounded.issues)
        self.assertIn("target_requires_clearance", grounded.issues)
        map_objects = grounded_map_objects(grounded)
        self.assertEqual(map_objects[0].location_id, "zone_maintenance_yard")
        self.assertFalse(map_objects[0].flyable)
        self.assertTrue(map_objects[0].requires_clearance)

    def test_ground_intent_surfaces_constraint_map_references(self) -> None:
        locations = load_map_locations(MAP_PATH)
        intent = parse_intent("Inspect the greenhouse and avoid the power lines.")

        grounded = ground_intent(intent, locations)

        refs = {reference.field: reference for reference in grounded.references}
        self.assertEqual(refs["target"].location.id, "loc_greenhouse")
        self.assertEqual(refs["constraint[0]"].status, "grounded")
        self.assertEqual(refs["constraint[0]"].location.id, "obs_power_lines")
        self.assertIn("constraint[0]_not_flyable", grounded.issues)
        self.assertIn("constraint[0]_requires_clearance", grounded.issues)

    def test_load_map_locations_rejects_duplicate_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "map.csv"
            path.write_text(
                "\n".join(
                    [
                        "id,name,category,latitude,longitude,radius_m,geometry_type,map_role,flyable,requires_clearance,aliases,source,split",
                        "loc_a,Alpha Field,field,1,1,10,circle,mission_area,true,false,alpha,unit_test,development",
                        "loc_a,Beta Field,field,2,2,10,circle,mission_area,true,false,beta,unit_test,development",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "duplicate map location id"):
                load_map_locations(path)

    def test_load_map_locations_rejects_invalid_schema_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "map.csv"
            path.write_text(
                "\n".join(
                    [
                        "id,name,category,latitude,longitude,radius_m,geometry_type,map_role,flyable,requires_clearance,aliases,source,split",
                        "loc_a,Alpha Field,field,1,1,10,multipolygon,mission_area,true,false,alpha,unit_test,development",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "unsupported geometry_type"):
                load_map_locations(path)


if __name__ == "__main__":
    unittest.main()
