extends Control

## HUD overlay for Act 1.1: voltage slider, five motor/mechanical parameter
## sliders (Kt, Kb, R, I, b), RPM bar with target, diagnostic, win banner.
##
## 1.1 is the motor primer: the player tunes the raw motor params to see
## how each shapes the steady-state RPM. Later levels abstract V→RPM away.

@export var voltage_slider_path: NodePath
@export var voltage_value_label_path: NodePath
@export var kt_slider_path: NodePath
@export var kt_value_label_path: NodePath
@export var kb_slider_path: NodePath
@export var kb_value_label_path: NodePath
@export var resistance_slider_path: NodePath
@export var resistance_value_label_path: NodePath
@export var inertia_slider_path: NodePath
@export var inertia_value_label_path: NodePath
@export var damping_slider_path: NodePath
@export var damping_value_label_path: NodePath
@export var rpm_value_label_path: NodePath
@export var target_value_label_path: NodePath
@export var rpm_bar_path: NodePath
@export var target_marker_path: NodePath
@export var diagnostic_panel_path: NodePath
@export var diagnostic_message_label_path: NodePath
@export var diagnostic_hint_label_path: NodePath
@export var win_panel_path: NodePath

var _state: Node
var _max_rpm_for_bar: float = 120.0
var _max_voltage: float = 24.0
var _sending: bool = false  # guard against feedback loops

# Slider ranges (min, max, step) for each tunable param.
const KT_MIN := 0.01
const KT_MAX := 0.5
const KB_MIN := 0.0
const KB_MAX := 0.5
const R_MIN := 0.1
const R_MAX := 10.0
const I_MIN := 0.001
const I_MAX := 1.0
const B_MIN := 0.001
const B_MAX := 1.0

func bind(state: Node) -> void:
	_state = state
	state.connect("joint_changed", _on_joint)
	state.connect("voltage_changed", _on_voltage_remote)
	state.connect("target_changed", _on_target)
	state.connect("diagnostic_changed", _on_diagnostic)
	state.connect("won_changed", _on_won)
	# Prime initial values.
	_on_target(state.target_rpm)
	_on_voltage_remote(state.last_voltage)

func _on_joint(_joint_id: int, rpm: float, _angle: float) -> void:
	# 1.1 has only one shaft (joint 0).
	_on_rpm(rpm)

func _ready() -> void:
	# Voltage slider.
	var v_slider: Range = get_node(voltage_slider_path) as Range
	if v_slider != null:
		v_slider.max_value = _max_voltage
		v_slider.min_value = -_max_voltage
		v_slider.step = 0.1
		v_slider.value_changed.connect(_on_voltage_slider)
	_refresh_voltage_label(v_slider.value if v_slider else 0.0)
	# Parameter sliders.
	_setup_param_slider(kt_slider_path, KT_MIN, KT_MAX, 0.005, 0.05)
	_setup_param_slider(kb_slider_path, KB_MIN, KB_MAX, 0.005, 0.05)
	_setup_param_slider(resistance_slider_path, R_MIN, R_MAX, 0.1, 1.0)
	_setup_param_slider(inertia_slider_path, I_MIN, I_MAX, 0.001, 0.05)
	_setup_param_slider(damping_slider_path, B_MIN, B_MAX, 0.005, 0.05)
	# Auto-bind to a sibling LevelState if present.
	var owner_node: Node = get_parent()
	if owner_node != null:
		var candidate: Node = owner_node.get_node_or_null("LevelState")
		if candidate != null and candidate.has_signal("joint_changed"):
			bind(candidate)

func _setup_param_slider(path: NodePath, lo: float, hi: float, step: float, _default: float) -> void:
	var slider: Range = get_node(path) as Range
	if slider == null:
		return
	slider.min_value = lo
	slider.max_value = hi
	slider.step = step
	slider.value_changed.connect(_on_param_slider_changed)

func _on_voltage_slider(value: float) -> void:
	if _sending or _state == null:
		return
	var bc: Node = get_node_or_null("/root/Bridge")
	if bc == null:
		return
	bc.send_action("set_voltage", {"value": float(value)})
	_refresh_voltage_label(value)

func _on_voltage_remote(value: float) -> void:
	var v_slider: Range = get_node(voltage_slider_path) as Range
	if v_slider != null and abs(v_slider.value - value) > 0.05:
		_sending = true
		v_slider.value = value
		_sending = false
	_refresh_voltage_label(value)

func _on_param_slider_changed(_value: float) -> void:
	if _sending or _state == null:
		return
	# Send the full param set from all five sliders.
	var kt: float = (get_node(kt_slider_path) as Range).value
	var kb: float = (get_node(kb_slider_path) as Range).value
	var r: float = (get_node(resistance_slider_path) as Range).value
	var i: float = (get_node(inertia_slider_path) as Range).value
	var b: float = (get_node(damping_slider_path) as Range).value
	_refresh_param_labels(kt, kb, r, i, b)
	var bc: Node = get_node_or_null("/root/Bridge")
	if bc == null:
		return
	bc.send_action("set_params", {
		"kt": kt, "kb": kb, "resistance": r, "inertia": i, "damping": b
	})

func _on_rpm(rpm: float) -> void:
	var bar: ProgressBar = get_node(rpm_bar_path) as ProgressBar
	if bar != null:
		bar.max_value = _max_rpm_for_bar
		bar.value = clamp(abs(rpm), 0.0, _max_rpm_for_bar)
	var lbl: Label = get_node(rpm_value_label_path) as Label
	if lbl != null:
		var arrow: String = "→" if rpm > 0.1 else ("←" if rpm < -0.1 else "·")
		lbl.text = "%s %.1f RPM" % [arrow, abs(rpm)]

func _on_target(target: float) -> void:
	_max_rpm_for_bar = max(120.0, target * 2.0)
	var bar: ProgressBar = get_node(rpm_bar_path) as ProgressBar
	if bar != null:
		bar.max_value = _max_rpm_for_bar
	var marker: Control = get_node(target_marker_path) as Control
	if marker != null and bar != null:
		var frac: float = clamp(target / _max_rpm_for_bar, 0.0, 1.0)
		marker.position.x = bar.position.x + bar.size.x * frac
	var t: Label = get_node(target_value_label_path) as Label
	if t != null:
		t.text = "Target: %.0f RPM" % target

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
		lbl.text = "Voltage: %+.2f V" % value

func _refresh_param_labels(kt: float, kb: float, r: float, i: float, b: float) -> void:
	var lbl: Label = get_node(kt_value_label_path) as Label
	if lbl != null:
		lbl.text = "%.3f" % kt
	lbl = get_node(kb_value_label_path) as Label
	if lbl != null:
		lbl.text = "%.3f" % kb
	lbl = get_node(resistance_value_label_path) as Label
	if lbl != null:
		lbl.text = "%.2f Ω" % r
	lbl = get_node(inertia_value_label_path) as Label
	if lbl != null:
		lbl.text = "%.3f" % i
	lbl = get_node(damping_value_label_path) as Label
	if lbl != null:
		lbl.text = "%.3f" % b

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
