extends MeshInstance3D

## Rotates a procedurally-built shaft mesh from the angle streamed in by
## LevelState. The shaft is a cylinder with knurl grooves around its
## circumference and a flat keyway along one side, so spin is unambiguous
## from any angle (a plain cylinder looks static when it spins).
##
## A Godot CylinderMesh has its geometry axis along +Y. We build our own
## mesh with the same axis convention, reorient Y → spin_axis once via a
## Quaternion (pure rotation, no scale baked in), and compose the spin on
## top each frame.

@export var state_path: NodePath
@export var joint_id: int = 0
@export var spin_axis: Vector3 = Vector3(0, 1, 0)
@export var shaft_color: Color = Color(0.7, 0.7, 0.75, 1.0)

# Shaft dimensions (normalized; the scene's transform sets world size).
const SHAFT_RADIUS := 0.1
const SHAFT_LENGTH := 2.0
const KNURL_GROOVES := 24  # circumferential grooves
const KNURL_DEPTH := 0.012  # how deep each groove bites into the radius
const KEYWAY_WIDTH_FRAC := 0.18  # angular width of the keyway flat
const KEYWAY_DEPTH := 0.03  # how far the flat cuts into the radius
const SEGMENTS := 48  # circumferential resolution of the cylinder

var _state: Node
var _angle: float = 0.0
var _orient: Quaternion  # Y → spin_axis, pure rotation

func _ready() -> void:
	_orient = _compute_axis_quaternion(spin_axis)
	# Preserve the scene's scale (set by .tscn / a parent assembly); only
	# bake orientation, not scale.
	var s: Vector3 = transform.basis.get_scale()
	transform = Transform3D(Basis(_orient) * Basis.from_scale(s), transform.origin)
	_build_mesh()
	_state = get_node_or_null(state_path)
	if _state != null and _state.has_signal("joint_changed"):
		_state.connect("joint_changed", _on_joint)

func _on_joint(jid: int, _rpm: float, angle: float) -> void:
	if jid == joint_id:
		_angle = angle
		# Compose the spin as a Quaternion around the mesh's own +Y normal
		# (the disc/shaft symmetry axis), then reapply the live scale so the
		# assembly's sizing survives the spin.
		var live_scale: Vector3 = transform.basis.get_scale()
		var spin: Quaternion = Quaternion(Vector3.UP, _angle)
		var final_basis: Basis = Basis(_orient * spin) * Basis.from_scale(live_scale)
		transform = Transform3D(final_basis, transform.origin)

func _build_mesh() -> void:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	st.set_color(shaft_color)
	_build_shaft_surface(st)
	st.generate_normals()
	mesh = st.commit()

# A cylinder along +Y from -L/2 to +L/2. The side wall is built ring-by-ring
# so we can modulate the radius with (a) knurl grooves and (b) a keyway flat.
# Caps are fanned from the center.
func _build_shaft_surface(st: SurfaceTool) -> void:
	var half_len: float = SHAFT_LENGTH * 0.5
	# Ring heights — denser rings so the knurl reads as discrete grooves.
	var n_rings: int = KNURL_GROOVES * 2
	# Keyway spans the full length on one side; angular center = 0 (local +X).
	var keyway_half_angle: float = TAU * KEYWAY_WIDTH_FRAC * 0.5

	# ---- Side wall rings (collect vertices for striping later) ----
	# rings[r] is the list of (top_vertex, bottom_vertex) for ring r.
	var rings_top: Array = []  # Array[PackedVector3Array] per ring
	var rings_bot: Array = []
	for r in range(n_rings + 1):
		var y: float = -half_len + SHAFT_LENGTH * float(r) / float(n_rings)
		var top_row: PackedVector3Array = PackedVector3Array()
		var bot_row: PackedVector3Array = PackedVector3Array()
		for i in range(SEGMENTS):
			var a: float = TAU * float(i) / float(SEGMENTS)
			var in_keyway: bool = abs(angle_mod(a)) < keyway_half_angle
			var r_base: float = SHAFT_RADIUS
			if in_keyway:
				r_base = SHAFT_RADIUS - KEYWAY_DEPTH
			# Knurl: subtract a small notch synchronized with the ring index
			# so grooves spiral slightly (visually distinct from a plain tube).
			var knurl_phase: float = float(r) / float(KNURL_GROOVES) * TAU
			var knurl: float = cos(a * float(KNURL_GROOVES) + knurl_phase)
			r_base -= KNURL_DEPTH * 0.5 * (1.0 - knurl)  # grooves when knurl=-1
			top_row.append(Vector3(cos(a) * r_base, y, sin(a) * r_base))
			bot_row.append(Vector3(cos(a) * r_base, y, sin(a) * r_base))
		# Only one height per ring (top_row and bot_row share y); simplify:
		rings_top.append(top_row)
		rings_bot.append(bot_row)

	# Emit side-wall quads between consecutive rings.
	for r in range(n_rings):
		var row_a: PackedVector3Array = rings_top[r]
		var row_b: PackedVector3Array = rings_top[r + 1]
		for i in range(SEGMENTS):
			var j: int = (i + 1) % SEGMENTS
			var p00: Vector3 = row_a[i]
			var p01: Vector3 = row_a[j]
			var p10: Vector3 = row_b[i]
			var p11: Vector3 = row_b[j]
			# Outward normal (approximate; generate_normals will recompute).
			var mid: Vector3 = (p00 + p01 + p10 + p11) * 0.25
			var n: Vector3 = Vector3(mid.x, 0.0, mid.z).normalized()
			st.set_normal(n)
			st.add_vertex(p00)
			st.set_normal(n)
			st.add_vertex(p10)
			st.set_normal(n)
			st.add_vertex(p11)
			st.set_normal(n)
			st.add_vertex(p00)
			st.set_normal(n)
			st.add_vertex(p11)
			st.set_normal(n)
			st.add_vertex(p01)

	# ---- Caps (top +Y, bottom -Y), fanned from center ----
	for sign in [1, -1]:
		var y: float = half_len * sign
		var ring: PackedVector3Array = rings_top[0] if sign > 0 else rings_top[n_rings]
		var normal_dir: Vector3 = Vector3(0, 1, 0) * sign
		for i in range(SEGMENTS):
			var j: int = (i + 1) % SEGMENTS
			if sign > 0:
				st.set_normal(normal_dir)
				st.add_vertex(ring[i])
				st.set_normal(normal_dir)
				st.add_vertex(ring[j])
				st.set_normal(normal_dir)
				st.add_vertex(Vector3(0, y, 0))
			else:
				st.set_normal(normal_dir)
				st.add_vertex(Vector3(0, y, 0))
				st.set_normal(normal_dir)
				st.add_vertex(ring[j])
				st.set_normal(normal_dir)
				st.add_vertex(ring[i])

static func angle_mod(a: float) -> float:
	# Wrap to [-PI, PI).
	var v: float = fmod(a + PI, TAU)
	if v < 0.0:
		v += TAU
	return v - PI

static func _compute_axis_quaternion(axis: Vector3) -> Quaternion:
	var a: Vector3 = axis.normalized()
	if a.is_zero_approx():
		return Quaternion.IDENTITY
	if a == Vector3.UP:
		return Quaternion.IDENTITY
	if a == -Vector3.UP:
		return Quaternion(Vector3.RIGHT, PI)
	return Quaternion(Vector3.UP, a)
