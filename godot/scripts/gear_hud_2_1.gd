extends Control

## HUD overlay for Act 2.1 (compound gearbox): voltage slider, load slider,
## FOUR gear selectors (A driver, B, C, D output), ratio readout
## (stage1 × stage2 = total vs target), RPM gauges (driver/intermediate/output),
## stall banner, torque readouts, diagnostic + win panels.

@export var voltage_slider_path: NodePath
@export var voltage_value_label_path: NodePath
@export var load_slider_path: NodePath
@export var load_value_label_path: NodePath
@export var target_load_label_path: NodePath
@export var gear_a_select_path: NodePath
@export var gear_b_select_path: NodePath
@export var gear_c_select_path: NodePath
@export var gear_d_select_path: NodePath
@export var ratio_value_label_path: NodePath
@export var target_ratio_label_path: NodePath
@export var driver_rpm_label_path: NodePath
@export var intermediate_rpm_label_path: NodePath
@export var output_rpm_label_path: NodePath
@export var target_value_label_path: NodePath
@export var driver_bar_path: NodePath
@export var intermediate_bar_path: NodePath
@export var output_bar_path: NodePath
@export var target_marker_path: NodePath
@export var output_torque_label_path: NodePath
@export var motor_side_load_label_path: NodePath
@export var stall_banner_path: NodePath
@export var diagnostic_panel_path: NodePath
@export var diagnostic_message_label_path: NodePath
@export var diagnostic_hint_label_path: NodePath
@export var win_panel_path: NodePath

var _state: Node
var _max_rpm: float = 200.0
var _max_voltage: float = 24.0
var _max_load: float = 2.0
var _sending: bool = false
const TEETH_OPTIONS: Array = [12, 16, 20, 24, 30, 36, 40, 48, 60]

func bind(state: Node) -> void:
	_state = state
	state.connect("voltage_changed", _on_voltage_remote)
	state.connect("load_changed", _on_load_remote)
	state.connect("target_load_changed", _on_target_load)
	state.connect("stall_changed", _on_stall)
	state.connect("target_changed", _on_target)
	state.connect("target_sign_changed", _on_target_sign)
	state.connect("compound_gears_changed", _on_gears)
	state.connect("meshed_changed", _on_meshed)
	state.connect("diagnostic_changed", _on_diagnostic)
	state.connect("won_changed", _on_won)
	state.connect("joint_changed", _on_joint)
	# Prime.
	_on_target(state.target_rpm)
	_on_gears(state.teeth_a, state.teeth_b, state.teeth_c, state.teeth_d)
	_on_meshed(state.meshed)
	_on_voltage_remote(state.last_voltage)
	_on_load_remote(state.load_torque)
	_on_target_load(state.target_load_torque)
	_on_stall(state.stalled)

func _ready() -> void:
	var v_slider: Range = get_node(voltage_slider_path) as Range
	if v_slider != null:
		v_slider.max_value = _max_voltage
		v_slider.min_value = -_max_voltage
		v_slider.step = 0.1
		v_slider.value_changed.connect(_on_voltage_slider)
	_refresh_voltage_label(v_slider.value if v_slider else 0.0)
	var l_slider: Range = get_node(load_slider_path) as Range
	if l_slider != null:
		l_slider.max_value = _max_load
		l_slider.min_value = 0.0
		l_slider.step = 0.05
		l_slider.value_changed.connect(_on_load_slider)
	_refresh_load_label(l_slider.value if l_slider else 0.0)
	for p in [gear_a_select_path, gear_b_select_path, gear_c_select_path, gear_d_select_path]:
		_populate_gear_select(get_node(p))
	for path in [gear_a_select_path, gear_b_select_path, gear_c_select_path, gear_d_select_path]:
		var ob: OptionButton = get_node(path) as OptionButton
		if ob != null:
			ob.item_selected.connect(_on_gear_picked)
	var owner_node: Node = get_parent()
	if owner_node != null:
		var candidate: Node = owner_node.get_node_or_null("LevelState")
		if candidate != null and candidate.has_signal("voltage_changed"):
			bind(candidate)

