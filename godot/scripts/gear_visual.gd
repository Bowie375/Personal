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

const GEAR_MODULE := 1.0
const GEAR_THICKNESS := 0.4
# The visible gear is drawn at this fraction of the pitch radius.
# A value < 1.0 keeps adjacent meshing gears from visually overlapping
# (since the real addendum would make outer radii sum to > center
# distance). 0.8 leaves a small visible gap between meshing gears.
const VISUAL_TIP_FACTOR := 0.8

var _state: Node
var _angle: float = 0.0
var _world_basis: Basis
var _axis_align: Basis
var _teeth: int = 0

func _ready() -> void:
	_world_basis = transform.basis
	_axis_align = _compute_axis_align(spin_axis)
	transform.basis = _world_basis * _axis_align
	_state = get_node_or_null(state_path)
	if _state == null:
		return
	if _state.has_signal("joint_changed"):
		_state.connect("joint_changed", _on_joint)
	if _state.has_signal("gear_teeth_changed"):
		_state.connect("gear_teeth_changed", _on_gears)
	# If the state already has a tooth count, build the mesh now.
	_initial_teeth_from_state()

func _initial_teeth_from_state() -> void:
	var driver_t: int = int(_state.get("driver_teeth", 0))
	var driven_t: int = int(_state.get("driven_teeth", 0))
	var t: int = driver_t if joint_id == 0 else driven_t
	if t <= 0:
		t = 30  # safe default if bridge hasn't sent state yet
	_teeth = t
	_rebuild_mesh()

func _on_joint(jid: int, _rpm: float, angle: float) -> void:
	if jid == joint_id:
		_angle = angle
		var axis: Vector3 = spin_axis.normalized()
		transform.basis = _world_basis * _axis_align * Basis(axis, _angle)

func _on_gears(driver_t: int, driven_t: int) -> void:
	var t: int = driver_t if joint_id == 0 else driven_t
	if t > 0 and t != _teeth:
		_teeth = t
		_rebuild_mesh()

func _rebuild_mesh() -> void:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	_build_gear_surface(st, _teeth, GEAR_MODULE, GEAR_THICKNESS)
	st.set_color(gear_color)
	st.generate_normals()
	mesh = st.commit()

# Procedural spur-gear geometry. The gear is a flat disc in the XZ plane
# with its axis along +Y — same convention as a Godot CylinderMesh. The
# _axis_align basis then reorients Y → spin_axis so the disc spins flat
# around the chosen world axis.
#
# Per tooth: a trapezoid with its bottom on the root circle and its
# top on the outer circle. Plus a hub hole through the center.
func _build_gear_surface(
	st: SurfaceTool, p_teeth: int, p_module: float, p_thickness: float
) -> void:
	var pitch_r: float = p_module * p_teeth / 2.0
	# Visual outer is < pitch_r + addendum to keep meshing gears apart.
	var outer_r: float = pitch_r * VISUAL_TIP_FACTOR
	var root_r: float = outer_r * 0.85
	var hub_r: float = max(p_module * 0.8, root_r * 0.25)
	var half_t: float = p_thickness * 0.5
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

static func _compute_axis_align(axis: Vector3) -> Basis:
	var a: Vector3 = axis.normalized()
	if a.is_zero_approx():
		return Basis.IDENTITY
	if a == Vector3.UP:
		return Basis.IDENTITY
	if a == -Vector3.UP:
		return Basis(Vector3.RIGHT, PI)
	var q: Quaternion = Quaternion(Vector3.UP, a)
	return Basis(q)
