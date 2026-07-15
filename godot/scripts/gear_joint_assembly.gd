extends Node3D

## Positions the planetary gearbox of Act 2.3 (sun + planets + ring + carrier)
## in the 3D scene, and rotates the ROD pivot by the carrier's joint angle.
##
## This mirrors gear_planetary_assembly.gd (the 2.2 layout): sun at the origin,
## N planets equally spaced on a circle of radius (r_sun + r_planet), the ring
## enclosing them, and a carrier plate linking the planet shafts. Spin axis is
## world Z (flat discs facing the camera at y=GEAR_HEIGHT), matching 1.2–1.4
## and 2.2.
##
## The difference from 2.2: the CARRIER is the JOINT OUTPUT here — it carries
## the rod. The rod pivot (RodPivot) is a SIBLING at the origin with scale 1.0
## (NOT a child of the scaled carrier, which would shrink the world-unit rod
## mesh back to invisible). The assembly rotates RodPivot around Z by joint id
## 1's angle (the carrier angle = the rod angle), and the rod swings with it.
##
##       ring (annulus, r_ring) ── encloses ──
##         sun(center) + 3 planets(carrier circle)
##                            |
##                        RodPivot (origin, scale 1.0)
##                            |  (rotates by joint id 1)
##                           rod hangs down (-Y)

@export var state_path: NodePath
@export var sun_path: NodePath
@export var planet_path: NodePath  # one planet MeshInstance3D; cloned per planet
@export var ring_path: NodePath
@export var carrier_path: NodePath
@export var rod_pivot_path: NodePath  # Node3D at the origin; carries the Rod
@export var num_planets: int = 3

const GEAR_HEIGHT: float = 1.0
const VISUAL_SCALE: float = 0.03
const GEAR_MODULE: float = 1.0
const DEFAULT_TEETH_SUN: int = 12
const DEFAULT_TEETH_PLANET: int = 24
const DEFAULT_TEETH_RING: int = 60

var _state: Node
var _sun: Node3D
var _planet_template: Node3D
var _ring: Node3D
var _carrier: Node3D
var _rod_pivot: Node3D
var _planets: Array[Node3D] = []
var _last_sun: int = 0
var _last_planet: int = 0
var _last_ring: int = 0


func _ready() -> void:
	_state = get_node_or_null(state_path)
	_sun = get_node_or_null(sun_path) as Node3D
	_planet_template = get_node_or_null(planet_path) as Node3D
	_ring = get_node_or_null(ring_path) as Node3D
	_carrier = get_node_or_null(carrier_path) as Node3D
	_rod_pivot = get_node_or_null(rod_pivot_path) as Node3D
	if _state == null or _sun == null or _planet_template == null or _ring == null:
		push_error("GearJointAssembly: missing state or member nodes")
		return
	# Hide the template planet; we clone it for each planet.
	_planet_template.visible = false
	if _state.has_signal("planetary_gears_changed"):
		_state.connect("planetary_gears_changed", _on_gears)
	if _state.has_signal("joint_changed"):
		_state.connect("joint_changed", _on_joint)
	# Rod pivot at the origin, scale 1.0 (rod mesh is in world units).
	if _rod_pivot != null:
		_rod_pivot.position = Vector3(0.0, GEAR_HEIGHT, 0.0)
		_rod_pivot.scale = Vector3.ONE
	_apply_layout_from_state()


func _process(_delta: float) -> void:
	# Bridge may send tooth counts without firing the signal on level start.
	var s_t: int = int(_state.get("teeth_sun")) if _state.get("teeth_sun") != null else 0
	var p_t: int = int(_state.get("teeth_planet")) if _state.get("teeth_planet") != null else 0
	var r_t: int = int(_state.get("teeth_ring")) if _state.get("teeth_ring") != null else 0
	if s_t > 0 and p_t > 0 and r_t > 0:
		if s_t != _last_sun or p_t != _last_planet or r_t != _last_ring:
			_apply_layout(s_t, p_t, r_t)
	# Rotate the rod pivot by the carrier joint angle (id 1) every frame.
	_update_rod_angle()


func _on_gears(teeth_sun: int, teeth_planet: int, teeth_ring: int) -> void:
	_apply_layout(teeth_sun, teeth_planet, teeth_ring)


func _on_joint(jid: int, _rpm: float, _angle: float) -> void:
	if jid == 1:
		_update_rod_angle()


func _apply_layout_from_state() -> void:
	var s_t: int = int(_state.get("teeth_sun")) if _state.get("teeth_sun") != null else 0
	var p_t: int = int(_state.get("teeth_planet")) if _state.get("teeth_planet") != null else 0
	var r_t: int = int(_state.get("teeth_ring")) if _state.get("teeth_ring") != null else 0
	if s_t <= 0 or p_t <= 0 or r_t <= 0:
		s_t = DEFAULT_TEETH_SUN
		p_t = DEFAULT_TEETH_PLANET
		r_t = DEFAULT_TEETH_RING
	_apply_layout(s_t, p_t, r_t)


func _apply_layout(teeth_sun: int, teeth_planet: int, teeth_ring: int) -> void:
	_last_sun = teeth_sun
	_last_planet = teeth_planet
	_last_ring = teeth_ring
	var r_sun: float = GEAR_MODULE * teeth_sun * 0.5
	var r_planet: float = GEAR_MODULE * teeth_planet * 0.5
	var r_ring: float = GEAR_MODULE * teeth_ring * 0.5
	var planet_orbit: float = (r_sun + r_planet) * VISUAL_SCALE

	_sun.position = Vector3(0.0, GEAR_HEIGHT, 0.0)
	_sun.scale = Vector3.ONE * (r_sun * VISUAL_SCALE)

	_ring.position = Vector3(0.0, GEAR_HEIGHT, 0.0)
	_ring.scale = Vector3.ONE * (r_ring * VISUAL_SCALE)

	if _carrier != null:
		_carrier.position = Vector3(0.0, GEAR_HEIGHT, 0.0)
		_carrier.scale = Vector3.ONE * (planet_orbit)

	_clear_planets()
	for i in num_planets:
		var ang: float = TAU * float(i) / float(num_planets)
		var px: float = cos(ang)
		var py: float = sin(ang)
		var p: Node3D = _planet_template.duplicate() as Node3D
		p.visible = true
		p.position = Vector3(px, py, 0.0)
		p.scale = Vector3.ONE * (r_planet * VISUAL_SCALE / planet_orbit)
		if _carrier != null:
			_carrier.add_child(p)
		else:
			add_child(p)
		p.owner = owner
		_planets.append(p)


func _clear_planets() -> void:
	for p in _planets:
		if is_instance_valid(p):
			p.queue_free()
	_planets.clear()


func _update_rod_angle() -> void:
	if _rod_pivot == null or _state == null:
		return
	var joints = _state.get("joints")
	if joints == null:
		return
	var j = joints.get("1")
	if j == null:
		return
	var ang: float = float(j.get("angle", 0.0))
	# Rotate the pivot around world Z by the carrier (rod) angle. Scale is 1.0
	# (set in _ready), so compose rotation onto Basis.from_scale to preserve it.
	var live_scale: Vector3 = _rod_pivot.transform.basis.get_scale()
	var spin: Quaternion = Quaternion(Vector3.BACK, ang)
	var basis: Basis = Basis(spin) * Basis.from_scale(live_scale)
	_rod_pivot.transform = Transform3D(basis, _rod_pivot.position)
