extends Node3D

## Positions the driver and driven gears in the 3D scene based on the
## current center distance from the sim. The bridge sends center_distance
## in the sim-state extras; we listen and update the gear world positions.
##
## Convention: gears are placed along the X axis, with the driver at
## -center_distance/2 and the driven at +center_distance/2. Both sit at
## y=GEAR_HEIGHT (their spin axes align with world Z, so the discs face
## the camera).

@export var state_path: NodePath
@export var driver_path: NodePath
@export var driven_path: NodePath
const GEAR_HEIGHT: float = 1.0

var _state: Node
var _driver: Node3D
var _driven: Node3D
var _last_distance: float = 0.0

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
	# Apply initial distance from state if known.
	_apply_state_distance()

func _process(_delta: float) -> void:
	# Bridge may send center_distance without a gear change (e.g. on level
	# start). Poll the state to catch the first packet.
	var cd: float = float(_state.get("center_distance", 0.0))
	if cd > 0.0 and abs(cd - _last_distance) > 1e-4:
		_apply_distance(cd)

func _on_gears(_driver_t: int, _driven_t: int) -> void:
	_apply_state_distance()

func _apply_state_distance() -> void:
	var cd: float = float(_state.get("center_distance", 0.0))
	if cd > 0.0:
		_apply_distance(cd)

func _apply_distance(cd: float) -> void:
	_last_distance = cd
	# Visual scale: real sim units are pitch_r = 15 for N30 (so cd=30 for
	# 1:1). At scale 0.05 the N30 gear is 0.6 wide and the assembly is
	# 1.5 across — fits the camera's left-3D area (~3 units wide) for any
	# reasonable pair. Both position and mesh scale use the same factor
	# so meshing gears touch at the right place.
	const VISUAL_SCALE: float = 0.05
	var offset: float = cd * 0.5 * VISUAL_SCALE
	_driver.position = Vector3(-offset, GEAR_HEIGHT, 0)
	_driven.position = Vector3(+offset, GEAR_HEIGHT, 0)
	_driver.scale = Vector3.ONE * VISUAL_SCALE
	_driven.scale = Vector3.ONE * VISUAL_SCALE
