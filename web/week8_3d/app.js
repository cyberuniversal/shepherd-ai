import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const COLORS = [0x27a8dc, 0xe28a32, 0x67c95d, 0xd36cac, 0xe3c84c];
const WORLD_PER_METER = 0.08;
const BASE_MINUTES_PER_SECOND = 0.55;

const ui = {
  scene: document.querySelector("#scene"),
  loading: document.querySelector("#loading"),
  connection: document.querySelector("#connection-status"),
  command: document.querySelector("#mission-command"),
  run: document.querySelector("#run-mission"),
  clarification: document.querySelector("#clarification"),
  clarificationMessage: document.querySelector("#clarification-message"),
  clarificationOptions: document.querySelector("#clarification-options"),
  stageList: document.querySelector("#stage-list"),
  droneList: document.querySelector("#drone-list"),
  missionClock: document.querySelector("#mission-clock"),
  safetyStatus: document.querySelector("#safety-status"),
  separation: document.querySelector("#separation-value"),
  perception: document.querySelector("#perception-status"),
  timeline: document.querySelector("#timeline"),
  timelineOutput: document.querySelector("#timeline-output"),
  speed: document.querySelector("#speed"),
  playPause: document.querySelector("#play-pause"),
  restart: document.querySelector("#restart"),
  cameraMode: document.querySelector("#camera-mode"),
  resetCamera: document.querySelector("#reset-camera"),
  notice: document.querySelector("#notice"),
};

const state = {
  config: null,
  result: null,
  scene: null,
  missionTime: 0,
  playing: false,
  lastFrame: performance.now(),
  resolutions: {},
};

