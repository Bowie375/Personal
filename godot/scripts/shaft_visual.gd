extends MeshInstance3D
class_name ShaftVisual

## Rotates the shaft mesh from the angle streamed in by LevelState.

@export var state_path: NodePath
@export var spin_axis: Vector3 = Vector3(0, 0, 1)

var _state: LevelState
var _base_rotation: Basis

func _ready() -> void:
	_base_rotation = transform.basis
	_state = get_node(state_path) as LevelState
	if _state != null:
		_state.angle_changed.connect(_on_angle)

func _on_angle(angle_rad: float) -> void:
	# Cylinder mesh default axis is Y; rotate around spin_axis.
	transform.basis = _base_rotation * Basis(spin_axis.normalized(), angle_rad)
