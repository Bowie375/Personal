extends Node

## Per-level sim state cached from the bridge.
## One instance lives on each level scene; subscribes to the Bridge autoload.

signal joint_changed(joint_id: int, rpm: float, angle: float)
signal voltage_changed(voltage: float)
signal torque_changed(torque: float)
signal target_changed(target_rpm: float)
signal target_sign_changed(target_sign: int)
signal gear_teeth_changed(driver_teeth: int, driven_teeth: int)
signal gear_train_changed(driver_teeth: int, idler_teeth: int, driven_teeth: int)
signal meshed_changed(meshed: bool)
signal diagnostic_changed(diag: Dictionary)
signal won_changed(won: bool)

# Per-joint state, keyed by joint id.
var joints: Dictionary = {}
# Legacy single-joint convenience (used by 1.1).
var last_rpm: float = 0.0
var last_angle: float = 0.0
var last_voltage: float = 0.0
var last_torque: float = 0.0
var target_rpm: float = 60.0
var target_sign: int = -1
var driver_teeth: int = 0
var idler_teeth: int = 0
var driven_teeth: int = 0
var center_distance: float = 0.0
var meshed: bool = false
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
	var joint_list: Array = state.get("joints", [])
	# Update per-joint state.
	for j in joint_list:
		if not (j is Dictionary):
			continue
		var jid: int = int(j.get("id", 0))
		var jrpm: float = float(j.get("rpm", 0.0))
		var jangle: float = float(j.get("angle", 0.0))
		var key: String = str(jid)
		var prev: Dictionary = joints.get(key, {})
		if not (prev.get("rpm", 0.0) == jrpm and prev.get("angle", 0.0) == jangle):
			joints[key] = {"rpm": jrpm, "angle": jangle}
			joint_changed.emit(jid, jrpm, jangle)
			# Mirror to legacy single-joint view.
			if jid == 0:
				if jrpm != last_rpm:
					last_rpm = jrpm
				if jangle != last_angle:
					last_angle = jangle
	# Update level-level state.
	var new_voltage: float = float(extras.get("voltage", 0.0))
	if new_voltage != last_voltage:
		last_voltage = new_voltage
		voltage_changed.emit(new_voltage)
	var new_torque: float = float(extras.get("torque", 0.0))
	if new_torque != last_torque:
		last_torque = new_torque
		torque_changed.emit(new_torque)
	var new_target: float = float(extras.get("target_driven_rpm", extras.get("target_rpm", 0.0)))
	if new_target != target_rpm:
		target_rpm = new_target
		target_changed.emit(new_target)
	var new_sign: int = int(extras.get("target_sign", 0))
	if new_sign != 0 and new_sign != target_sign:
		target_sign = new_sign
		target_sign_changed.emit(new_sign)
	var new_driver: int = int(extras.get("driver_teeth", 0))
	var new_idler: int = int(extras.get("idler_teeth", 0))
	var new_driven: int = int(extras.get("driven_teeth", 0))
	if new_driver != driver_teeth or new_idler != idler_teeth or new_driven != driven_teeth:
		driver_teeth = new_driver
		idler_teeth = new_idler
		driven_teeth = new_driven
		# For backward compatibility with 1.2, always emit the 2-arg signal.
		gear_teeth_changed.emit(new_driver, new_driven)
		# For 1.3 (3-gear), also emit the 3-arg signal.
		if new_idler > 0:
			gear_train_changed.emit(new_driver, new_idler, new_driven)
	var new_center_distance: float = float(extras.get("center_distance", 0.0))
	center_distance = new_center_distance  # always update; consumers compare
	var new_meshed: bool = bool(extras.get("meshed", true))
	if new_meshed != meshed:
		meshed = new_meshed
		meshed_changed.emit(new_meshed)
	var new_won: bool = bool(extras.get("won", false))
	if new_won != won:
		won = new_won
		won_changed.emit(new_won)
	var diag_raw: Variant = extras.get("diagnostic", {})
	# Python sends null when there's no diagnostic; the .get() default only
	# applies when the key is absent, not when it's explicitly null. Coerce.
	var new_diag: Dictionary = diag_raw if diag_raw is Dictionary else {}
	if new_diag != diagnostic:
		diagnostic = new_diag
		diagnostic_changed.emit(new_diag)
