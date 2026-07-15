extends Node3D

## Positions the four gears of a 2-stage compound gearbox (Act 2.1) in the 3D
## scene based on the current tooth counts from the sim.
##
## Gears are flat discs whose normal is +X — they face SIDEWAYS, like wheels
## on an axle (this is the 1.1 motor-shaft orientation). The spin axis is
## world X. This matters because B and C share the INTERMEDIATE SHAFT, which
## runs along X: with the axle perpendicular to the camera, B and C separate
## SIDE-BY-SIDE on screen instead of stacking in depth (where C hid behind B).
##
## Top-down (X right, Z toward camera):
##
##       z<----(mesh)----          (mesh)---->z
##            A   B   ===shared shaft===   C   D
##                       (runs along X)
##
## - A meshes with B: coplanar (same x), pitch circles touch along Z.
## - B and C share the intermediate shaft (runs along X): same z, B at x_low,
##   C at x_high. They separate horizontally so both are visible.
## - C meshes with D: coplanar (same x), pitch circles touch along Z.
##
## Each gear's MeshInstance3D is scaled by its own pitch radius (mesh is built
## normalized), so the silhouette size matches the sim. All sit at y=GEAR_HEIGHT.

@export var state_path: NodePath
@export var gear_a_path: NodePath
@export var gear_b_path: NodePath
@export var gear_c_path: NodePath
@export var gear_d_path: NodePath
const GEAR_HEIGHT: float = 1.0
const VISUAL_SCALE: float = 0.03
const GEAR_MODULE: float = 1.0
const DEFAULT_TEETH: int = 30
# How far apart B and C sit along the shared intermediate shaft (world X).
# The shaft runs perpendicular to the camera, so this gap spreads B and C
# horizontally on screen — both stay visible.
const SHAFT_GAP: float = 0.8

var _state: Node
var _a: Node3D
var _b: Node3D
var _c: Node3D
var _d: Node3D
var _last_a: int = 0
var _last_b: int = 0
var _last_c: int = 0
var _last_d: int = 0

func _ready() -> void:
	_state = get_node_or_null(state_path)
	_a = get_node_or_null(gear_a_path) as Node3D
	_b = get_node_or_null(gear_b_path) as Node3D
	_c = get_node_or_null(gear_c_path) as Node3D
	_d = get_node_or_null(gear_d_path) as Node3D
	if _state == null or _a == null or _b == null or _c == null or _d == null:
		push_error("GearCompoundAssembly: missing state or gear nodes")
		return
	if _state.has_signal("compound_gears_changed"):
		_state.connect("compound_gears_changed", _on_gears)
	_apply_layout_from_state()

func _process(_delta: float) -> void:
	# Bridge may send tooth counts without firing the signal on level start.
	# Poll the state to catch the first packet.
	var a_t: int = int(_state.get("teeth_a")) if _state.get("teeth_a") != null else 0
	var b_t: int = int(_state.get("teeth_b")) if _state.get("teeth_b") != null else 0
	var c_t: int = int(_state.get("teeth_c")) if _state.get("teeth_c") != null else 0
	var d_t: int = int(_state.get("teeth_d")) if _state.get("teeth_d") != null else 0
	if a_t > 0 and b_t > 0 and c_t > 0 and d_t > 0:
		if a_t != _last_a or b_t != _last_b or c_t != _last_c or d_t != _last_d:
			_apply_layout(a_t, b_t, c_t, d_t)

func _on_gears(a_t: int, b_t: int, c_t: int, d_t: int) -> void:
	_apply_layout(a_t, b_t, c_t, d_t)

func _apply_layout_from_state() -> void:
	var a_t: int = int(_state.get("teeth_a")) if _state.get("teeth_a") != null else 0
	var b_t: int = int(_state.get("teeth_b")) if _state.get("teeth_b") != null else 0
	var c_t: int = int(_state.get("teeth_c")) if _state.get("teeth_c") != null else 0
	var d_t: int = int(_state.get("teeth_d")) if _state.get("teeth_d") != null else 0
	if a_t <= 0 or b_t <= 0 or c_t <= 0 or d_t <= 0:
		a_t = DEFAULT_TEETH
		b_t = DEFAULT_TEETH
		c_t = DEFAULT_TEETH
		d_t = DEFAULT_TEETH
	_apply_layout(a_t, b_t, c_t, d_t)

func _apply_layout(a_t: int, b_t: int, c_t: int, d_t: int) -> void:
	_last_a = a_t
	_last_b = b_t
	_last_c = c_t
	_last_d = d_t
	var r_a: float = GEAR_MODULE * a_t * 0.5
	var r_b: float = GEAR_MODULE * b_t * 0.5
	var r_c: float = GEAR_MODULE * c_t * 0.5
	var r_d: float = GEAR_MODULE * d_t * 0.5
	# Spin axis = X. The shared INTERMEDIATE SHAFT runs along X, so B and C
	# separate ALONG X (the shaft) — both visible side-by-side. Meshing pairs
	# (A-B, C-D) separate along Z (the line of centers); each pair is coplanar
	# in X so their pitch circles touch.
	var cd_ab: float = (r_a + r_b) * VISUAL_SCALE  # A-B center distance (along Z)
	var cd_cd: float = (r_c + r_d) * VISUAL_SCALE  # C-D center distance (along Z)
	# B sits on the shared shaft at the left; C at the right.
	var x_b: float = 0.0
	var x_c: float = x_b + SHAFT_GAP
	# A meshes with B: coplanar with B (same x), offset in Z by -cd_ab so the
	# pitch circles touch. C meshes with D: coplanar with C, offset +cd_cd.
	var x_a: float = x_b
	var x_d: float = x_c
	var z_b: float = 0.0
	var z_c: float = 0.0
	var z_a: float = z_b - cd_ab
	var z_d: float = z_c + cd_cd
	# Center the cluster at the world origin so it stays framed regardless of
	# the chosen tooth counts (the HUD reads positions relative to this).
	var cx: float = (x_a + x_b + x_c + x_d) * 0.25
	var cz: float = (z_a + z_b + z_c + z_d) * 0.25
	_a.position = Vector3(x_a - cx, GEAR_HEIGHT, z_a - cz)
	_b.position = Vector3(x_b - cx, GEAR_HEIGHT, z_b - cz)
	_c.position = Vector3(x_c - cx, GEAR_HEIGHT, z_c - cz)
	_d.position = Vector3(x_d - cx, GEAR_HEIGHT, z_d - cz)
	_a.scale = Vector3.ONE * (r_a * VISUAL_SCALE)
	_b.scale = Vector3.ONE * (r_b * VISUAL_SCALE)
	_c.scale = Vector3.ONE * (r_c * VISUAL_SCALE)
	_d.scale = Vector3.ONE * (r_d * VISUAL_SCALE)
