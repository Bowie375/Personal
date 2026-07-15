extends Control

## HUD overlay for Act 2.2 (planetary gearbox): voltage slider, load slider,
## TWO gear selectors (sun / ring — the planet is DERIVED from N_ring =
## N_sun + 2*N_planet and shown as a read-only label), a 3-way MODE selector
## (ground ring / ground sun / ground carrier), ratio readout (mode formula vs
## target), RPM gauges (sun/carrier/ring), torque readouts, stall +
## not-assemblable banners, diagnostic + win panels.
##
## The teaching pivot: the SAME gears give three ratios depending on which
## member is grounded. Switching the mode live-updates the ratio readout and
## which member is the output.

@export var voltage_slider_path: NodePath
@export var voltage_value_label_path: NodePath
@export var load_slider_path: NodePath
@export var load_value_label_path: NodePath
@export var target_load_label_path: NodePath
@export var sun_select_path: NodePath
@export var ring_select_path: NodePath
@export var planet_label_path: NodePath  # read-only: planet is DERIVED from sun+ring
@export var mode_select_path: NodePath
@export var ratio_value_label_path: NodePath
@export var target_ratio_label_path: NodePath
@export var sun_rpm_label_path: NodePath
@export var carrier_rpm_label_path: NodePath
@export var ring_rpm_label_path: NodePath
@export var target_value_label_path: NodePath
@export var sun_bar_path: NodePath
@export var carrier_bar_path: NodePath
@export var ring_bar_path: NodePath
@export var target_marker_path: NodePath
@export var output_torque_label_path: NodePath
@export var motor_side_load_label_path: NodePath
@export var stall_banner_path: NodePath
@export var assemble_banner_path: NodePath
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
# Mode labels in the OptionButton (index -> mode id sent to the backend).
const MODE_IDS: Array = ["ring_fixed", "sun_fixed", "carrier_fixed"]
const MODE_LABELS: Array = ["Ring fixed (sun→carrier)", "Sun fixed (ring→carrier)", "Carrier fixed (sun→ring, reversing)"]

func bind(state: Node) -> void:
	_state = state
	state.connect("voltage_changed", _on_voltage_remote)
	state.connect("load_changed", _on_load_remote)
	state.connect("target_load_changed", _on_target_load)
	state.connect("stall_changed", _on_stall)
	state.connect("assemblable_changed", _on_assemblable)
	state.connect("target_changed", _on_target)
	state.connect("target_sign_changed", _on_target_sign)
	state.connect("planetary_gears_changed", _on_gears)
	state.connect("mode_changed", _on_mode)
	state.connect("meshed_changed", _on_meshed)
	state.connect("diagnostic_changed", _on_diagnostic)
	state.connect("won_changed", _on_won)
	state.connect("joint_changed", _on_joint)
	# Prime.
	_on_target(state.target_rpm)
	_on_gears(state.teeth_sun, state.teeth_planet, state.teeth_ring)
	_on_mode(state.mode)
	_on_assemblable(state.assemblable)
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
	for p in [sun_select_path, ring_select_path]:
		_populate_gear_select(get_node(p))
	for path in [sun_select_path, ring_select_path]:
		var ob: OptionButton = get_node(path) as OptionButton
		if ob != null:
			ob.item_selected.connect(_on_gear_picked)
	# Mode selector: 3 fixed options.
	var mode_ob: OptionButton = get_node(mode_select_path) as OptionButton
	if mode_ob != null:
		mode_ob.clear()
		for lbl in MODE_LABELS:
			mode_ob.add_item(lbl)
		mode_ob.selected = 0
		mode_ob.item_selected.connect(_on_mode_picked)
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
	var sun: int = int((get_node(sun_select_path) as OptionButton).get_selected_id())
	var ring: int = int((get_node(ring_select_path) as OptionButton).get_selected_id())
	var bc: Node = get_node_or_null("/root/Bridge")
	if bc != null:
		# The planet is derived by the backend from N_ring = N_sun + 2*N_planet.
		bc.send_action("set_gears", {"sun": sun, "ring": ring})

