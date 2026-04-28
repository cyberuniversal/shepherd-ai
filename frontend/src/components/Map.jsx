import { useEffect, useRef, useState } from 'react';
import Map, { Layer, Marker, Source } from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';
import { Building2, Plane, GraduationCap, Tent, Castle, Shield, Landmark } from 'lucide-react';

const LANDMARKS = [
  { id: 'imam', name: 'Imam University', lat: 24.8144, lng: 46.7027, icon: GraduationCap },
  { id: 'airport', name: 'King Khalid Airport', lat: 24.9576, lng: 46.7000, icon: Plane },
  { id: 'kafd', name: 'KAFD', lat: 24.7610, lng: 46.6402, icon: Building2 },
  { id: 'wadi', name: 'Wadi Hanifah', lat: 24.6366, lng: 46.6120, icon: Tent },
  { id: 'kingdom', name: 'Kingdom Centre', lat: 24.7114, lng: 46.6744, icon: Building2 },
  { id: 'faisaliyah', name: 'Al Faisaliyah', lat: 24.6906, lng: 46.6851, icon: Building2 },
  { id: 'boulevard', name: 'Boulevard City', lat: 24.7675, lng: 46.6044, icon: Tent },
  { id: 'diriyah', name: 'Diriyah', lat: 24.7335, lng: 46.5750, icon: Castle },
  { id: 'masmak', name: 'Masmak Fortress', lat: 24.6312, lng: 46.7133, icon: Castle },
  { id: 'stadium', name: 'King Fahd Stadium', lat: 24.7886, lng: 46.8396, icon: Landmark },
  { id: 'ksu', name: 'King Saud University', lat: 24.7163, lng: 46.6190, icon: GraduationCap },
  { id: 'museum', name: 'National Museum', lat: 24.6473, lng: 46.7107, icon: Landmark },
  { id: 'mod', name: 'Ministry of Defense', lat: 24.6644, lng: 46.7126, icon: Shield },
];

const METERS_PER_LAT_DEG = 111320.0;
const METERS_PER_LNG_DEG = 101100.0;
const TARGET_RADIUS_M = 50.0;

const emptyFeatureCollection = {
  type: 'FeatureCollection',
  features: [],
};

const getMarkerStyle = (status) => {
  switch (status) {
    case 'offline': return { color: '#ef4444', bg: 'bg-destructive', pulse: false };
    case 'assigned': return { color: '#10b981', bg: 'bg-primary', pulse: true };
    case 'on_station': return { color: '#f59e0b', bg: 'bg-amber-500', pulse: true };
    case 'returning': return { color: '#3b82f6', bg: 'bg-blue-500', pulse: true };
    default: return { color: '#94a3b8', bg: 'bg-muted-foreground', pulse: false };
  }
};

const getBatteryColor = (battery) => {
  if (battery < 20) return '#ef4444';
  if (battery < 50) return '#f59e0b';
  return '#10b981';
};

const getNavColor = (confidence = 1) => {
  if (confidence < 0.3) return '#ef4444';
  if (confidence < 0.65) return '#f59e0b';
  return '#10b981';
};

const buildCirclePolygon = (lat, lng, radiusM = TARGET_RADIUS_M) => {
  const coordinates = [];
  for (let i = 0; i <= 64; i += 1) {
    const angle = (2 * Math.PI * i) / 64;
    coordinates.push([
      lng + (radiusM / METERS_PER_LNG_DEG) * Math.sin(angle),
      lat + (radiusM / METERS_PER_LAT_DEG) * Math.cos(angle),
    ]);
  }
  return coordinates;
};

const waypointToCoordinate = (waypoint) => [waypoint[1], waypoint[0]];

const formatDroneLabel = (id) => {
  const [squadron, number] = id.split('-');
  const prefix = { alpha: 'A', beta: 'B', gamma: 'G', delta: 'D' }[squadron] || id[0]?.toUpperCase() || '?';
  return `${prefix}${number || ''}`;
};

