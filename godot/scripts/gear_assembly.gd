extends Node3D

## Positions the driver and driven gears in the 3D scene based on the
## current tooth counts and center distance from the sim. The bridge
## sends both in the sim-state extras; we listen and update the gear
## world positions and scales.
##
## Convention: gears are placed along the X axis. For two meshing
## gears with pitch radii r1, r2 and center distance cd = r1 + r2, the
## driver sits at -r2 and the driven sits at +r1 in pitch-radius
## units, so their pitch circles touch. Each gear's MeshInstance3D is
## scaled by its own pitch radius (mesh is built normalized), so the
## silhouette size matches the sim. Both sit at y=GEAR_HEIGHT with
## their spin axes along world Z, so the discs face the camera.
##
## VISUAL_SCALE converts sim units (module = 1.0, so N30 → pitch_r=15)
## to world units. A 60-tooth gear at scale 0.03 has world radius 0.9,
## keeping the largest catalog pair inside the viewport.

@export var state_path: NodePath
@export var driver_path: NodePath
@export var driven_path: NodePath
const GEAR_HEIGHT: float = 1.0
const VISUAL_SCALE: float = 0.03
const GEAR_MODULE: float = 1.0
const DEFAULT_TEETH: int = 30

var _state: Node
var _driver: Node3D
var _driven: Node3D
var _last_distance: float = 0.0
var _last_driver_t: int = 0
var _last_driven_t: int = 0

func _ready() -> void:
	_state = get_node_or_null(state_path)
	_driver = get_node_or_null(driver_path) as Node3D
	_driven = get_node_or_null(driven_path) as Node3D
	if _state == null or _driver == null or _driven == null:
		push_error("GearAssembly: missing state or gear nodes")
		return
	if not _state.has_signal("gear_teeth_changed"):
		push_error("GearAssembly: state missing gear_teeth_changed signal")
		return
	_state.connect("gear_teeth_changed", _on_gears)
	# Apply initial layout from state if known.
	_apply_state_layout()

func _process(_delta: float) -> void:
	# Bridge may send tooth counts or center_distance without firing the
	# signal (e.g. on level start). Poll the state to catch the first
	# packet.
	var raw = _state.get("center_distance")
	var cd: float = float(raw) if raw != null else 0.0
	if cd > 0.0 and (cd != _last_distance
			or _last_driver_t <= 0 or _last_driven_t <= 0):
		_apply_state_layout()

func _on_gears(_driver_t: int, _driven_t: int) -> void:
	_apply_state_layout()

func _apply_state_layout() -> void:
	# Object.get() has no default-value argument; coerce a null to 0.
	var d_raw = _state.get("driver_teeth")
	var n_raw = _state.get("driven_teeth")
	var driver_t: int = int(d_raw) if d_raw != null else 0
	var driven_t: int = int(n_raw) if n_raw != null else 0
	if driver_t <= 0 or driven_t <= 0:
		driver_t = DEFAULT_TEETH
		driven_t = DEFAULT_TEETH
	if driver_t == _last_driver_t and driven_t == _last_driven_t:
		# Tooth counts unchanged — leave mesh scale alone.
		# But still update position if center_distance changed.
		var cd_raw = _state.get("center_distance")
		var cd: float = float(cd_raw) if cd_raw != null else 0.0
		if cd > 0.0 and abs(cd - _last_distance) > 1e-4:
			_apply_layout(driver_t, driven_t, cd)
		return
	_last_driver_t = driver_t
	_last_driven_t = driven_t
	# Center distance (sim units): r1 + r2 where r = module * teeth / 2.
	var center_distance: float = GEAR_MODULE * (driver_t + driven_t) * 0.5
	_apply_layout(driver_t, driven_t, center_distance)

func _apply_layout(driver_t: int, driven_t: int, cd: float) -> void:
	_last_distance = cd
	# Pitch radii in sim units.
	var r_driver: float = GEAR_MODULE * driver_t * 0.5
	var r_driven: float = GEAR_MODULE * driven_t * 0.5
	# Position so pitch circles touch along the X axis.
	var driver_x: float = -r_driven * VISUAL_SCALE
	var driven_x: float = +r_driver * VISUAL_SCALE
	# Scale: mesh is normalized to pitch_r = 1, so we scale to its real
	# pitch radius in world units.
	var driver_scale: float = r_driver * VISUAL_SCALE
	var driven_scale: float = r_driven * VISUAL_SCALE
	_driver.position = Vector3(driver_x, GEAR_HEIGHT, 0)
	_driven.position = Vector3(driven_x, GEAR_HEIGHT, 0)
	_driver.scale = Vector3.ONE * driver_scale
	_driven.scale = Vector3.ONE * driven_scale
