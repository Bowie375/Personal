extends MeshInstance3D

## Rotates a clean cylinder shaft from the angle streamed in by LevelState.
##
## The shaft is a plain metallic cylinder (set via CylinderMesh in the
## .tscn); the toothed gear mounted on it provides the visible rotation cue.
## We reorient the mesh's geometry axis (+Y) onto spin_axis once via a
## Quaternion (pure rotation, no scale baked in), and compose the spin on
## top each frame — same pattern as gear_visual.gd.

@export var state_path: NodePath
@export var joint_id: int = 0
@export var spin_axis: Vector3 = Vector3(0, 1, 0)

var _state: Node
var _angle: float = 0.0
var _orient: Quaternion

func _ready() -> void:
	_orient = _compute_axis_quaternion(spin_axis)
	# Preserve the scene's scale; only bake orientation.
	var s: Vector3 = transform.basis.get_scale()
	transform = Transform3D(Basis(_orient) * Basis.from_scale(s), transform.origin)
	_state = get_node_or_null(state_path)
	if _state != null and _state.has_signal("joint_changed"):
		_state.connect("joint_changed", _on_joint)

func _on_joint(jid: int, _rpm: float, angle: float) -> void:
	if jid == joint_id:
		_angle = angle
		# Compose the spin around the mesh's +Y symmetry axis, reapplying
		# the live scale so any assembly sizing survives the spin.
		var live_scale: Vector3 = transform.basis.get_scale()
		var spin: Quaternion = Quaternion(Vector3.UP, _angle)
		var final_basis: Basis = Basis(_orient * spin) * Basis.from_scale(live_scale)
		transform = Transform3D(final_basis, transform.origin)

static func _compute_axis_quaternion(axis: Vector3) -> Quaternion:
	var a: Vector3 = axis.normalized()
	if a.is_zero_approx():
		return Quaternion.IDENTITY
	if a == Vector3.UP:
		return Quaternion.IDENTITY
	if a == -Vector3.UP:
		return Quaternion(Vector3.RIGHT, PI)
	return Quaternion(Vector3.UP, a)
