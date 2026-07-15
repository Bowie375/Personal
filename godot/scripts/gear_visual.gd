extends MeshInstance3D

## Rotates a gear mesh from a specific joint id in LevelState.
##
## Listens for joint angle updates and applies a Y→spin_axis alignment
## so the gear disc spins in place around the chosen axis. Also listens
## for gear_teeth_changed so the mesh can be rebuilt to match the new
## tooth count (gear size and tooth count must agree visually).
##
## A Godot CylinderMesh has its geometry axis along +Y. To spin the gear
## in place around an arbitrary world axis, we reorient the mesh once
## (Y → spin_axis) and then apply the spin on top.

@export var state_path: NodePath
@export var joint_id: int = 0
@export var spin_axis: Vector3 = Vector3(0, 0, 1)
@export var gear_color: Color = Color(0.7, 0.65, 0.45, 1.0)
# Act 2.1 compound: which physical gear is this? 0=A, 1=B, 2=C, 3=D.
# B and C share a shaft (joint_id 1) but have DIFFERENT tooth counts; this
# role tells _on_compound_gears which count to draw. -1 = not a compound gear
# (use the 1.2/1.3 path keyed on joint_id).
# Act 2.2 planetary roles: 4=sun, 5=planet, 6=ring. Each also overrides the
# joint it spins with (sun=jt0, carrier=jt1, ring=jt2, planet self-spin=jt3),
# because the planetary members are co-axial and a planet both orbits and
# spins — its self-rotation is joint 3, set per-planet by the assembly.
@export var gear_role: int = -1

const GEAR_MODULE := 1.0
const GEAR_THICKNESS := 0.4
# The visible gear is drawn at this fraction of the pitch radius.
# A value < 1.0 keeps adjacent meshing gears from visually overlapping
# (since the real addendum would make outer radii sum to > center
# distance). 0.8 leaves a small visible gap between meshing gears.
const VISUAL_TIP_FACTOR := 0.8
# Mesh is built in *normalized* units: pitch radius = 1.0. The
# GearAssembly applies the real-world scale (pitch_r * VISUAL_SCALE) so
# the gear fits the 3D viewport regardless of tooth count.
const MESH_PITCH_RADIUS := 1.0
# Resolution of the ring gear's smooth annulus cap and outer rim (independent
# of tooth count, so a 6-tooth ring still has a round silhouette).
const RING_CAP_SEGMENTS := 64

var _state: Node
var _angle: float = 0.0
# Orientation baked at _ready: the Y→spin_axis reorientation. We keep
# this as a Quaternion so the spin composes rotation WITHOUT clobbering
# the Node3D scale that GearAssembly/GearTrain sets (scale = pitch_r *
# VISUAL_SCALE, which depends on tooth count). Overwriting transform.basis
# would discard that scale and freeze the gear at its initial radius.
var _orient: Quaternion
var _teeth: int = 0

func _ready() -> void:
	# Reorient the mesh's geometry axis (+Y) onto the requested spin_axis,
	# but do NOT bake the current scale in — the assembly owns scale.
	_orient = _compute_axis_quaternion(spin_axis)
	# Preserve the scene's initial scale (set by the assembly / .tscn).
	# (Godot 4: a Quaternion converts to a Basis via the Basis(q) ctor,
	# not a get_basis() method.)
	var s: Vector3 = transform.basis.get_scale()
	transform = Transform3D(Basis(_orient) * Basis.from_scale(s), transform.origin)
	_state = get_node_or_null(state_path)
	if _state == null:
		return
	if _state.has_signal("joint_changed"):
		_state.connect("joint_changed", _on_joint)
	if _state.has_signal("gear_teeth_changed"):
		_state.connect("gear_teeth_changed", _on_gears)
	# 1.3: listen to 3-gear signal for correct idler tooth count.
	if _state.has_signal("gear_train_changed"):
		_state.connect("gear_train_changed", _on_gears_train)
	# 2.1: listen to 4-gear signal so B and C each draw their own teeth.
	if _state.has_signal("compound_gears_changed"):
		_state.connect("compound_gears_changed", _on_compound_gears)
	# 2.2: listen to planetary signal so sun/planet/ring each draw their teeth.
	if _state.has_signal("planetary_gears_changed"):
		_state.connect("planetary_gears_changed", _on_planetary_gears)
	# If the state already has a tooth count, build the mesh now.
	_initial_teeth_from_state()

