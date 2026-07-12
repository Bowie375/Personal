extends Node

## Per-level sim state cached from the bridge.
## One instance lives on each level scene; subscribes to the Bridge autoload.

signal rpm_changed(rpm: float)
signal angle_changed(angle: float)
signal torque_changed(torque: float)
signal target_changed(target_rpm: float)
signal diagnostic_changed(diag: Dictionary)
signal won_changed(won: bool)

var last_rpm: float = 0.0
var last_torque: float = 0.0
var last_angle: float = 0.0
var target_rpm: float = 60.0
var won: bool = false
var diagnostic: Dictionary = {}

func _ready() -> void:
	var bc: Node = get_node_or_null("/root/Bridge")
	if bc == null:
		push_error("LevelState: Bridge autoload not found")
		return
	bc.connect("sim_state_received", _on_sim_state)

func _on_sim_state(state: Dictionary) -> void:
	var extras: Dictionary = state.get("extras", {})
	var joints: Array = state.get("joints", [])
	if joints.is_empty():
		return
	var new_rpm: float = float(joints[0].get("rpm", 0.0))
	var new_angle: float = float(joints[0].get("angle", 0.0))
	var new_torque: float = float(extras.get("torque", 0.0))
	var new_target: float = float(extras.get("target_rpm", 0.0))
	var new_won: bool = bool(extras.get("won", false))
	var new_diag: Dictionary = extras.get("diagnostic", {})

	if new_rpm != last_rpm:
		last_rpm = new_rpm
		rpm_changed.emit(new_rpm)
	if new_angle != last_angle:
		last_angle = new_angle
		angle_changed.emit(new_angle)
	if new_torque != last_torque:
		last_torque = new_torque
		torque_changed.emit(new_torque)
	if new_target != target_rpm:
		target_rpm = new_target
		target_changed.emit(new_target)
	if new_won != won:
		won = new_won
		won_changed.emit(new_won)
	if new_diag != diagnostic:
		diagnostic = new_diag
		diagnostic_changed.emit(new_diag)