class MissionScene {
  constructor(host, config) {
    this.host = host;
    this.config = config;
    this.locations = config.map_locations;
    this.centerLat = this.locations.reduce((sum, item) => sum + item.latitude, 0) / this.locations.length;
    this.centerLon = this.locations.reduce((sum, item) => sum + item.longitude, 0) / this.locations.length;
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x718987);
    this.scene.fog = new THREE.Fog(0x718987, 95, 220);
    this.camera = new THREE.PerspectiveCamera(48, host.clientWidth / host.clientHeight, 0.1, 500);
    this.renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setSize(host.clientWidth, host.clientHeight);
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    host.appendChild(this.renderer.domElement);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.maxPolarAngle = Math.PI * 0.46;
    this.controls.minDistance = 24;
    this.controls.maxDistance = 170;
    this.droneMeshes = new Map();
    this.routeObjects = [];
    this.activeDroneId = null;
    this.cameraMode = "overview";
    this.buildWorld();
    this.resetCamera();
    window.addEventListener("resize", () => this.resize());
  }

  toWorld(latitude, longitude, altitude = 0) {
    const east = (longitude - this.centerLon) * 111320 * Math.cos(THREE.MathUtils.degToRad(this.centerLat));
    const north = (latitude - this.centerLat) * 111320;
    return new THREE.Vector3(east * WORLD_PER_METER, altitude * WORLD_PER_METER, -north * WORLD_PER_METER);
  }

  buildWorld() {
    this.scene.add(new THREE.HemisphereLight(0xdde9e5, 0x304139, 2.2));
    const sun = new THREE.DirectionalLight(0xfff1d1, 3.1);
    sun.position.set(-45, 75, -20);
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    sun.shadow.camera.left = -110;
    sun.shadow.camera.right = 110;
    sun.shadow.camera.top = 110;
    sun.shadow.camera.bottom = -110;
    this.scene.add(sun);

    const ground = new THREE.Mesh(
      new THREE.PlaneGeometry(220, 190),
      new THREE.MeshStandardMaterial({ color: 0x344d38, roughness: 0.98 }),
    );
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    this.scene.add(ground);

    const grid = new THREE.GridHelper(190, 38, 0x64796f, 0x43594e);
    grid.position.y = 0.025;
    grid.material.opacity = 0.32;
    grid.material.transparent = true;
    this.scene.add(grid);

    for (const location of this.locations) this.addLocation(location);
    for (const [index, drone] of this.config.drones.entries()) {
      const mesh = this.createDrone(COLORS[index % COLORS.length]);
      mesh.position.copy(this.toWorld(drone.current_latitude, drone.current_longitude, 0.8));
      mesh.userData.droneId = drone.drone_id;
      this.droneMeshes.set(drone.drone_id, mesh);
      this.scene.add(mesh);
    }
  }

  addLocation(location) {
    const position = this.toWorld(location.latitude, location.longitude);
    const radius = Math.max(location.radius_m * WORLD_PER_METER, 1.2);
    let color = 0x567b42;
    if (location.category === "waterway") color = 0x267da1;
    if (location.category === "structure" || location.category === "base") color = 0x88918b;
    if (!location.flyable) color = 0x9a4141;
    const area = new THREE.Mesh(
      new THREE.CylinderGeometry(radius, radius, 0.12, 48),
      new THREE.MeshStandardMaterial({ color, transparent: true, opacity: 0.68, roughness: 0.9 }),
    );
    area.position.set(position.x, 0.07, position.z);
    area.receiveShadow = true;
    this.scene.add(area);

    if (location.category === "field") this.addCropRows(position, radius, color);
    if (location.map_role === "base") this.addLandingPad(position, radius);
    const label = this.createLabel(location.name, location.flyable ? "#dfe7e2" : "#ffd7d7");
    label.position.set(position.x, 2.1, position.z);
    this.scene.add(label);
  }

  addCropRows(position, radius) {
    const rowMaterial = new THREE.MeshStandardMaterial({ color: 0x274d2d, roughness: 1 });
    const rowCount = 7;
    for (let index = 0; index < rowCount; index += 1) {
      const row = new THREE.Mesh(new THREE.BoxGeometry(radius * 1.45, 0.09, 0.22), rowMaterial);
      row.position.set(position.x, 0.18, position.z - radius * 0.54 + index * radius * 0.18);
      row.rotation.y = 0.12;
      row.castShadow = true;
      this.scene.add(row);
    }
  }

  addLandingPad(position, radius) {
    const pad = new THREE.Mesh(
      new THREE.CylinderGeometry(Math.min(radius * 0.65, 2.1), Math.min(radius * 0.65, 2.1), 0.16, 24),
      new THREE.MeshStandardMaterial({ color: 0x303a38, roughness: 0.72 }),
    );
    pad.position.set(position.x, 0.18, position.z);
    this.scene.add(pad);
  }

  createDrone(color) {
    const group = new THREE.Group();
    const bodyMaterial = new THREE.MeshStandardMaterial({ color, metalness: 0.42, roughness: 0.3 });
    const darkMaterial = new THREE.MeshStandardMaterial({ color: 0x101817, metalness: 0.65, roughness: 0.24 });
    const body = new THREE.Mesh(new THREE.BoxGeometry(1.05, 0.35, 0.72), bodyMaterial);
    body.castShadow = true;
    group.add(body);
    for (const angle of [Math.PI / 4, 3 * Math.PI / 4, 5 * Math.PI / 4, 7 * Math.PI / 4]) {
      const arm = new THREE.Mesh(new THREE.BoxGeometry(1.45, 0.08, 0.08), darkMaterial);
      arm.rotation.y = angle;
      group.add(arm);
      const rotor = new THREE.Mesh(new THREE.CylinderGeometry(0.34, 0.34, 0.025, 20), darkMaterial);
      rotor.position.set(Math.cos(angle) * 0.62, 0.13, -Math.sin(angle) * 0.62);
      rotor.userData.rotor = true;
      group.add(rotor);
    }
    group.scale.setScalar(0.72);
    return group;
  }

  createLabel(text, color) {
    const canvas = document.createElement("canvas");
    canvas.width = 512;
    canvas.height = 96;
    const context = canvas.getContext("2d");
    context.fillStyle = "rgba(5, 12, 11, 0.82)";
    context.roundRect(3, 3, 506, 90, 12);
    context.fill();
    context.strokeStyle = "rgba(170, 190, 182, 0.62)";
    context.stroke();
    context.fillStyle = color;
    context.font = "600 34px system-ui";
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.fillText(text, 256, 49, 480);
    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture, transparent: true, depthTest: false }));
    sprite.scale.set(5.8, 1.1, 1);
    return sprite;
  }

  loadMission(result) {
    for (const object of this.routeObjects) this.scene.remove(object);
    this.routeObjects = [];
    const snapshots = result.simulation.snapshots;
    const ids = [...new Set(snapshots.flatMap((snapshot) => snapshot.drones.map((drone) => drone.drone_id)))];
    for (const [index, droneId] of ids.entries()) {
      const points = [];
      for (const snapshot of snapshots) {
        const drone = snapshot.drones.find((item) => item.drone_id === droneId);
        if (!drone) continue;
        points.push(this.toWorld(drone.latitude, drone.longitude, Math.max(drone.altitude_m, 0.45)));
      }
      const geometry = new THREE.BufferGeometry().setFromPoints(points);
      const line = new THREE.Line(
        geometry,
        new THREE.LineBasicMaterial({ color: COLORS[index % COLORS.length], transparent: true, opacity: 0.82 }),
      );
      line.position.y += 0.03;
      this.scene.add(line);
      this.routeObjects.push(line);
    }
    this.updateTelemetry(result.simulation, 0);
  }

  updateTelemetry(simulation, time) {
    if (!simulation?.snapshots?.length) return [];
    const snapshots = simulation.snapshots;
    let upperIndex = snapshots.findIndex((snapshot) => snapshot.time_min >= time);
    if (upperIndex < 0) upperIndex = snapshots.length - 1;
    const lowerIndex = Math.max(0, upperIndex - 1);
    const lower = snapshots[lowerIndex];
    const upper = snapshots[upperIndex];
    const span = Math.max(upper.time_min - lower.time_min, 1e-9);
    const fraction = THREE.MathUtils.clamp((time - lower.time_min) / span, 0, 1);
    const rows = [];
    for (const upperDrone of upper.drones) {
      const lowerDrone = lower.drones.find((item) => item.drone_id === upperDrone.drone_id) || upperDrone;
      const latitude = THREE.MathUtils.lerp(lowerDrone.latitude, upperDrone.latitude, fraction);
      const longitude = THREE.MathUtils.lerp(lowerDrone.longitude, upperDrone.longitude, fraction);
      const altitude = THREE.MathUtils.lerp(lowerDrone.altitude_m, upperDrone.altitude_m, fraction);
      const mesh = this.droneMeshes.get(upperDrone.drone_id);
      if (mesh) {
        mesh.visible = true;
        mesh.position.copy(this.toWorld(latitude, longitude, Math.max(altitude, 0.45)));
        for (const child of mesh.children) if (child.userData.rotor) child.rotation.y += 0.35;
      }
      rows.push({ ...upperDrone, latitude, longitude, altitude_m: altitude });
    }
    this.activeDroneId = rows.find((row) => !["waiting", "completed"].includes(row.phase))?.drone_id || rows[0]?.drone_id;
    return rows;
  }

  setCameraMode(mode) { this.cameraMode = mode; }

  resetCamera() {
    this.camera.position.set(73, 68, 82);
    this.controls.target.set(0, 0, 0);
    this.controls.update();
  }

  resize() {
    const width = this.host.clientWidth;
    const height = this.host.clientHeight;
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height);
  }

  render() {
    if (this.cameraMode === "follow" && this.activeDroneId) {
      const drone = this.droneMeshes.get(this.activeDroneId);
      if (drone) {
        const desired = drone.position.clone().add(new THREE.Vector3(10, 8, 12));
        this.camera.position.lerp(desired, 0.035);
        this.controls.target.lerp(drone.position, 0.08);
      }
    }
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }
}