func _initial_teeth_from_state() -> void:
	# Pick the tooth count for THIS gear. 2.1's compound uses gear_role to
	# disambiguate B vs C (both on joint 1). 2.2's planetary uses gear_role
	# 4/5/6 for sun/planet/ring. 1.2/1.3 key off joint_id.
	var t: int = 0
	if gear_role >= 0 and gear_role <= 3:
		# Compound (2.1): read the 4 gear tooth counts directly.
		var a_raw = _state.get("teeth_a")
		var b_raw = _state.get("teeth_b")
		var c_raw = _state.get("teeth_c")
		var d_raw = _state.get("teeth_d")
		var a_t: int = int(a_raw) if a_raw != null else 0
		var b_t: int = int(b_raw) if b_raw != null else 0
		var c_t: int = int(c_raw) if c_raw != null else 0
		var d_t: int = int(d_raw) if d_raw != null else 0
		match gear_role:
			0:
				t = a_t
			1:
				t = b_t
			2:
				t = c_t
			3:
				t = d_t
			_:
				t = 0
	elif gear_role >= 4 and gear_role <= 6:
		# Planetary (2.2): read sun/planet/ring tooth counts.
		var sun_raw = _state.get("teeth_sun")
		var planet_raw = _state.get("teeth_planet")
		var ring_raw = _state.get("teeth_ring")
		var sun_t: int = int(sun_raw) if sun_raw != null else 0
		var planet_t: int = int(planet_raw) if planet_raw != null else 0
		var ring_t: int = int(ring_raw) if ring_raw != null else 0
		match gear_role:
			4:
				t = sun_t
			5:
				t = planet_t
			6:
				t = ring_t
			_:
				t = 0
	else:
		# 1.2/1.3: joint_id 0=driver, 1=idler (1.3) or driven (1.2), 2=driven.
		var driver_t_raw = _state.get("driver_teeth")
		var idler_t_raw = _state.get("idler_teeth")
		var driven_t_raw = _state.get("driven_teeth")
		var driver_t: int = int(driver_t_raw) if driver_t_raw != null else 0
		var idler_t: int = int(idler_t_raw) if idler_t_raw != null else 0
		var driven_t: int = int(driven_t_raw) if driven_t_raw != null else 0
		if joint_id == 0:
			t = driver_t
		elif joint_id == 1:
			t = idler_t if idler_t > 0 else driven_t  # idler; fall back for 1.2
		else:
			t = driven_t
	if t <= 0:
		t = 30  # safe default if bridge hasn't sent state yet
	_teeth = t
	_rebuild_mesh()

func _on_joint(jid: int, _rpm: float, angle: float) -> void:
	if jid == joint_id:
		_angle = angle
		# Apply the spin as a Quaternion composed onto the baked orientation.
		# Because we keep the Node3D's scale separate (read live from the
		# current basis), the gear's radius — which the assembly scales by
		# pitch_r * VISUAL_SCALE — survives the spin. Spinning around the
		# mesh-local +Y normal keeps the disc spinning in place; the
		# baked _orient reorients that onto the requested world axis.
		var live_scale: Vector3 = transform.basis.get_scale()
		var spin: Quaternion = Quaternion(Vector3.UP, _angle)
		var final_basis: Basis = Basis(_orient * spin) * Basis.from_scale(live_scale)
		transform = Transform3D(final_basis, transform.origin)

func _on_gears(driver_t: int, driven_t: int) -> void:
	# 1.2 (2-gear) callback: joint_id 0=driver, 1=driven.
	var t: int = driver_t if joint_id == 0 else driven_t
	if t > 0 and t != _teeth:
		_teeth = t
		_rebuild_mesh()

func _on_gears_train(driver_t: int, idler_t: int, driven_t: int) -> void:
	# 1.3 (3-gear) callback: joint_id 0=driver, 1=idler, 2=driven.
	var t: int
	if joint_id == 0:
		t = driver_t
	elif joint_id == 1:
		t = idler_t
	else:
		t = driven_t
	if t > 0 and t != _teeth:
		_teeth = t
		_rebuild_mesh()