const MapComponent = ({ fleet, focusedDroneId }) => {
  const mapRef = useRef(null);
  const [trails, setTrails] = useState({});

  const handleMapLoad = (event) => {
    const map = event.target;
    if (!map || map.getLayer('3d-buildings')) return;

    const layers = map.getStyle().layers || [];
    const labelLayer = layers.find(layer => layer.type === 'symbol' && layer.layout?.['text-field']);
    const sources = map.getStyle().sources || {};
    const sourceId = ['openmaptiles', 'openfreemap', 'composite'].find(source => sources[source]);
    if (!sourceId) return;

    try {
      map.addLayer({
        id: '3d-buildings',
        source: sourceId,
        'source-layer': 'building',
        type: 'fill-extrusion',
        minzoom: 13,
        paint: {
          'fill-extrusion-color': '#1a2332',
          'fill-extrusion-height': ['coalesce', ['get', 'render_height'], ['get', 'height'], 12],
          'fill-extrusion-base': ['coalesce', ['get', 'render_min_height'], ['get', 'min_height'], 0],
          'fill-extrusion-opacity': 0.72,
          'fill-extrusion-vertical-gradient': true,
        },
      }, labelLayer?.id);
    } catch (err) {
      console.warn('3D buildings layer could not be added for this map style.', err);
    }
  };

  useEffect(() => {
    if (focusedDroneId && mapRef.current) {
      const drone = fleet.find(d => d.id === focusedDroneId);
      if (drone && drone.status !== 'offline') {
        mapRef.current.getMap().easeTo({
          center: [drone.lng, drone.lat],
          zoom: 16,
          pitch: 75,
          duration: 1000,
          essential: true,
        });
      }
    }
  }, [fleet, focusedDroneId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTrails((previousTrails) => {
      const nextTrails = { ...previousTrails };

      fleet.forEach((drone) => {
        if (drone.status === 'offline') {
          delete nextTrails[drone.id];
          return;
        }

        if (drone.status !== 'assigned' && drone.status !== 'returning') {
          delete nextTrails[drone.id];
          return;
        }

        const coordinate = [drone.lng, drone.lat];
        const currentTrail = nextTrails[drone.id] || [];
        const lastCoordinate = currentTrail[currentTrail.length - 1];
        const moved = !lastCoordinate ||
          Math.abs(lastCoordinate[0] - coordinate[0]) > 0.000001 ||
          Math.abs(lastCoordinate[1] - coordinate[1]) > 0.000001;

        if (moved) {
          nextTrails[drone.id] = [...currentTrail, coordinate].slice(-20);
        }
      });

      return nextTrails;
    });
  }, [fleet]);

  const fleetById = Object.fromEntries(fleet.map((drone) => [drone.id, drone]));

  const flightPaths = {
    type: 'FeatureCollection',
    features: fleet
      .filter((drone) => drone.status === 'assigned' || drone.status === 'returning')
      .filter((drone) => drone.target_lat !== null && drone.target_lng !== null)
      .map((drone) => ({
        type: 'Feature',
        properties: { status: drone.status, id: drone.id },
        geometry: {
          type: 'LineString',
          coordinates: [[drone.lng, drone.lat], [drone.target_lng, drone.target_lat]],
        },
      })),
  };

  const waypointPaths = {
    type: 'FeatureCollection',
    features: fleet
      .filter((drone) => drone.status === 'assigned' && drone.waypoints?.length > 1)
      .map((drone) => ({
        type: 'Feature',
        properties: { id: drone.id },
        geometry: {
          type: 'LineString',
          coordinates: [
            [drone.lng, drone.lat],
            ...drone.waypoints.slice(drone.waypoint_index || 0).map(waypointToCoordinate),
          ],
        },
      })),
  };

  const targetZones = {
    type: 'FeatureCollection',
    features: fleet.reduce((features, drone) => {
      if (drone.status !== 'assigned' && drone.status !== 'on_station') return features;

      const lat = drone.mission_target_lat ?? drone.target_lat;
      const lng = drone.mission_target_lng ?? drone.target_lng;
      if (lat === null || lng === null) return features;

      const key = `${lat.toFixed(5)}:${lng.toFixed(5)}`;
      if (features.some((feature) => feature.properties.key === key)) return features;

      features.push({
        type: 'Feature',
        properties: { key },
        geometry: {
          type: 'Polygon',
          coordinates: [buildCirclePolygon(lat, lng)],
        },
      });
      return features;
    }, []),
  };

  const targetCenters = targetZones.features.map((feature) => {
    const firstCoordinate = feature.geometry.coordinates[0][0];
    return {
      id: feature.properties.key,
      lng: Number(feature.properties.key.split(':')[1]),
      lat: Number(feature.properties.key.split(':')[0]),
      fallbackLng: firstCoordinate[0],
      fallbackLat: firstCoordinate[1],
    };
  });

  const trailPaths = {
    type: 'FeatureCollection',
    features: Object.entries(trails)
      .filter(([droneId, coordinates]) => {
        const drone = fleetById[droneId];
        return coordinates.length > 1 && (drone?.status === 'assigned' || drone?.status === 'returning');
      })
      .map(([droneId, coordinates]) => ({
        type: 'Feature',
        properties: { id: droneId },
        geometry: { type: 'LineString', coordinates },
      })),
  };

  return (
    <div className="relative h-full w-full map-scanline">
      <Map
        ref={mapRef}
        initialViewState={{
          longitude: 46.6753,
          latitude: 24.7136,
          zoom: 11,
          pitch: 60,
          bearing: -20,
        }}
        mapStyle="https://tiles.openfreemap.org/styles/dark"
        onLoad={handleMapLoad}
        style={{ width: '100%', height: '100%' }}
      >
      <Source id="target-zones" type="geojson" data={targetZones.features.length ? targetZones : emptyFeatureCollection}>
        <Layer
          id="target-zone-fill"
          type="fill"
          paint={{ 'fill-color': '#10b981', 'fill-opacity': 0.1 }}
        />
        <Layer
          id="target-zone-outline"
          type="line"
          paint={{ 'line-color': '#10b981', 'line-width': 2, 'line-opacity': 0.85 }}
        />
      </Source>

      <Source id="drone-trails" type="geojson" data={trailPaths.features.length ? trailPaths : emptyFeatureCollection} lineMetrics={true}>
        <Layer
          id="drone-trails-line"
          type="line"
          paint={{
            'line-width': 3,
            'line-gradient': ['interpolate', ['linear'], ['line-progress'], 0, 'rgba(16,185,129,0)', 1, '#10b981'],
          }}
        />
      </Source>

      <Source id="waypoint-paths" type="geojson" data={waypointPaths.features.length ? waypointPaths : emptyFeatureCollection}>
        <Layer
          id="waypoint-paths-line"
          type="line"
          paint={{ 'line-color': '#22d3ee', 'line-width': 2, 'line-opacity': 0.55, 'line-dasharray': [1, 1.2] }}
        />
      </Source>

      <Source id="flight-paths" type="geojson" data={flightPaths.features.length ? flightPaths : emptyFeatureCollection}>
        <Layer
          id="flight-paths-line"
          type="line"
          paint={{
            'line-color': ['match', ['get', 'status'], 'returning', '#f59e0b', '#10b981'],
            'line-width': 2,
            'line-opacity': 0.75,
            'line-dasharray': [2, 1.5],
          }}
        />
      </Source>

      {targetCenters.map((target) => (
        <Marker
          key={target.id}
          longitude={target.lng || target.fallbackLng}
          latitude={target.lat || target.fallbackLat}
          anchor="center"
        >
            <div className="pointer-events-none relative h-10 w-10 text-primary">
              <div className="pulse-ring"></div>
              <div className="target-zone-pulse absolute inset-2 rounded-full border border-primary bg-primary/10 shadow-[0_0_20px_rgba(16,185,129,0.35)]" />
            </div>
          </Marker>
      ))}

      {/* Render Landmarks */}
      {LANDMARKS.map(landmark => {
        const Icon = landmark.icon;
        return (
          <Marker
            key={landmark.id}
            longitude={landmark.lng}
            latitude={landmark.lat}
            anchor="bottom"
          >
            <div className="flex flex-col items-center group cursor-pointer z-10">
              <div className="bg-card border border-border px-2 py-1 rounded text-xs mb-1 opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap shadow-lg">
                {landmark.name}
              </div>
              <div className="w-8 h-8 rounded-full bg-secondary/80 border border-primary flex items-center justify-center text-primary shadow-[0_0_15px_rgba(16,185,129,0.3)]">
                <Icon size={16} />
              </div>
            </div>
          </Marker>
        );
      })}

      {/* Render Drones */}
      {fleet.map((drone) => {
        const markerStyle = getMarkerStyle(drone.status);
        const isOffline = drone.status === 'offline';
        const batteryCritical = drone.battery < 20 && !isOffline;
        const bgColorClass = batteryCritical ? 'bg-destructive' : markerStyle.bg;
        const shadowClass = isOffline ? 'shadow-[0_0_10px_theme(colors.destructive.DEFAULT)]' :
          markerStyle.pulse ? 'shadow-[0_0_10px_currentColor]' : '';
        const batteryWidth = `${Math.max(0, Math.min(drone.battery, 100))}%`;

        return (
          <Marker
            key={drone.id}
            longitude={drone.lng}
            latitude={drone.lat}
            anchor="center"
            style={{ zIndex: isOffline ? 0 : 50 }}
          >
            <div className="relative group cursor-pointer">
              {/* Tooltip */}
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 bg-card border border-border p-2 rounded text-xs opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap shadow-lg pointer-events-none z-50 min-w-32">
                <strong className="text-foreground">{drone.id.toUpperCase()}</strong><br />
                <span className="text-muted-foreground">Status:</span> {drone.status}<br />
                <span className="text-muted-foreground">Bat:</span> {drone.battery.toFixed(1)}%<br />
                <div className="mt-1 h-1.5 w-full rounded bg-muted overflow-hidden">
                  <div className="h-full rounded" style={{ width: batteryWidth, backgroundColor: getBatteryColor(drone.battery) }} />
                </div>
                <span className="text-muted-foreground">Rotor:</span> {drone.rotor_speed.toFixed(0)}%<br />
                <span className="text-muted-foreground">Nav:</span> {Math.round((drone.nav_confidence ?? 1) * 100)}% {drone.nav_source || 'gps'}<br />
                <span className="text-muted-foreground">Alt:</span> {Math.round(drone.altitude_m || 10)}m
              </div>

              {/* Drone Icon */}
              <div className="relative w-6 h-6 text-white" style={{ color: markerStyle.color }}>
                {markerStyle.pulse && <div className="pulse-ring"></div>}
                <div
                  className="absolute -right-1 -top-1 z-20 h-2.5 w-2.5 rounded-full border border-background"
                  style={{ backgroundColor: getNavColor(drone.nav_confidence) }}
                  title="Navigation confidence"
                />
                <div className={`absolute inset-0 border-2 border-white rounded-full flex items-center justify-center z-10 ${bgColorClass} ${shadowClass} ${batteryCritical ? 'animate-pulse ring-2 ring-destructive' : ''}`}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 2v20M2 12h20M12 12l8 8M12 12l-8-8M12 12l8-8M12 12l-8 8" />
                  </svg>
                </div>
                <div className="absolute left-1/2 top-full z-20 mt-1 -translate-x-1/2 rounded border border-border bg-card/90 px-1 py-0.5 text-[9px] font-bold leading-none text-foreground shadow-lg">
                  {formatDroneLabel(drone.id)}
                </div>
              </div>
            </div>
          </Marker>
        );
      })}
      </Map>

      <div className="absolute right-4 top-4 z-30 rounded-lg border border-border bg-card/85 p-3 text-[10px] font-mono uppercase tracking-wider text-muted-foreground shadow-lg backdrop-blur-sm">
        <div className="mb-2 text-foreground">Map Legend</div>
        <div className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-primary" />Assigned</div>
        <div className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-amber-500" />On Station</div>
        <div className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-blue-500" />Returning</div>
        <div className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-muted-foreground" />Idle</div>
        <div className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-destructive" />Offline</div>
      </div>
    </div>
  );
};

export default MapComponent;
