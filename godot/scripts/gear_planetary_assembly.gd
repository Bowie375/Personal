extends Node3D

## Positions the members of a planetary gearset (Act 2.2) in the 3D scene
## based on the current tooth counts from the sim: a central sun, N planets
## equally spaced on a circle, an outer ring, and a carrier plate linking the
## planet shafts.
##
## Spin axis is world Z (the 1.2–1.4 gear orientation): the gears are flat
## discs whose normal is +Z, face-on to a camera looking down -Z. The whole
## planetary is co-axial along Z, so all members share the Z axis and separate
## in the XY plane (the carrier plane). No overlapping gears (unlike 2.1's
## shared intermediate shaft), so the 1.2-style face-on framing reads cleanly.
##
## Layout (looking along -Z, the carrier plane is XY):
##
##            ring (annulus, radius r_ring)
##         /              \
##        /   planet \      planet   ...
##       |     o        o        o     |
##        \   r_p + r_s  (carrier circle)/
##         \              /
##            sun (center, radius r_sun)
##
## - Sun at the origin of the carrier plane (x=0, y=0 on the axle at z=0).
## - Planets on a circle of radius (r_sun + r_planet) — their pitch circles
##   tangent to the sun AND tangent internally to the ring (r_ring = r_sun +
##   2*r_planet by the planetary constraint, so a planet also sits at
##   r_ring - r_planet from center — the same circle). Equally spaced at
##   2*pi/num_planets.
## - Ring centered at the origin, radius r_ring (drawn as a large gear / annulus).
## - Carrier: a disc of radius (r_sun + r_planet) linking the planet shafts
##   (visual only; it spins at the carrier rate in ring/sun-fixed modes).
##
## Each MeshInstance3D is scaled by its own pitch radius (meshes are built
## normalized), so the silhouette matches the sim. All sit at y=GEAR_HEIGHT.
## The cluster is centered at the world origin.

@export var state_path: NodePath
@export var sun_path: NodePath
@export var planet_path: NodePath  # one planet MeshInstance3D; cloned per planet
@export var ring_path: NodePath
@export var carrier_path: NodePath
@export var num_planets: int = 3

const GEAR_HEIGHT: float = 1.0
const VISUAL_SCALE: float = 0.03
const GEAR_MODULE: float = 1.0
const DEFAULT_TEETH_SUN: int = 24
const DEFAULT_TEETH_PLANET: int = 12
const DEFAULT_TEETH_RING: int = 48

var _state: Node
var _sun: Node3D
var _planet_template: Node3D
var _ring: Node3D
var _carrier: Node3D
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
	if _state == null or _sun == null or _planet_template == null or _ring == null:
		push_error("GearPlanetaryAssembly: missing state or member nodes")
		return
	# Hide the template planet; we'll clone it for each planet.
	_planet_template.visible = false
	if _state.has_signal("planetary_gears_changed"):
		_state.connect("planetary_gears_changed", _on_gears)
	_apply_layout_from_state()

func _process(_delta: float) -> void:
	# Bridge may send tooth counts without firing the signal on level start.
	# Poll the state to catch the first packet.
	var s_t: int = int(_state.get("teeth_sun")) if _state.get("teeth_sun") != null else 0
	var p_t: int = int(_state.get("teeth_planet")) if _state.get("teeth_planet") != null else 0
	var r_t: int = int(_state.get("teeth_ring")) if _state.get("teeth_ring") != null else 0
	if s_t > 0 and p_t > 0 and r_t > 0:
		if s_t != _last_sun or p_t != _last_planet or r_t != _last_ring:
			_apply_layout(s_t, p_t, r_t)
	# Drive the carrier's rotation (the planets orbit with it). The carrier
	# angle is joint 1 (LevelState.joints["1"]). Planets self-spin via their
	# own gear_visual (joint 3); here we only orbit them by rotating the
	# carrier node they're parented under.
	_orbit_carrier()

func _orbit_carrier() -> void:
	if _carrier == null or _state == null:
		return
	var j = _state.get("joints")
	if j == null:
		return
	var cj = j.get("1")
	if cj == null:
		return
	var ang: float = float(cj.get("angle", 0.0))
	# Carrier spins around the axle (world Z). Parenting the planets to the
	# carrier makes them orbit at the carrier rate (they stay in the XY plane,
	# perpendicular to the axle); their self-spin is added by gear_visual
	# (joint 3) on top. Preserve the carrier's scale (set in _apply_layout to
	# planet_orbit) — overwriting transform.basis alone would discard it, so
	# compose rotation onto a Basis.from_scale(live_scale). The disc mesh is
	# laid flat (normal along +Z) by a static child rotation baked in the scene,
	# so the carrier's own basis is just spin * scale (no reorientation — that
	# would drag the planets out of the XY plane).
	var live_scale: Vector3 = _carrier.transform.basis.get_scale()
	var spin: Quaternion = Quaternion(Vector3.BACK, ang)
	var basis: Basis = Basis(spin) * Basis.from_scale(live_scale)
	_carrier.transform = Transform3D(basis, _carrier.position)

func _on_gears(teeth_sun: int, teeth_planet: int, teeth_ring: int) -> void:
	_apply_layout(teeth_sun, teeth_planet, teeth_ring)

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
	# Planet center radius from the sun center: (r_sun + r_planet). For a valid
	# planetary this also equals (r_ring - r_planet) — the planet meshes with
	# both the sun (externally) and the ring (internally).
	var planet_orbit: float = (r_sun + r_planet) * VISUAL_SCALE

	# Sun at the origin of the carrier plane.
	_sun.position = Vector3(0.0, GEAR_HEIGHT, 0.0)
	_sun.scale = Vector3.ONE * (r_sun * VISUAL_SCALE)

	# Ring centered at the origin, large.
	_ring.position = Vector3(0.0, GEAR_HEIGHT, 0.0)
	_ring.scale = Vector3.ONE * (r_ring * VISUAL_SCALE)

	# Carrier: a disc spanning to the planet orbit radius. Planets are
	# parented to the carrier so they ORBIT when the carrier rotates; their
	# self-spin is added by gear_visual (joint 3) on top of the orbit.
	if _carrier != null:
		_carrier.position = Vector3(0.0, GEAR_HEIGHT, 0.0)
		_carrier.scale = Vector3.ONE * (planet_orbit)

	# Rebuild the planet clones to match num_planets, equally spaced. Parent
	# each to the carrier so it orbits with it.
	_clear_planets()
	for i in num_planets:
		var ang: float = TAU * float(i) / float(num_planets)
		# Place in the XY plane (the carrier plane); z stays 0 (all on the
		# axle). Positions are in the CARRIER's local frame (before its scale),
		# so the unit-circle coords land on the orbit circle after the carrier
		# is scaled by planet_orbit.
		var px: float = cos(ang)
		var py: float = sin(ang)
		var p: Node3D = _planet_template.duplicate() as Node3D
		p.visible = true
		# Local position relative to the (unscaled) carrier; the carrier's
		# scale places it on the orbit circle.
		p.position = Vector3(px, py, 0.0)
		p.scale = Vector3.ONE * (r_planet * VISUAL_SCALE / planet_orbit)
		# Inherit spin_axis / gear_role (5=planet, joint 3) from the template.
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
