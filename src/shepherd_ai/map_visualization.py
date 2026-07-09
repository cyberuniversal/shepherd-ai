"""Folium map rendering for Shepherd-AI grounding artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from shepherd_ai.grounding import GroundedIntent, MapLocation


def render_map(
    locations: Iterable[MapLocation],
    output_path: str | Path,
    *,
    grounded_intent: GroundedIntent | None = None,
    title: str = "Shepherd-AI Grounding Map",
) -> Path:
    """Render map locations and optional grounding results to an HTML file."""

    try:
        import folium
    except ImportError as exc:
        raise RuntimeError("folium is required for map visualization") from exc

    map_locations = list(locations)
    if not map_locations:
        raise ValueError("at least one map location is required")

    center_latitude = sum(location.latitude for location in map_locations) / len(map_locations)
    center_longitude = sum(location.longitude for location in map_locations) / len(map_locations)
    folium_map = folium.Map(location=[center_latitude, center_longitude], zoom_start=16)

    folium.Marker(
        location=[center_latitude, center_longitude],
        popup=title,
        tooltip=title,
        icon=folium.Icon(color="blue", icon="info-sign"),
    ).add_to(folium_map)

    grounded_ids = _grounded_location_ids(grounded_intent)
    candidate_ids = _candidate_location_ids(grounded_intent)

    for location in map_locations:
        color = _location_color(location.id, grounded_ids, candidate_ids)
        popup = _location_popup(location)
        if location.geometry_type == "polygon" and location.boundary:
            folium.Polygon(
                locations=[[latitude, longitude] for latitude, longitude in location.boundary],
                popup=popup,
                tooltip=f"{location.id}: {location.name}",
                color=color,
                fill=True,
                fill_opacity=0.18,
                weight=2,
            ).add_to(folium_map)
        else:
            folium.Circle(
                location=[location.latitude, location.longitude],
                radius=location.radius_m,
                popup=popup,
                tooltip=f"{location.id}: {location.name}",
                color=color,
                fill=True,
                fill_opacity=0.18,
                weight=2,
            ).add_to(folium_map)
        folium.Marker(
            location=[location.latitude, location.longitude],
            popup=popup,
            tooltip=location.name,
            icon=folium.Icon(color=color, icon="map-marker"),
        ).add_to(folium_map)

    if grounded_intent is not None:
        _add_grounding_summary(folium_map, grounded_intent)

    html_path = Path(output_path)
    html_path.parent.mkdir(parents=True, exist_ok=True)
    folium_map.save(str(html_path))
    return html_path


def _grounded_location_ids(grounded_intent: GroundedIntent | None) -> set[str]:
    if grounded_intent is None:
        return set()
    return {
        reference.location.id
        for reference in grounded_intent.references
        if reference.location is not None and reference.status == "grounded"
    }


def _candidate_location_ids(grounded_intent: GroundedIntent | None) -> set[str]:
    if grounded_intent is None:
        return set()
    return {
        candidate.id
        for reference in grounded_intent.references
        if reference.status == "ambiguous"
        for candidate in reference.candidates
    }


def _location_color(location_id: str, grounded_ids: set[str], candidate_ids: set[str]) -> str:
    if location_id in grounded_ids:
        return "green"
    if location_id in candidate_ids:
        return "orange"
    return "gray"


def _location_popup(location: MapLocation) -> str:
    aliases = ", ".join(location.aliases) if location.aliases else "none"
    return (
        f"<b>{location.name}</b><br>"
        f"id: {location.id}<br>"
        f"category: {location.category}<br>"
        f"role: {location.map_role}<br>"
        f"geometry: {location.geometry_type}<br>"
        f"radius_m: {location.radius_m}<br>"
        f"flyable: {location.flyable}<br>"
        f"requires_clearance: {location.requires_clearance}<br>"
        f"aliases: {aliases}<br>"
        f"source: {location.source}<br>"
        f"split: {location.split}"
    )


def _add_grounding_summary(folium_map: object, grounded_intent: GroundedIntent) -> None:
    import folium

    rows = []
    for reference in grounded_intent.references:
        location_id = reference.location.id if reference.location else ""
        candidate_ids = ", ".join(candidate.id for candidate in reference.candidates)
        rows.append(
            "<tr>"
            f"<td>{reference.field}</td>"
            f"<td>{reference.phrase or ''}</td>"
            f"<td>{reference.status}</td>"
            f"<td>{location_id}</td>"
            f"<td>{candidate_ids}</td>"
            "</tr>"
        )

    html = (
        "<div style='font-family: sans-serif; font-size: 13px;'>"
        "<h4>Grounding Summary</h4>"
        f"<p><b>Ready for planning:</b> {grounded_intent.ready_for_planning}</p>"
        "<table border='1' cellpadding='4' cellspacing='0'>"
        "<tr><th>field</th><th>phrase</th><th>status</th><th>location</th><th>candidates</th></tr>"
        + "".join(rows)
        + "</table>"
        "</div>"
    )
    folium_map.get_root().html.add_child(folium.Element(html))