func _on_compound_gears(teeth_a: int, teeth_b: int, teeth_c: int, teeth_d: int) -> void:
	# 2.1 (4-gear compound) callback: pick THIS gear's count by role.
	# B and C share joint_id 1 but have distinct teeth, so joint_id alone
	# is ambiguous — gear_role disambiguates (0=A,1=B,2=C,3=D).
	if gear_role < 0:
		return
	var t: int
	match gear_role:
		0:
			t = teeth_a
		1:
			t = teeth_b
		2:
			t = teeth_c
		3:
			t = teeth_d
		_:
			t = 0
	if t > 0 and t != _teeth:
		_teeth = t
		_rebuild_mesh()

func _on_planetary_gears(teeth_sun: int, teeth_planet: int, teeth_ring: int) -> void:
	# 2.2 (planetary) callback: pick THIS gear's count by role.
	# 4=sun, 5=planet, 6=ring. The carrier has no teeth (it's a plain disc).
	if gear_role < 4 or gear_role > 6:
		return
	var t: int
	match gear_role:
		4:
			t = teeth_sun
		5:
			t = teeth_planet
		6:
			t = teeth_ring
		_:
			t = 0
	if t > 0 and t != _teeth:
		_teeth = t
		_rebuild_mesh()


func _rebuild_mesh() -> void:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	# set_color must come before the first add_vertex so the format
	# includes ARRAY_FORMAT_COLOR (Godot 4 SurfaceTool).
	st.set_color(gear_color)
	# gear_role 6 = the RING gear of a planetary set: an annulus with INWARD
	# teeth (the sun + planets mesh inside it). All other roles use the
	# outward-toothed spur gear.
	if gear_role == 6:
		_build_ring_surface_normalized(st, _teeth)
	else:
		_build_gear_surface_normalized(st, _teeth)
	st.generate_normals()
	mesh = st.commit()

