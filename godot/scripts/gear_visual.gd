extends MeshInstance3D

## Rotates a gear mesh from a specific joint id in LevelState.

@export var state_path: NodePath
@export var joint_id: int = 0
@export var spin_axis: Vector3 = Vector3(0, 0, 1)

var _state: Node
var _angle: float = 0.0
var _base_rotation: Basis

func _ready() -> void:
	_base_rotation = transform.basis
	_state = get_node_or_null(state_path)
	if _state != null and _state.has_signal("joint_changed"):
		_state.connect("joint_changed", _on_joint)

func _on_joint(jid: int, _rpm: float, angle: float) -> void:
	if jid == joint_id:
		_angle = angle
		transform.basis = _base_rotation * Basis(spin_axis.normalized(), _angle)