function setStage(name, status, detail) {
  const item = ui.stageList.querySelector(`[data-stage="${name}"]`);
  if (!item) return;
  item.classList.remove("complete", "active", "warning", "blocked");
  if (status) item.classList.add(status);
  item.querySelector("small").textContent = detail;
}

function resetStages() {
  for (const item of ui.stageList.querySelectorAll("li")) {
    item.className = "";
    item.querySelector("small").textContent = item.dataset.stage === "vision" ? "Awaiting imagery" : "Waiting";
  }
}

function pipelinePending() {
  resetStages();
  setStage("input", "active", "Processing command");
}

function pipelineClarification() {
  setStage("input", "complete", "Complete");
  setStage("intent", "complete", "Structured");
  setStage("grounding", "warning", "Clarification");
}

function pipelineReady() {
  for (const name of ["input", "intent", "grounding", "planning", "scheduling", "safety"]) {
    setStage(name, "complete", "Complete");
  }
  setStage("simulation", "active", "Running");
  setStage("vision", "warning", "Awaiting imagery");
}

async function runMission(resolutions = {}) {
  const command = ui.command.value.trim();
  if (!command) return showNotice("Enter a mission command.");
  ui.run.disabled = true;
  ui.clarification.hidden = true;
  state.resolutions = resolutions;
  pipelinePending();
  try {
    const response = await fetch("/api/mission", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command, grounding_resolutions: resolutions }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || result.error || "Mission request failed");
    state.result = result;
    if (result.status === "clarification_required") {
      pipelineClarification();
      renderClarification(result.clarifications[0]);
      state.playing = false;
      return;
    }
    if (result.status !== "simulation_ready") {
      setStage("simulation", "blocked", result.status.replaceAll("_", " "));
      showNotice(result.preparation?.issues?.join(", ") || "Mission pipeline blocked.");
      return;
    }
    pipelineReady();
    state.scene.loadMission(result);
    state.missionTime = 0;
    state.playing = true;
    ui.timeline.max = result.simulation.planned_makespan_min;
    ui.timeline.value = 0;
    renderPerception(result.preparation.perception_targets);
    updatePlaybackIcon();
  } catch (error) {
    setStage("input", "blocked", "Request failed");
    showNotice(error.message);
  } finally {
    ui.run.disabled = false;
  }
}