func _populate_gear_select(select: Node) -> void:
	if select == null or not (select is OptionButton):
		return
	var ob: OptionButton = select as OptionButton
	ob.clear()
	for n in TEETH_OPTIONS:
		ob.add_item("N%d" % n, n)
	ob.selected = 4  # index of 30

func _on_gear_picked(_idx: int) -> void:
	_send_gears()

func _send_gears() -> void:
	var a: int = int((get_node(gear_a_select_path) as OptionButton).get_selected_id())
	var b: int = int((get_node(gear_b_select_path) as OptionButton).get_selected_id())
	var c: int = int((get_node(gear_c_select_path) as OptionButton).get_selected_id())
	var d: int = int((get_node(gear_d_select_path) as OptionButton).get_selected_id())
	var bc: Node = get_node_or_null("/root/Bridge")
	if bc != null:
		bc.send_action("set_gears", {"a": a, "b": b, "c": c, "d": d})

func _on_voltage_slider(value: float) -> void:
	if _sending:
		return
	var bc: Node = get_node_or_null("/root/Bridge")
	if bc == null:
		return
	bc.send_action("set_voltage", {"value": float(value)})
	_refresh_voltage_label(value)

func _on_load_slider(value: float) -> void:
	if _sending:
		return
	var bc: Node = get_node_or_null("/root/Bridge")
	if bc == null:
		return
	bc.send_action("set_load", {"value": float(value)})
	_refresh_load_label(value)

func _on_voltage_remote(value: float) -> void:
	var v_slider: Range = get_node(voltage_slider_path) as Range
	if v_slider != null and abs(v_slider.value - value) > 0.05:
		_sending = true
		v_slider.value = value
		_sending = false
	_refresh_voltage_label(value)

func _on_load_remote(value: float) -> void:
	var l_slider: Range = get_node(load_slider_path) as Range
	if l_slider != null and abs(l_slider.value - value) > 0.05:
		_sending = true
		l_slider.value = value
		_sending = false
	_refresh_load_label(value)

func _on_target_load(target: float) -> void:
	var lbl: Label = get_node(target_load_label_path) as Label
	if lbl != null:
		lbl.text = "Target load: %.2f N·m" % target

func _on_stall(stalled: bool) -> void:
	var banner: Control = get_node_or_null(stall_banner_path) as Control
	if banner != null:
		banner.visible = stalled

func _on_joint(joint_id: int, rpm: float, _angle: float) -> void:
	if joint_id == 0:
		_set_bar(get_node(driver_rpm_label_path), get_node(driver_bar_path), rpm)
	elif joint_id == 1:
		_set_bar(get_node(intermediate_rpm_label_path), get_node(intermediate_bar_path), rpm)
	elif joint_id == 2:
		_set_bar(get_node(output_rpm_label_path), get_node(output_bar_path), rpm)
	_update_torque()

func _set_bar(lbl: Label, bar: ProgressBar, rpm: float) -> void:
	if bar != null:
		bar.max_value = _max_rpm
		bar.value = clamp(abs(rpm), 0.0, _max_rpm)
	if lbl != null:
		var arrow: String = "→" if rpm > 0.1 else ("←" if rpm < -0.1 else "·")
		lbl.text = "%s %.1f RPM" % [arrow, abs(rpm)]

func _on_target(target: float) -> void:
	_max_rpm = max(120.0, target * 6.0)  # driver spins ratio× faster; room to show it
	var marker: Control = get_node(target_marker_path) as Control
	var obar: ProgressBar = get_node(output_bar_path) as ProgressBar
	if marker != null and obar != null:
		var frac: float = clamp(target / _max_rpm, 0.0, 1.0)
		marker.position.x = obar.position.x + obar.size.x * frac
	var t: Label = get_node(target_value_label_path) as Label
	if t != null:
		t.text = "Target: %.0f RPM" % target

