extends Control

## Per-joint control panel for Act 2.4. One panel, re-binds to whichever joint
## the player clicked. Shows that joint's REDUCTION ratio slider + motor
## VOLTAGE slider, initialised from the live state. This is the abstraction
## boundary: the gearbox is gone, replaced by its two knobs.

@export var ratio_slider_path: NodePath
@export var ratio_value_label_path: NodePath
@export var voltage_slider_path: NodePath
@export var voltage_value_label_path: NodePath
@export var joint_label_path: NodePath
@export var state_path: NodePath

var _state: Node
var _active_joint: int = -1  # -1 = none selected
var _sending: bool = false

const RATIO_CHOICES: Array = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
const MAX_VOLTAGE: float = 24.0


func bind(state: Node) -> void:
	_state = state


func _make_click_through(node: Node) -> void:
	if node is Control:
		# Sliders keep their default STOP so they capture clicks; everything
		# else lets clicks pass through to the 3D scene behind.
		if not (node is Range or node is Button or node is OptionButton):
			node.mouse_filter = Control.MOUSE_FILTER_IGNORE
	for c in node.get_children():
		_make_click_through(c)


func _ready() -> void:
	# This panel overlays the 3D scene. Its sliders must stay clickable, but
	# the panel itself + its containers/labels must let clicks fall through to
	# the 3D scene (otherwise they'd swallow the joint picks). IGNORE every
	# non-interactive Control under this panel.
	_make_click_through(self)
	var r_slider: Range = get_node(ratio_slider_path) as Range
	if r_slider != null:
		r_slider.min_value = 0.0
		r_slider.max_value = float(RATIO_CHOICES.size() - 1)
		r_slider.step = 1.0
		r_slider.value_changed.connect(_on_ratio_slider)
	var v_slider: Range = get_node(voltage_slider_path) as Range
	if v_slider != null:
		v_slider.min_value = 0.0
		v_slider.max_value = MAX_VOLTAGE
		v_slider.step = 0.05
		v_slider.value_changed.connect(_on_voltage_slider)
	# Auto-bind to sibling LevelState.
	var owner_node: Node = get_parent()
	if owner_node != null:
		var candidate: Node = owner_node.get_node_or_null("LevelState")
		if candidate != null:
			bind(candidate)
	# No joint selected at start.
	_show_none()


func select_joint(joint_id: int) -> void:
	_active_joint = joint_id
	var jlbl: Label = get_node(joint_label_path) as Label
	if jlbl != null:
		jlbl.text = "Joint %d (%s)" % [joint_id, "Shoulder" if joint_id == 0 else "Elbow"]
	_refresh_from_state()


func deselect() -> void:
	_active_joint = -1
	_show_none()


func _show_none() -> void:
	var jlbl: Label = get_node(joint_label_path) as Label
	if jlbl != null:
		jlbl.text = "Click a joint…"


func _refresh_from_state() -> void:
	if _state == null or _active_joint < 0:
		return
	# Read the current ratio + voltage for the active joint from the state.
	var ratio: float = float(_state.get("ratio_1")) if _active_joint == 0 else float(_state.get("ratio_2"))
	var volt: float = float(_state.get("voltage_1")) if _active_joint == 0 else float(_state.get("voltage_2"))
	# Map the ratio value to its index in RATIO_CHOICES (snap to nearest).
	var idx: int = 0
	var best_err: float = INF
	for i in RATIO_CHOICES.size():
		var e: float = abs(float(RATIO_CHOICES[i]) - ratio)
		if e < best_err:
			best_err = e
			idx = i
	var r_slider: Range = get_node(ratio_slider_path) as Range
	if r_slider != null:
		_sending = true
		r_slider.value = float(idx)
		_sending = false
	var v_slider: Range = get_node(voltage_slider_path) as Range
	if v_slider != null:
		_sending = true
		v_slider.value = volt
		_sending = false
	_refresh_ratio_label(ratio)
	_refresh_voltage_label(volt)


func _on_ratio_slider(idx: float) -> void:
	if _sending or _active_joint < 0:
		return
	var i: int = int(idx)
	if i < 0 or i >= RATIO_CHOICES.size():
		return
	var ratio: float = float(RATIO_CHOICES[i])
	var bc: Node = get_node_or_null("/root/Bridge")
	if bc != null:
		bc.send_action("set_joint_ratio", {"id": _active_joint, "value": ratio})
	_refresh_ratio_label(ratio)


func _on_voltage_slider(value: float) -> void:
	if _sending or _active_joint < 0:
		return
	var bc: Node = get_node_or_null("/root/Bridge")
	if bc != null:
		bc.send_action("set_joint_voltage", {"id": _active_joint, "value": float(value)})
	_refresh_voltage_label(value)


func _refresh_ratio_label(ratio: float) -> void:
	var lbl: Label = get_node(ratio_value_label_path) as Label
	if lbl != null:
		lbl.text = "Ratio: %.0f:1" % ratio


func _refresh_voltage_label(value: float) -> void:
	var lbl: Label = get_node(voltage_value_label_path) as Label
	if lbl != null:
		lbl.text = "Voltage: %.2f V" % value


func _process(_delta: float) -> void:
	# Keep the sliders tracking the live state (e.g. after a reset, or if the
	# backend clamps a value), guarded by _sending to avoid feedback loops.
	if _state == null or _active_joint < 0:
		return
	var volt: float = float(_state.get("voltage_1")) if _active_joint == 0 else float(_state.get("voltage_2"))
	var v_slider: Range = get_node(voltage_slider_path) as Range
	if v_slider != null and abs(v_slider.value - volt) > 0.05:
		_sending = true
		v_slider.value = volt
		_sending = false
		_refresh_voltage_label(volt)
