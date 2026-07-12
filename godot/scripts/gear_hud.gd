extends Control

## HUD overlay for Act 1.2: voltage slider, gear selectors, two RPM gauges,
## diagnostic panel, win panel.

@export var voltage_slider_path: NodePath
@export var voltage_value_label_path: NodePath
@export var driver_rpm_label_path: NodePath
@export var driven_rpm_label_path: NodePath
@export var target_value_label_path: NodePath
@export var driver_bar_path: NodePath
@export var driven_bar_path: NodePath
@export var target_marker_path: NodePath
@export var driver_gear_select_path: NodePath
@export var driven_gear_select_path: NodePath
@export var mesh_status_label_path: NodePath
@export var diagnostic_panel_path: NodePath
@export var diagnostic_message_label_path: NodePath
@export var diagnostic_hint_label_path: NodePath
@export var win_panel_path: NodePath

var _state: Node
var _max_rpm: float = 200.0
var _max_voltage: float = 24.0
var _sending: bool = false
const TEETH_OPTIONS: Array = [12, 16, 20, 24, 30, 36, 40, 48, 60]

func bind(state: Node) -> void:
	_state = state
	state.connect("voltage_changed", _on_voltage_remote)
	state.connect("target_changed", _on_target)
	state.connect("target_sign_changed", _on_target_sign)
	state.connect("gear_teeth_changed", _on_gears)
	state.connect("meshed_changed", _on_meshed)
	state.connect("diagnostic_changed", _on_diagnostic)
	state.connect("won_changed", _on_won)
	state.connect("joint_changed", _on_joint)
	# Prime.
	_on_target(state.target_rpm)
	_on_gears(state.driver_teeth, state.driven_teeth)
	_on_meshed(state.meshed)
	_on_voltage_remote(state.last_voltage)

func _ready() -> void:
	# Voltage slider.
	var v_slider: Range = get_node(voltage_slider_path) as Range
	if v_slider != null:
		v_slider.max_value = _max_voltage
		v_slider.min_value = -_max_voltage
		v_slider.step = 0.1
		v_slider.value_changed.connect(_on_voltage_slider)
	_refresh_voltage_label(v_slider.value if v_slider else 0.0)
	# Gear selectors: populate and wire.
	_populate_gear_select(get_node(driver_gear_select_path))
	_populate_gear_select(get_node(driven_gear_select_path))
	var dsel: OptionButton = get_node(driver_gear_select_path) as OptionButton
	var nsel: OptionButton = get_node(driven_gear_select_path) as OptionButton
	if dsel != null:
		dsel.item_selected.connect(_on_driver_gear_picked)
	if nsel != null:
		nsel.item_selected.connect(_on_driven_gear_picked)
	# Auto-bind to sibling LevelState.
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
	# Default to 30 (1:1 default).
	ob.selected = 3  # 24,30,36 — pick index of 30

func _on_driver_gear_picked(idx: int) -> void:
	_send_gears()

func _on_driven_gear_picked(idx: int) -> void:
	_send_gears()

func _send_gears() -> void:
	var dsel: OptionButton = get_node(driver_gear_select_path) as OptionButton
	var nsel: OptionButton = get_node(driven_gear_select_path) as OptionButton
	if dsel == null or nsel == null:
		return
	var d: int = int(dsel.get_selected_id())
	var dn: int = int(nsel.get_selected_id())
	var bc: Node = get_node_or_null("/root/Bridge")
	if bc != null:
		bc.send_action("set_gears", {"driver": d, "driven": dn})

func _on_voltage_slider(value: float) -> void:
	if _sending:
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

func _on_joint(joint_id: int, rpm: float, _angle: float) -> void:
	if joint_id == 0:
		_set_bar(get_node(driver_rpm_label_path), get_node(driver_bar_path), rpm)
	elif joint_id == 1:
		_set_bar(get_node(driven_rpm_label_path), get_node(driven_bar_path), rpm)

func _set_bar(lbl: Label, bar: ProgressBar, rpm: float) -> void:
	if bar != null:
		bar.max_value = _max_rpm
		# Show magnitude on bar but mark direction in label.
		bar.value = clamp(abs(rpm), 0.0, _max_rpm)
	if lbl != null:
		var arrow: String = "→" if rpm > 0.1 else ("←" if rpm < -0.1 else "·")
		lbl.text = "%s %.1f RPM" % [arrow, abs(rpm)]

func _on_target(target: float) -> None:
	_max_rpm = max(120.0, target * 2.0)
	var marker: Control = get_node(target_marker_path) as Control
	var dbar: ProgressBar = get_node(driver_bar_path) as ProgressBar
	if marker != null and dbar != null:
		var frac: float = clamp(target / _max_rpm, 0.0, 1.0)
		marker.position.x = dbar.position.x + dbar.size.x * frac
	var t: Label = get_node(target_value_label_path) as Label
	if t != null:
		t.text = "Target: %.0f RPM" % target

func _on_target_sign(_sign: int) -> void:
	# Could flip a directional indicator here; for now the level summary
	# already shows the magnitude, and the diagnostic flags sign errors.
	pass

func _on_gears(d_teeth: int, dn_teeth: int) -> void:
	if d_teeth > 0:
		var dsel: OptionButton = get_node(driver_gear_select_path) as OptionButton
		if dsel != null and dsel.get_selected_id() != d_teeth:
			# Map teeth to index in TEETH_OPTIONS.
			var idx: int = TEETH_OPTIONS.find(d_teeth)
			if idx >= 0:
				_sending = true
				dsel.selected = idx
				_sending = false
	if dn_teeth > 0:
		var nsel: OptionButton = get_node(driven_gear_select_path) as OptionButton
		if nsel != null and nsel.get_selected_id() != dn_teeth:
			var idx2: int = TEETH_OPTIONS.find(dn_teeth)
			if idx2 >= 0:
				_sending = true
				nsel.selected = idx2
				_sending = false

func _on_meshed(meshed: bool) -> void:
	var lbl: Label = get_node(mesh_status_label_path) as Label
	if lbl != null:
		lbl.text = "Mesh: " + ("OK" if meshed else "NOT MESHED")
		lbl.modulate = Color(0.4, 1.0, 0.4) if meshed else Color(1.0, 0.5, 0.4)

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
