extends MeshInstance3D

## Rotates the shaft mesh from the angle streamed in by LevelState.

@export var state_path: NodePath
@export var spin_axis: Vector3 = Vector3(0, 0, 1)

var _state: Node
var _base_rotation: Basis

func _ready() -> void:
	_base_rotation = transform.basis
	_state = get_node_or_null(state_path)
	if _state != null and _state.has_signal("angle_changed"):
		_state.connect("angle_changed", _on_angle)

func _on_angle(angle_rad: float) -> void:
	transform.basis = _base_rotation * Basis(spin_axis.normalized(), angle_rad)