func _on_mode_picked(idx: int) -> void:
	var mode: String = MODE_IDS[idx] if idx >= 0 and idx < MODE_IDS.size() else "ring_fixed"
	var bc: Node = get_node_or_null("/root/Bridge")
	if bc != null:
		bc.send_action("set_mode", {"mode": mode})

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

func _on_assemblable(assemblable: bool) -> void:
	var banner: Control = get_node_or_null(assemble_banner_path) as Control
	if banner != null:
		banner.visible = not assemblable

func _on_joint(joint_id: int, rpm: float, _angle: float) -> void:
	if joint_id == 0:
		_set_bar(get_node(sun_rpm_label_path), get_node(sun_bar_path), rpm)
	elif joint_id == 1:
		_set_bar(get_node(carrier_rpm_label_path), get_node(carrier_bar_path), rpm)
	elif joint_id == 2:
		_set_bar(get_node(ring_rpm_label_path), get_node(ring_bar_path), rpm)
	_update_torque()

func _set_bar(lbl: Label, bar: ProgressBar, rpm: float) -> void:
	if bar != null:
		bar.max_value = _max_rpm
		bar.value = clamp(abs(rpm), 0.0, _max_rpm)
	if lbl != null:
		var arrow: String = "→" if rpm > 0.1 else ("←" if rpm < -0.1 else "·")
		lbl.text = "%s %.1f RPM" % [arrow, abs(rpm)]

func _on_target(target: float) -> void:
	_max_rpm = max(120.0, target * 8.0)  # sun spins ratio× faster; room to show it
	var marker: Control = get_node(target_marker_path) as Control
	var obar: ProgressBar = get_node(carrier_bar_path) as ProgressBar
	if marker != null and obar != null:
		var frac: float = clamp(target / _max_rpm, 0.0, 1.0)
		marker.position.x = obar.position.x + obar.size.x * frac
	var t: Label = get_node(target_value_label_path) as Label
	if t != null:
		t.text = "Target: %.0f RPM" % target

func _on_target_sign(_sign: int) -> void:
	pass

func _on_gears(sun: int, planet: int, ring: int) -> void:
	if sun > 0:
		_select_teeth(sun_select_path, sun)
	if ring > 0:
		_select_teeth(ring_select_path, ring)
	# The planet is derived (not chosen); show it as a read-only label.
	if planet > 0:
		var plbl: Label = get_node_or_null(planet_label_path) as Label
		if plbl != null:
			plbl.text = "Planet: N%d (derived)" % planet
	_refresh_ratio()

func _on_mode(mode: String) -> void:
	var idx: int = MODE_IDS.find(mode)
	if idx >= 0:
		var ob: OptionButton = get_node(mode_select_path) as OptionButton
		if ob != null and ob.selected != idx:
			_sending = true
			ob.selected = idx
			_sending = false
	_refresh_ratio()

func _refresh_ratio() -> void:
	if _state == null:
		return
	var sun: int = int(_state.get("teeth_sun"))
	var ring: int = int(_state.get("teeth_ring"))
	var mode: String = str(_state.get("mode"))
	if sun <= 0 or ring <= 0:
		return
	var ratio: float = 0.0
	var formula: String = ""
	match mode:
		"ring_fixed":
			ratio = 1.0 + float(ring) / float(sun)
			formula = "1 + %d/%d = %.2f" % [ring, sun, ratio]
		"sun_fixed":
			ratio = 1.0 + float(sun) / float(ring)
			formula = "1 + %d/%d = %.2f" % [sun, ring, ratio]
		"carrier_fixed":
			ratio = -float(ring) / float(sun)
			formula = "-%d/%d = %.2f (reversing)" % [ring, sun, ratio]
		_:
			formula = "?"
	var lbl: Label = get_node(ratio_value_label_path) as Label
	if lbl != null:
		lbl.text = formula
	var tgt_lbl: Label = get_node(target_ratio_label_path) as Label
	if tgt_lbl != null:
		var tr: float = float(_state.get("target_ratio")) if _state.get("target_ratio") != null else 0.0
		tgt_lbl.text = "Target: %.1f:1" % tr

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

func _on_meshed(_meshed: bool) -> void:
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
