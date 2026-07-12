extends MeshInstance3D

## Rotates a gear mesh from a specific joint id in LevelState.
##
## A Godot CylinderMesh has its geometry axis along +Y. To spin the gear
## in place around an arbitrary world axis, we reorient the mesh once
## (Y → spin_axis) and then apply the spin on top.

@export var state_path: NodePath
@export var joint_id: int = 0
@export var spin_axis: Vector3 = Vector3(0, 0, 1)

var _state: Node
var _angle: float = 0.0
var _world_basis: Basis
var _axis_align: Basis

func _ready() -> void:
	_world_basis = transform.basis
	_axis_align = _compute_axis_align(spin_axis)
	transform.basis = _world_basis * _axis_align
	_state = get_node_or_null(state_path)
	if _state != null and _state.has_signal("joint_changed"):
		_state.connect("joint_changed", _on_joint)

func _on_joint(jid: int, _rpm: float, angle: float) -> void:
	if jid == joint_id:
		_angle = angle
		var axis: Vector3 = spin_axis.normalized()
		transform.basis = _world_basis * _axis_align * Basis(axis, _angle)

static func _compute_axis_align(axis: Vector3) -> Basis:
	# Returns a basis that rotates the mesh so its +Y axis aligns with `axis`.
	var a: Vector3 = axis.normalized()
	if a.is_zero_approx():
		return Basis.IDENTITY
	if a == Vector3.UP:
		return Basis.IDENTITY
	if a == -Vector3.UP:
		return Basis(Vector3.RIGHT, PI)
	# General case: rotation that takes UP to a, via Quaternion.
	var q: Quaternion = Quaternion(Vector3.UP, a)
	return Basis(q)