# Procedural spur-gear geometry, built in *normalized* units (pitch
# radius = 1.0). The MeshInstance3D's `scale` is set by the
# GearAssembly to `pitch_r * VISUAL_SCALE` so the gear fits the 3D
# viewport regardless of tooth count.
#
# The gear is a flat disc in the XZ plane with its axis along +Y — same
# convention as a Godot CylinderMesh. The _axis_align basis then
# reorients Y → spin_axis so the disc spins flat around the chosen world
# axis.
#
# Per tooth: a trapezoid with its bottom on the root circle and its top
# on the outer circle. Plus a hub hole through the center.
func _build_gear_surface_normalized(st: SurfaceTool, p_teeth: int) -> void:
	# In normalized units, module and tooth count only matter for the
	# tooth-vs-hub proportions; the outer envelope is unit-radius.
	var pitch_r: float = MESH_PITCH_RADIUS
	# Visual outer is < pitch_r + addendum to keep meshing gears apart.
	var outer_r: float = pitch_r * VISUAL_TIP_FACTOR
	var root_r: float = outer_r * 0.85
	# Hub radius scales with module (tooth size), not pitch diameter, so
	# small gears still have a visible bore.
	var hub_r: float = clamp(0.15 * outer_r, 0.04, 0.25)
	var half_t: float = GEAR_THICKNESS * 0.5
	var tooth_angle: float = TAU / float(p_teeth)
	var tooth_w: float = tooth_angle * 0.5 * 0.5  # half-width of one tooth

	# 2D outline in the XZ plane: each point is (x, z); y is the thickness axis.
	var outline: Array[Vector2] = []
	for i in p_teeth:
		var center: float = float(i) * tooth_angle
		var a_left_root: float = center - tooth_w
		var a_left_outer: float = center - tooth_w * 0.6
		var a_right_outer: float = center + tooth_w * 0.6
		var a_right_root: float = center + tooth_w
		outline.append(Vector2(cos(a_left_root) * root_r, sin(a_left_root) * root_r))
		outline.append(Vector2(cos(a_left_outer) * outer_r, sin(a_left_outer) * outer_r))
		outline.append(Vector2(cos(a_right_outer) * outer_r, sin(a_right_outer) * outer_r))
		outline.append(Vector2(cos(a_right_root) * root_r, sin(a_right_root) * root_r))

	var n_outline: int = outline.size()
	# Top (+y) and bottom (-y) faces, fanned from the center.
	for face_sign in [1, -1]:
		var y: float = half_t * face_sign
		var normal_dir: Vector3 = Vector3(0, 1, 0) * face_sign
		for i in n_outline:
			var p0: Vector2 = outline[i]
			var p1: Vector2 = outline[(i + 1) % n_outline]
			if face_sign > 0:
				st.set_normal(normal_dir)
				st.add_vertex(Vector3(p0.x, y, p0.y))
				st.set_normal(normal_dir)
				st.add_vertex(Vector3(p1.x, y, p1.y))
				st.set_normal(normal_dir)
				st.add_vertex(Vector3(0, y, 0))
			else:
				st.set_normal(normal_dir)
				st.add_vertex(Vector3(0, y, 0))
				st.set_normal(normal_dir)
				st.add_vertex(Vector3(p1.x, y, p1.y))
				st.set_normal(normal_dir)
				st.add_vertex(Vector3(p0.x, y, p0.y))

	# Side wall: outward-facing quads around the XZ outline, connecting ±y.
	for i in n_outline:
		var p0: Vector2 = outline[i]
		var p1: Vector2 = outline[(i + 1) % n_outline]
		var v0_top: Vector3 = Vector3(p0.x, half_t, p0.y)
		var v1_top: Vector3 = Vector3(p1.x, half_t, p1.y)
		var v0_bot: Vector3 = Vector3(p0.x, -half_t, p0.y)
		var v1_bot: Vector3 = Vector3(p1.x, -half_t, p1.y)
		# Outward normal in the XZ plane.
		var edge: Vector2 = (p1 - p0)
		var outward: Vector2 = Vector2(edge.y, -edge.x).normalized()
		var mid: Vector2 = (p0 + p1) * 0.5
		if outward.dot(mid) < 0.0:
			outward = -outward
		var n: Vector3 = Vector3(outward.x, 0, outward.y)
		st.set_normal(n)
		st.add_vertex(v0_top)
		st.set_normal(n)
		st.add_vertex(v1_top)
		st.set_normal(n)
		st.add_vertex(v1_bot)
		st.set_normal(n)
		st.add_vertex(v0_top)
		st.set_normal(n)
		st.add_vertex(v1_bot)
		st.set_normal(n)
		st.add_vertex(v0_bot)

	# Hub hole: an inner cylinder wall so the silhouette has a center bore.
	var hub_segments: int = 24
	for i in hub_segments:
		var a0: float = TAU * float(i) / float(hub_segments)
		var a1: float = TAU * float(i + 1) / float(hub_segments)
		var p0_top: Vector3 = Vector3(cos(a0) * hub_r, half_t, sin(a0) * hub_r)
		var p1_top: Vector3 = Vector3(cos(a1) * hub_r, half_t, sin(a1) * hub_r)
		var p0_bot: Vector3 = Vector3(cos(a0) * hub_r, -half_t, sin(a0) * hub_r)
		var p1_bot: Vector3 = Vector3(cos(a1) * hub_r, -half_t, sin(a1) * hub_r)
		var mid_a: float = (a0 + a1) * 0.5
		var n: Vector3 = Vector3(-cos(mid_a), 0, -sin(mid_a))
		st.set_normal(n)
		st.add_vertex(p0_top)
		st.set_normal(n)
		st.add_vertex(p1_bot)
		st.set_normal(n)
		st.add_vertex(p1_top)
		st.set_normal(n)
		st.add_vertex(p0_top)
		st.set_normal(n)
		st.add_vertex(p0_bot)
		st.set_normal(n)
		st.add_vertex(p1_bot)

