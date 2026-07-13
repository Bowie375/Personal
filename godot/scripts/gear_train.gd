extends Node3D

## Positions three gears (driver, idler, driven) in the 3D scene based on
## the current tooth counts and center distances from the sim. The bridge
## sends tooth counts in the sim-state extras; we listen and update the
## gear world positions and scales.
##
## Convention: gears are placed along the X axis. The idler sits at x=0
## (center of the train). The driver sits at -(r_driver + r_idler)*scale,
## and the driven sits at +(r_idler + r_driven)*scale, so that all three
## pitch circles touch at their boundaries. Each gear's MeshInstance3D is
## scaled by its own pitch radius (mesh is built normalized), so the
## silhouette size matches the sim.
##
## VISUAL_SCALE converts sim units (module = 1.0) to world units.
## All three sit at y=GEAR_HEIGHT with spin axes along world Z.

@export var state_path: NodePath
@export var driver_path: NodePath
@export var idler_path: NodePath
@export var driven_path: NodePath
const GEAR_HEIGHT: float = 1.0
const VISUAL_SCALE: float = 0.03
const GEAR_MODULE: float = 1.0
const DEFAULT_TEETH: int = 30

var _state: Node
var _driver: Node3D
var _idler: Node3D
var _driven: Node3D
var _last_driver_t: int = 0
var _last_idler_t: int = 0
var _last_driven_t: int = 0

func _ready() -> void:
	_state = get_node_or_null(state_path)
	_driver = get_node_or_null(driver_path) as Node3D
	_idler = get_node_or_null(idler_path) as Node3D
	_driven = get_node_or_null(driven_path) as Node3D
	if _state == null or _driver == null or _idler == null or _driven == null:
		push_error("GearTrain: missing state or gear nodes")
		return
	if not _state.has_signal("gear_train_changed"):
		push_error("GearTrain: state missing gear_train_changed signal")
		return
	_state.connect("gear_train_changed", _on_gears)
	# Apply initial layout from state if known.
	_apply_state_layout()

func _process(_delta: float) -> void:
	# Bridge may send tooth counts without firing the signal (e.g. on level
	# start). Poll the state to catch the first packet.
	var d_raw = _state.get("driver_teeth")
	var i_raw = _state.get("idler_teeth")
	var n_raw = _state.get("driven_teeth")
	var driver_t: int = int(d_raw) if d_raw != null else 0
	var idler_t: int = int(i_raw) if i_raw != null else 0
	var driven_t: int = int(n_raw) if n_raw != null else 0
	if (driver_t > 0 and idler_t > 0 and driven_t > 0
			and (driver_t != _last_driver_t or idler_t != _last_idler_t or driven_t != _last_driven_t)):
		_apply_layout(driver_t, idler_t, driven_t)

func _on_gears(_driver_t: int, _idler_t: int, _driven_t: int) -> void:
	_apply_state_layout()

func _apply_state_layout() -> void:
	# Read tooth counts from state.
	var d_raw = _state.get("driver_teeth")
	var i_raw = _state.get("idler_teeth")
	var n_raw = _state.get("driven_teeth")
	var driver_t: int = int(d_raw) if d_raw != null else 0
	var idler_t: int = int(i_raw) if i_raw != null else 0
	var driven_t: int = int(n_raw) if n_raw != null else 0
	if driver_t <= 0 or idler_t <= 0 or driven_t <= 0:
		driver_t = DEFAULT_TEETH
		idler_t = DEFAULT_TEETH
		driven_t = DEFAULT_TEETH
	_apply_layout(driver_t, idler_t, driven_t)

func _apply_layout(driver_t: int, idler_t: int, driven_t: int) -> void:
	_last_driver_t = driver_t
	_last_idler_t = idler_t
	_last_driven_t = driven_t
	# Pitch radii in sim units.
	var r_driver: float = GEAR_MODULE * driver_t * 0.5
	var r_idler: float = GEAR_MODULE * idler_t * 0.5
	var r_driven: float = GEAR_MODULE * driven_t * 0.5
	# Position so pitch circles touch along the X axis.
	# Idler at center (x=0), driver at -(r_driver + r_idler)*scale,
	# driven at +(r_idler + r_driven)*scale.
	var driver_x: float = -(r_driver + r_idler) * VISUAL_SCALE
	var idler_x: float = 0.0
	var driven_x: float = +(r_idler + r_driven) * VISUAL_SCALE
	# Scale: mesh is normalized to pitch_r = 1, so we scale to its real
	# pitch radius in world units.
	var driver_scale: float = r_driver * VISUAL_SCALE
	var idler_scale: float = r_idler * VISUAL_SCALE
	var driven_scale: float = r_driven * VISUAL_SCALE
	_driver.position = Vector3(driver_x, GEAR_HEIGHT, 0)
	_idler.position = Vector3(idler_x, GEAR_HEIGHT, 0)
	_driven.position = Vector3(driven_x, GEAR_HEIGHT, 0)
	_driver.scale = Vector3.ONE * driver_scale
	_idler.scale = Vector3.ONE * idler_scale
	_driven.scale = Vector3.ONE * driven_scale