func _on_target_sign(_sign: int) -> void:
	pass

func _on_gears(a: int, b: int, c: int, d: int) -> void:
	if a > 0:
		_select_teeth(gear_a_select_path, a)
	if b > 0:
		_select_teeth(gear_b_select_path, b)
	if c > 0:
		_select_teeth(gear_c_select_path, c)
	if d > 0:
		_select_teeth(gear_d_select_path, d)
	# Ratio readout: stage1 × stage2 = total, vs target.
	if a > 0 and b > 0 and c > 0 and d > 0:
		var s1: float = float(b) / float(a)
		var s2: float = float(d) / float(c)
		var total: float = s1 * s2
		var lbl: Label = get_node(ratio_value_label_path) as Label
		if lbl != null:
			lbl.text = "%.2f × %.2f = %.1f:1" % [s1, s2, total]
		var tgt_lbl: Label = get_node(target_ratio_label_path) as Label
		if tgt_lbl != null and _state != null:
			var tr: float = float(_state.get("target_ratio")) if _state.get("target_ratio") != null else 0.0
			tgt_lbl.text = "Target: %.1f:1 (single mesh max 5:1)" % tr
	_update_torque()

func _select_teeth(path: NodePath, teeth: int) -> void:
	var ob: OptionButton = get_node(path) as OptionButton
	if ob != null and ob.get_selected_id() != teeth:
		var idx: int = TEETH_OPTIONS.find(teeth)
		if idx >= 0:
			_sending = true
			ob.selected = idx
			_sending = false

func _update_torque() -> void:
	if _state == null:
		return
	var out_t: float = float(_state.get("output_torque"))
	var motor_t: float = float(_state.get("motor_side_load"))
	var out_lbl: Label = get_node(output_torque_label_path) as Label
	if out_lbl != null:
		out_lbl.text = "%.2f N·m" % out_t
	var motor_lbl: Label = get_node(motor_side_load_label_path) as Label
	if motor_lbl != null:
		motor_lbl.text = "%.2f N·m" % motor_t

func _on_meshed(meshed: bool) -> void:
	# 2.1 always meshes (uniform module catalog); no separate mesh label.
	pass

func _on_diagnostic(diag: Dictionary) -> void:
	var panel: Control = get_node(diagnostic_panel_path) as Control
	var msg: Label = get_node(diagnostic_message_label_path) as Label
	var hint: Label = get_node(diagnostic_hint_label_path) as Label
	if panel == null:
		return
	if diag.is_empty():
		panel.visible = false
		return
	panel.visible = true
	if msg != null:
		msg.text = str(diag.get("message", ""))
	if hint != null:
		hint.text = str(diag.get("hint", ""))

func _on_won(won: bool) -> void:
	var panel: Control = get_node(win_panel_path) as Control
	if panel != null:
		panel.visible = won

func _refresh_voltage_label(value: float) -> void:
	var lbl: Label = get_node(voltage_value_label_path) as Label
	if lbl != null:
		lbl.text = "%+.2f V" % value

func _refresh_load_label(value: float) -> void:
	var lbl: Label = get_node(load_value_label_path) as Label
	if lbl != null:
		lbl.text = "%.2f N·m" % value
	_update_torque()

func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("torque_up"):
		_bump_voltage(0.5)
	elif event.is_action_pressed("torque_down"):
		_bump_voltage(-0.5)
	elif event.is_action_pressed("reset_level"):
		var bc: Node = get_node_or_null("/root/Bridge")
		if bc != null:
			bc.send_action("reset", {})

func _bump_voltage(delta: float) -> void:
	var v_slider: Range = get_node(voltage_slider_path) as Range
	if v_slider != null:
		v_slider.value = clamp(v_slider.value + delta, -_max_voltage, _max_voltage)