# Ring gear (annulus) geometry — the RING of a planetary set. Unlike a spur
# gear, the ring's teeth point INWARD (toward the axle): a planet meshes with
# the ring's internal bore. The pitch circle (radius = MESH_PITCH_RADIUS = 1.0,
# scaled by the assembly to r_ring * VISUAL_SCALE) sits in the tooth gap, so
# the planets — placed at (r_sun + r_planet) = (r_ring - r_planet) for a valid
# set — mesh at the ring's pitch circle and seat into its tooth spaces.
#
# Structure (radii measured from the axle):
#   outer_r  ─ solid outer rim + cylinder wall (smooth)
#             solid band — smooth annulus cap (root_r → outer_r)
#   root_r   ─ tooth roots / inner edge of the solid band (smooth circle)
#             ╳╳ teeth (bore wall, root_r → tip_r, normals inward) ╳╳
#   tip_r    ─ tooth tips (closest to the axle)
#             hollow center (no geometry)
# The cap is a smooth ring from root_r to outer_r; the toothed profile lives
# ONLY on the bore wall, so no teeth bleed onto the outer rim.
func _build_ring_surface_normalized(st: SurfaceTool, p_teeth: int) -> void:
	var pitch_r: float = MESH_PITCH_RADIUS
	# Inward teeth: tips are CLOSEST to the axle (inside the pitch circle),
	# roots are FARTHER out (outside the pitch circle, where teeth meet the
	# solid band). This is the mirror of a spur gear: the tooth dips from
	# root_r inward to tip_r. A planet meshes at the pitch circle (pitch_r),
	# seating its own tips into the ring's tooth gaps. Tooth depth (root_r −
	# tip_r) is kept shallow so the tips don't stretch far toward the axle.
	var tip_r: float = pitch_r * 0.92  # tooth tips, closest to axle (< pitch_r)
	var root_r: float = pitch_r * 1.08  # tooth roots, inner edge of solid band (> pitch_r)
	# Solid outer rim: outside the roots, so the band runs smooth from root_r
	# → outer_r and the toothed profile lives only on the bore (no teeth bleed
	# onto the outer silhouette).
	var outer_r: float = pitch_r * 1.35
	var half_t: float = GEAR_THICKNESS * 0.5
	var tooth_angle: float = TAU / float(p_teeth)
	var tooth_w: float = tooth_angle * 0.5 * 0.5  # half-width of one tooth
	# Resolution of the smooth annulus cap and outer rim (independent of tooth
	# count so a low-tooth ring still reads as round).
	var cap_segments: int = RING_CAP_SEGMENTS

	# Toothed bore profile (inward teeth): a closed polygon walked around the
	# axle where each tooth dips from root_r down to tip_r and back. tip_r < root_r
	# so the teeth point INWARD (toward the axle). This outline is used only for
	# the bore WALL — the cap is a separate smooth annulus (see below) so the
	# tooth wobble never reaches the outer rim.
	var outline: Array[Vector2] = []
	for i in p_teeth:
		var center: float = float(i) * tooth_angle
		var a_left_root: float = center - tooth_w
		var a_left_tip: float = center - tooth_w * 0.6
		var a_right_tip: float = center + tooth_w * 0.6
		var a_right_root: float = center + tooth_w
		outline.append(Vector2(cos(a_left_root) * root_r, sin(a_left_root) * root_r))
		outline.append(Vector2(cos(a_left_tip) * tip_r, sin(a_left_tip) * tip_r))
		outline.append(Vector2(cos(a_right_tip) * tip_r, sin(a_right_tip) * tip_r))
		outline.append(Vector2(cos(a_right_root) * root_r, sin(a_right_root) * root_r))

	var n_outline: int = outline.size()
	# Top (+y) and bottom (-y) faces: a SMOOTH annulus from root_r (the inner
	# edge of the solid band) to outer_r (the outer rim). It is NOT fanned
	# from the toothed outline — that would drag tooth wobble onto the outer
	# edge. Instead the inner boundary is a plain circle at root_r, so the cap
	# reads as a clean ring with a smooth outer silhouette and a smooth inner
	# boundary at the tooth roots.
	for face_sign in [1, -1]:
		var y: float = half_t * face_sign
		var normal_dir: Vector3 = Vector3(0, 1, 0) * face_sign
		for i in cap_segments:
			var a0: float = TAU * float(i) / float(cap_segments)
			var a1: float = TAU * float(i + 1) / float(cap_segments)
			# Inner point at root_r, outer point at outer_r.
			var ix: float = cos(a0) * root_r
			var iz: float = sin(a0) * root_r
			var jx: float = cos(a1) * root_r
			var jz: float = sin(a1) * root_r
			var ox: float = cos(a0) * outer_r
			var oz: float = sin(a0) * outer_r
			var px: float = cos(a1) * outer_r
			var pz: float = sin(a1) * outer_r
			if face_sign > 0:
				st.set_normal(normal_dir)
				st.add_vertex(Vector3(ix, y, iz))
				st.set_normal(normal_dir)
				st.add_vertex(Vector3(jx, y, jz))
				st.set_normal(normal_dir)
				st.add_vertex(Vector3(ox, y, oz))
				st.set_normal(normal_dir)
				st.add_vertex(Vector3(jx, y, jz))
				st.set_normal(normal_dir)
				st.add_vertex(Vector3(px, y, pz))
				st.set_normal(normal_dir)
				st.add_vertex(Vector3(ox, y, oz))
			else:
				st.set_normal(normal_dir)
				st.add_vertex(Vector3(ix, y, iz))
				st.set_normal(normal_dir)
				st.add_vertex(Vector3(ox, y, oz))
				st.set_normal(normal_dir)
				st.add_vertex(Vector3(jx, y, jz))
				st.set_normal(normal_dir)
				st.add_vertex(Vector3(jx, y, jz))
				st.set_normal(normal_dir)
				st.add_vertex(Vector3(ox, y, oz))
				st.set_normal(normal_dir)
				st.add_vertex(Vector3(px, y, pz))

	# Bore wall: the toothed profile, side faces around the outline, normals
	# pointing INWARD (toward the axle) so the internal teeth are lit.
	for i in n_outline:
		var p0: Vector2 = outline[i]
		var p1: Vector2 = outline[(i + 1) % n_outline]
		var v0_top: Vector3 = Vector3(p0.x, half_t, p0.y)
		var v1_top: Vector3 = Vector3(p1.x, half_t, p1.y)
		var v0_bot: Vector3 = Vector3(p0.x, -half_t, p0.y)
		var v1_bot: Vector3 = Vector3(p1.x, -half_t, p1.y)
		# Inward normal (toward axle): flip the spur-gear outward normal.
		var edge: Vector2 = (p1 - p0)
		var inward: Vector2 = Vector2(-edge.y, edge.x).normalized()
		var mid: Vector2 = (p0 + p1) * 0.5
		if inward.dot(mid) > 0.0:
			inward = -inward
		var n: Vector3 = Vector3(inward.x, 0, inward.y)
		st.set_normal(n)
		st.add_vertex(v0_top)
		st.set_normal(n)
		st.add_vertex(v1_top)
		st.set_normal(n)
		st.add_vertex(v1_bot)
		st.set_normal(n)
		st.add_vertex(v0_top)
		st.set_normal(n)
		st.add_vertex(v1_bot)
		st.set_normal(n)
		st.add_vertex(v0_bot)

	# Outer rim wall: a cylinder at outer_r so the solid band has an outside.
	for i in cap_segments:
		var a0: float = TAU * float(i) / float(cap_segments)
		var a1: float = TAU * float(i + 1) / float(cap_segments)
		var p0_top: Vector3 = Vector3(cos(a0) * outer_r, half_t, sin(a0) * outer_r)
		var p1_top: Vector3 = Vector3(cos(a1) * outer_r, half_t, sin(a1) * outer_r)
		var p0_bot: Vector3 = Vector3(cos(a0) * outer_r, -half_t, sin(a0) * outer_r)
		var p1_bot: Vector3 = Vector3(cos(a1) * outer_r, -half_t, sin(a1) * outer_r)
		var mid_a: float = (a0 + a1) * 0.5
		var n2: Vector3 = Vector3(cos(mid_a), 0, sin(mid_a))
		st.set_normal(n2)
		st.add_vertex(p0_top)
		st.set_normal(n2)
		st.add_vertex(p1_bot)
		st.set_normal(n2)
		st.add_vertex(p1_top)
		st.set_normal(n2)
		st.add_vertex(p0_top)
		st.set_normal(n2)
		st.add_vertex(p0_bot)
		st.set_normal(n2)
		st.add_vertex(p1_bot)


# Quaternion (pure rotation, no scale) so callers can compose spins
# without baking in the Node3D scale.
static func _compute_axis_quaternion(axis: Vector3) -> Quaternion:
	var a: Vector3 = axis.normalized()
	if a.is_zero_approx():
		return Quaternion.IDENTITY
	if a == Vector3.UP:
		return Quaternion.IDENTITY
	if a == -Vector3.UP:
		return Quaternion(Vector3.RIGHT, PI)
	return Quaternion(Vector3.UP, a)

# Kept for backward compat with any external caller (e.g. shaft_visual.gd
# pattern). Returns the same reorientation as a Basis.
static func _compute_axis_align(axis: Vector3) -> Basis:
	return Basis(_compute_axis_quaternion(axis))
