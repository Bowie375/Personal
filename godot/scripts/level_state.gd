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
signal compound_gears_changed(teeth_a: int, teeth_b: int, teeth_c: int, teeth_d: int)
signal planetary_gears_changed(teeth_sun: int, teeth_planet: int, teeth_ring: int)
signal mode_changed(mode: String)
signal assemblable_changed(assemblable: bool)
signal meshed_changed(meshed: bool)
signal diagnostic_changed(diag: Dictionary)
signal won_changed(won: bool)
signal load_changed(load_torque: float)
signal target_load_changed(target_load_torque: float)
signal stall_changed(stalled: bool)

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
# Act 1.4 — load on the driven shaft.
var load_torque: float = 0.0
var target_load_torque: float = 0.0
var stalled: bool = false
var output_torque: float = 0.0  # torque at the driven (output) shaft
var motor_side_load: float = 0.0  # load as the motor feels it (reflected)
# Act 2.1 — four-gear compound (A driver, B+C shared shaft, D output).
var teeth_a: int = 0
var teeth_b: int = 0
var teeth_c: int = 0
var teeth_d: int = 0
# Act 2.2 — planetary (sun drives, planets idler, ring/carrier grounded per mode).
var teeth_sun: int = 0
var teeth_planet: int = 0
var teeth_ring: int = 0
var mode: String = "ring_fixed"
var assemblable: bool = false
# Act 2.3 — first joint: the rod's settled angle and its target (radians).
# Read per-tick by the HUD/rod; no dedicated signal (joint_changed id 1 carries
# the angle for the rod's rotation; these are the readout values).
var link_angle: float = 0.0
var target_angle: float = 0.0
# Act 2.4 — two abstracted joints (shoulder + elbow). Per-joint ratio + voltage
# knobs, plus the FK tip position and the target region. Read per-tick by the
# HUD + control panel; no dedicated signals (joint_changed carries the angles;
# id 2 carries the tip pseudo-joint).
var ratio_1: float = 6.0
var ratio_2: float = 6.0
var voltage_1: float = 0.0
var voltage_2: float = 0.0
var joint_angle_1: float = 0.0
var joint_angle_2: float = 0.0
var tip_x: float = 0.0
var tip_y: float = 0.0
var target_x: float = 0.0
var target_y: float = 0.0
var target_radius: float = 0.0
var tip_in_region: bool = false
var settled: bool = false

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
	# Act 2.1 — four-gear compound (teeth_a..d). Absent in other levels.
	var new_a: int = int(extras.get("teeth_a", 0))
	var new_b: int = int(extras.get("teeth_b", 0))
	var new_c: int = int(extras.get("teeth_c", 0))
	var new_d: int = int(extras.get("teeth_d", 0))
	if new_a != teeth_a or new_b != teeth_b or new_c != teeth_c or new_d != teeth_d:
		teeth_a = new_a
		teeth_b = new_b
		teeth_c = new_c
		teeth_d = new_d
		if new_a > 0 and new_b > 0 and new_c > 0 and new_d > 0:
			compound_gears_changed.emit(new_a, new_b, new_c, new_d)
	# Act 2.2 — planetary (sun/planet/ring). Absent in other levels.
	var new_sun: int = int(extras.get("teeth_sun", 0))
	var new_planet: int = int(extras.get("teeth_planet", 0))
	var new_ring: int = int(extras.get("teeth_ring", 0))
	if new_sun != teeth_sun or new_planet != teeth_planet or new_ring != teeth_ring:
		teeth_sun = new_sun
		teeth_planet = new_planet
		teeth_ring = new_ring
		if new_sun > 0 and new_planet > 0 and new_ring > 0:
			planetary_gears_changed.emit(new_sun, new_planet, new_ring)
	var new_mode: String = str(extras.get("mode", ""))
	if new_mode != "" and new_mode != mode:
		mode = new_mode
		mode_changed.emit(new_mode)
	var new_assemblable: bool = bool(extras.get("assemblable", true))
	if new_assemblable != assemblable:
		assemblable = new_assemblable
		assemblable_changed.emit(new_assemblable)
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
	# Act 1.4 — load + stall. Absent in other levels; defaults keep them inert.
	var new_load: float = float(extras.get("load_torque", 0.0))
	if new_load != load_torque:
		load_torque = new_load
		load_changed.emit(new_load)
	var new_target_load: float = float(extras.get("target_load_torque", 0.0))
	if new_target_load != target_load_torque:
		target_load_torque = new_target_load
		target_load_changed.emit(new_target_load)
	var new_stalled: bool = bool(extras.get("stalled", false))
	if new_stalled != stalled:
		stalled = new_stalled
		stall_changed.emit(new_stalled)
	# Act 1.4 readouts — no change signal; the HUD reads them per tick.
	output_torque = float(extras.get("output_torque", 0.0))
	motor_side_load = float(extras.get("motor_side_load", 0.0))
	# Act 2.3 — rod angle + target. Absent in other levels; defaults keep
	# them inert. The HUD reads these per tick to render the angle readout.
	link_angle = float(extras.get("link_angle", 0.0))
	target_angle = float(extras.get("target_angle", 0.0))
	# Act 2.4 — two abstracted joints. Absent in other levels; defaults keep
	# them inert. The HUD + control panel read these per tick.
	ratio_1 = float(extras.get("ratio_1", ratio_1))
	ratio_2 = float(extras.get("ratio_2", ratio_2))
	voltage_1 = float(extras.get("voltage_1", voltage_1))
	voltage_2 = float(extras.get("voltage_2", voltage_2))
	joint_angle_1 = float(extras.get("joint_angle_1", joint_angle_1))
	joint_angle_2 = float(extras.get("joint_angle_2", joint_angle_2))
	tip_x = float(extras.get("tip_x", tip_x))
	tip_y = float(extras.get("tip_y", tip_y))
	target_x = float(extras.get("target_x", target_x))
	target_y = float(extras.get("target_y", target_y))
	target_radius = float(extras.get("target_radius", target_radius))
	tip_in_region = bool(extras.get("tip_in_region", tip_in_region))
	settled = bool(extras.get("settled", settled))
	var diag_raw: Variant = extras.get("diagnostic", {})
	# Python sends null when there's no diagnostic; the .get() default only
	# applies when the key is absent, not when it's explicitly null. Coerce.
	var new_diag: Dictionary = diag_raw if diag_raw is Dictionary else {}
	if new_diag != diagnostic:
		diagnostic = new_diag
		diagnostic_changed.emit(new_diag)