function renderClarification(clarification) {
  ui.clarification.hidden = false;
  ui.clarificationMessage.textContent = clarification.message;
  ui.clarificationOptions.replaceChildren();
  for (const option of clarification.options) {
    const button = document.createElement("button");
    button.type = "button";
    button.innerHTML = `<strong>${escapeHtml(option.name)}</strong><small>${escapeHtml(option.reference_field)}: ${escapeHtml(option.phrase || "not stated")}</small>`;
    button.addEventListener("click", () => runMission({ ...state.resolutions, [clarification.clause_id]: option.location_id }));
    ui.clarificationOptions.appendChild(button);
  }
  window.lucide?.createIcons();
}

function renderPerception(targets) {
  if (!targets?.length) {
    ui.perception.textContent = "No open target";
    return;
  }
  ui.perception.textContent = `${targets.map((target) => target.phrase).join(", ")} · awaiting vision`;
}

function renderDroneRows(rows) {
  const existing = new Map([...ui.droneList.children].map((node) => [node.dataset.droneId, node]));
  for (const [index, row] of rows.entries()) {
    let node = existing.get(row.drone_id);
    if (!node) {
      node = document.createElement("article");
      node.className = "drone-row";
      node.dataset.droneId = row.drone_id;
      node.innerHTML = `<header><strong></strong><span>SIMULATED</span></header><dl><dt>Phase</dt><dd data-field="phase"></dd><dt>Task</dt><dd data-field="task"></dd><dt>Altitude</dt><dd data-field="altitude"></dd></dl>`;
      ui.droneList.appendChild(node);
    }
    node.style.borderLeftColor = `#${COLORS[index % COLORS.length].toString(16).padStart(6, "0")}`;
    node.querySelector("header strong").textContent = row.drone_id;
    node.querySelector('[data-field="phase"]').textContent = row.phase.replaceAll("_", " ");
    node.querySelector('[data-field="task"]').textContent = row.task_id || "none";
    node.querySelector('[data-field="altitude"]').textContent = `${row.altitude_m.toFixed(1)} m`;
  }
}

