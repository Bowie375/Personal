extends Control

## HUD overlay: torque slider, RPM bar with target, diagnostic, win banner.
## Bind in the editor to the children listed in @export vars.

@export var torque_slider_path: NodePath
@export var torque_value_label_path: NodePath
@export var rpm_value_label_path: NodePath
@export var target_value_label_path: NodePath
@export var rpm_bar_path: NodePath
@export var target_marker_path: NodePath
@export var diagnostic_panel_path: NodePath
@export var diagnostic_message_label_path: NodePath
@export var diagnostic_hint_label_path: NodePath
@export var win_panel_path: NodePath

var _state: Node  # sibling LevelState node; untyped to avoid parse-order issues
var _max_rpm_for_bar: float = 120.0
var _max_torque: float = 2.0
var _sending: bool = false  # guard against feedback loop

func bind(state: Node) -> void:
	_state = state
	state.connect("joint_changed", _on_joint)
	state.connect("torque_changed", _on_torque_remote)
	state.connect("target_changed", _on_target)
	state.connect("diagnostic_changed", _on_diagnostic)
	state.connect("won_changed", _on_won)
	# Prime initial values.
	_on_target(state.target_rpm)
	_on_torque_remote(state.last_torque)

func _on_joint(_joint_id: int, rpm: float, _angle: float) -> void:
	# 1.1 has only one shaft (joint 0), so any joint change updates the bar.
	_on_rpm(rpm)

func _ready() -> void:
	# Slider drives torque actions; release/change sends a set_torque.
	var slider: Range = get_node(torque_slider_path) as Range
	if slider != null:
		slider.max_value = _max_torque
		slider.min_value = -_max_torque
		slider.step = 0.01
		slider.value_changed.connect(_on_slider_changed)
	_refresh_torque_label(slider.value if slider else 0.0)
	# Auto-bind to a sibling LevelState if present.
	var owner_node: Node = get_parent()
	if owner_node != null:
		var candidate: Node = owner_node.get_node_or_null("LevelState")
		if candidate != null and candidate.has_signal("joint_changed"):
			bind(candidate)

func _on_slider_changed(value: float) -> void:
	if _sending or _state == null:
		return
	var bc: Node = get_node_or_null("/root/Bridge")
	if bc == null:
		return
	bc.send_action("set_torque", {"value": float(value)})
	_refresh_torque_label(value)

func _on_torque_remote(value: float) -> void:
	# Server echoed our torque back. Sync slider without re-sending.
	var slider: Range = get_node(torque_slider_path) as Range
	if slider != null and abs(slider.value - value) > 0.001:
		_sending = true
		slider.value = value
		_sending = false
	_refresh_torque_label(value)

func _on_rpm(rpm: float) -> void:
	var bar: ProgressBar = get_node(rpm_bar_path) as ProgressBar
	if bar != null:
		bar.max_value = _max_rpm_for_bar
		bar.value = clamp(rpm, 0.0, _max_rpm_for_bar)
	var lbl: Label = get_node(rpm_value_label_path) as Label
	if lbl != null:
		lbl.text = "%.1f RPM" % rpm

func _on_target(target: float) -> void:
	_max_rpm_for_bar = max(120.0, target * 2.0)
	var bar: ProgressBar = get_node(rpm_bar_path) as ProgressBar
	if bar != null:
		bar.max_value = _max_rpm_for_bar
	var marker: Control = get_node(target_marker_path) as Control
	if marker != null and bar != null:
		# Position marker as a fraction of the bar.
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

func _refresh_torque_label(value: float) -> void:
	var lbl: Label = get_node(torque_value_label_path) as Label
	if lbl != null:
		lbl.text = "Torque: %+.2f N·m" % value

func _unhandled_input(event: InputEvent) -> void:
	# Keyboard torque control: Up/W increase, Down/S decrease, R reset.
	if event.is_action_pressed("torque_up"):
		_bump_torque(0.05)
	elif event.is_action_pressed("torque_down"):
		_bump_torque(-0.05)
	elif event.is_action_pressed("reset_level"):
		var bc: Node = get_node_or_null("/root/Bridge")
		if bc != null:
			bc.send_action("reset", {})

func _bump_torque(delta: float) -> void:
	var slider: Range = get_node(torque_slider_path) as Range
	if slider != null:
		slider.value = clamp(slider.value + delta, -_max_torque, _max_torque)