function updateUI(rows) {
  const simulation = state.result?.simulation;
  if (!simulation) return;
  ui.missionClock.textContent = formatTime(state.missionTime);
  ui.timeline.value = state.missionTime;
  ui.timelineOutput.textContent = `${formatTime(state.missionTime)} / ${formatTime(simulation.planned_makespan_min)}`;
  ui.separation.textContent = `${simulation.minimum_observed_separation_m.toFixed(1)} m`;
  ui.safetyStatus.textContent = simulation.status === "completed" ? "Nominal" : simulation.status.replaceAll("_", " ");
  renderDroneRows(rows);
  if (state.missionTime >= simulation.planned_makespan_min) {
    state.playing = false;
    setStage("simulation", "complete", "Complete");
    updatePlaybackIcon();
  }
}

function animate(now) {
  const deltaSeconds = Math.min((now - state.lastFrame) / 1000, 0.1);
  state.lastFrame = now;
  const simulation = state.result?.simulation;
  if (state.playing && simulation) {
    state.missionTime = Math.min(
      state.missionTime + deltaSeconds * BASE_MINUTES_PER_SECOND * Number(ui.speed.value),
      simulation.planned_makespan_min,
    );
  }
  const rows = simulation ? state.scene.updateTelemetry(simulation, state.missionTime) : [];
  if (simulation) updateUI(rows);
  state.scene?.render();
  requestAnimationFrame(animate);
}

function updatePlaybackIcon() {
  ui.playPause.innerHTML = `<i data-lucide="${state.playing ? "pause" : "play"}"></i>`;
  window.lucide?.createIcons();
}

function formatTime(minutes) {
  const totalSeconds = Math.max(0, Math.round(minutes * 60));
  const mins = Math.floor(totalSeconds / 60).toString().padStart(2, "0");
  const secs = (totalSeconds % 60).toString().padStart(2, "0");
  return `${mins}:${secs}`;
}

function showNotice(message) {
  ui.notice.textContent = message;
  ui.notice.hidden = false;
  window.setTimeout(() => { ui.notice.hidden = true; }, 5000);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[character]));
}

async function initialize() {
  try {
    const response = await fetch("/api/config");
    if (!response.ok) throw new Error("Could not load simulator configuration");
    state.config = await response.json();
    state.scene = new MissionScene(ui.scene, state.config);
    ui.command.value = state.config.default_command;
    ui.connection.classList.add("connected");
    ui.connection.innerHTML = '<i data-lucide="circle"></i> Connected';
    ui.safetyStatus.textContent = "Standby";
    ui.loading.classList.add("hidden");
    window.lucide?.createIcons();
    requestAnimationFrame(animate);
  } catch (error) {
    ui.loading.querySelector("strong").textContent = error.message;
    ui.connection.textContent = "Offline";
  }
}

ui.run.addEventListener("click", () => runMission({}));
ui.command.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") runMission({});
});
ui.playPause.addEventListener("click", () => {
  if (!state.result?.simulation) return;
  state.playing = !state.playing;
  updatePlaybackIcon();
});
ui.restart.addEventListener("click", () => {
  state.missionTime = 0;
  state.playing = Boolean(state.result?.simulation);
  updatePlaybackIcon();
});
ui.timeline.addEventListener("input", () => {
  state.missionTime = Number(ui.timeline.value);
  state.playing = false;
  updatePlaybackIcon();
});
ui.cameraMode.addEventListener("change", () => state.scene?.setCameraMode(ui.cameraMode.value));
ui.resetCamera.addEventListener("click", () => state.scene?.resetCamera());

window.lucide?.createIcons();
initialize();
