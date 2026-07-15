extends Control

## HUD overlay for Act 2.3 (First Joint, planetary). Voltage slider, sun/ring
## gear selectors (planet DERIVED, shown read-only like 2.2), a mode selector
## (ring_fixed is the winning config), an ANGLE readout (the rod's settled
## angle vs the 45° target — this level's win target, not RPM), ratio, the
## not-assemblable banner, and diagnostic + win panels.
##
## No load slider (gravity is the load, fixed). The angle bar spans 0..90°
## (rod from straight-down to horizontal).

@export var voltage_slider_path: NodePath
@export var voltage_value_label_path: NodePath
@export var sun_select_path: NodePath
@export var ring_select_path: NodePath
@export var planet_label_path: NodePath  # read-only: planet derived from sun+ring
@export var mode_select_path: NodePath
@export var angle_label_path: NodePath
@export var target_angle_label_path: NodePath
@export var angle_bar_path: NodePath
@export var target_marker_path: NodePath
@export var ratio_value_label_path: NodePath
@export var assemble_banner_path: NodePath
@export var mesh_status_label_path: NodePath
@export var diagnostic_panel_path: NodePath
@export var diagnostic_message_label_path: NodePath
@export var diagnostic_hint_label_path: NodePath
@export var win_panel_path: NodePath

var _state: Node
var _max_voltage: float = 24.0
var _sending: bool = false
const TEETH_OPTIONS: Array = [12, 16, 20, 24, 30, 36, 40, 48, 60]
const MODE_IDS: Array = ["ring_fixed", "sun_fixed", "carrier_fixed"]
const MODE_LABELS: Array = [
	"Ring fixed (sun→carrier) [win]",
	"Sun fixed (can't drive via sun)",
	"Carrier fixed (reversing)",
]
const ANGLE_BAR_RANGE: float = 90.0
const DEFAULT_TEETH_SUN: int = 12
const DEFAULT_TEETH_RING: int = 60


func bind(state: Node) -> void:
	_state = state
	if state.has_signal("voltage_changed"):
		state.connect("voltage_changed", _on_voltage_remote)
	if state.has_signal("planetary_gears_changed"):
		state.connect("planetary_gears_changed", _on_gears)
	if state.has_signal("mode_changed"):
		state.connect("mode_changed", _on_mode)
	if state.has_signal("assemblable_changed"):
		state.connect("assemblable_changed", _on_assemblable)
	if state.has_signal("meshed_changed"):
		state.connect("meshed_changed", _on_meshed)
	if state.has_signal("diagnostic_changed"):
		state.connect("diagnostic_changed", _on_diagnostic)
	if state.has_signal("won_changed"):
		state.connect("won_changed", _on_won)
	if state.has_signal("joint_changed"):
		state.connect("joint_changed", _on_joint)
	# Prime.
	_on_gears(state.teeth_sun, state.teeth_planet, state.teeth_ring)
	_on_mode(state.mode)
	_on_assemblable(state.assemblable)
	_on_meshed(state.meshed)
	_on_voltage_remote(state.last_voltage)
	_refresh_angle()


func _ready() -> void:
	var v_slider: Range = get_node(voltage_slider_path) as Range
	if v_slider != null:
		v_slider.max_value = _max_voltage
		v_slider.min_value = 0.0  # 2.3 only lifts (positive voltage)
		v_slider.step = 0.05
		v_slider.value_changed.connect(_on_voltage_slider)
	_refresh_voltage_label(v_slider.value if v_slider else 0.0)
	_populate_gear_select(get_node(sun_select_path))
	_populate_gear_select(get_node(ring_select_path))
	var ssel: OptionButton = get_node(sun_select_path) as OptionButton
	var rsel: OptionButton = get_node(ring_select_path) as OptionButton
	if ssel != null:
		ssel.item_selected.connect(_on_sun_picked)
	if rsel != null:
		rsel.item_selected.connect(_on_ring_picked)
	# Mode selector.
	var mob: OptionButton = get_node(mode_select_path) as OptionButton
	if mob != null:
		mob.clear()
		for lbl in MODE_LABELS:
			mob.add_item(lbl)
		mob.selected = 0
		mob.item_selected.connect(_on_mode_picked)
	# Default selectors to the level's default set (sun N12 / ring N60).
	_select_teeth(ssel, DEFAULT_TEETH_SUN)
	_select_teeth(rsel, DEFAULT_TEETH_RING)
	# Angle bar spans 0..90°.
	var abar: Range = get_node(angle_bar_path) as Range
	if abar != null:
		abar.max_value = ANGLE_BAR_RANGE
		abar.min_value = 0.0
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


func _select_teeth(select: OptionButton, teeth: int) -> void:
	if select == null:
		return
	var idx: int = TEETH_OPTIONS.find(teeth)
	if idx >= 0:
		select.selected = idx


func _on_sun_picked(_idx: int) -> void:
	_send_gears()


func _on_ring_picked(_idx: int) -> void:
	_send_gears()


func _send_gears() -> void:
	var ssel: OptionButton = get_node(sun_select_path) as OptionButton
	var rsel: OptionButton = get_node(ring_select_path) as OptionButton
	if ssel == null or rsel == null:
		return
	var sun: int = int(ssel.get_selected_id())
	var ring: int = int(rsel.get_selected_id())
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


func _on_voltage_remote(value: float) -> void:
	var v_slider: Range = get_node(voltage_slider_path) as Range
	if v_slider != null and abs(v_slider.value - value) > 0.05:
		_sending = true
		v_slider.value = value
		_sending = false
	_refresh_voltage_label(value)


func _on_gears(sun: int, planet: int, ring: int) -> void:
	if sun > 0:
		_select_teeth(get_node(sun_select_path) as OptionButton, sun)
	if ring > 0:
		_select_teeth(get_node(ring_select_path) as OptionButton, ring)
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


func _on_joint(joint_id: int, _rpm: float, _angle: float) -> void:
	if joint_id == 1:  # the carrier = the rod
		_refresh_angle()


func _refresh_angle() -> void:
	if _state == null:
		return
	# _state is a Node (Object); .get() takes ONE arg. Guard null before float().
	var la_raw = _state.get("link_angle")
	var ta_raw = _state.get("target_angle")
	var angle_deg: float = rad_to_deg(float(la_raw) if la_raw != null else 0.0)
	var target_deg: float = rad_to_deg(float(ta_raw) if ta_raw != null else 0.0)
	var lbl: Label = get_node(angle_label_path) as Label
	if lbl != null:
		lbl.text = "Rod: %.1f°" % angle_deg
	var tlbl: Label = get_node(target_angle_label_path) as Label
	if tlbl != null:
		tlbl.text = "Target: %.1f°" % target_deg
	var bar: Range = get_node(angle_bar_path) as Range
	if bar != null:
		bar.value = clamp(angle_deg, 0.0, ANGLE_BAR_RANGE)
	var marker: Control = get_node(target_marker_path) as Control
	if marker != null and bar != null:
		var frac: float = clamp(target_deg / ANGLE_BAR_RANGE, 0.0, 1.0)
		marker.position.x = bar.position.x + bar.size.x * frac


func _refresh_ratio() -> void:
	var ratio_lbl: Label = get_node(ratio_value_label_path) as Label
	if ratio_lbl == null or _state == null:
		return
	var rr_raw = _state.get("reduction_ratio")  # set by level_state from extras? No
	# — reduction_ratio isn't a level_state var. Read from the summary extras
	# via teeth + mode. The HUD computes it from the cached teeth + mode.
	var sun: int = int(_state.get("teeth_sun")) if _state.get("teeth_sun") != null else 0
	var ring: int = int(_state.get("teeth_ring")) if _state.get("teeth_ring") != null else 0
	var mode: String = str(_state.get("mode"))
	if sun > 0 and ring > 0:
		var ratio: float
		if mode == "carrier_fixed":
			ratio = -float(ring) / float(sun)
		else:
			ratio = 1.0 + float(ring) / float(sun)
		ratio_lbl.text = "%.2f:1 (%s)" % [abs(ratio), mode]


func _on_assemblable(assemblable: bool) -> void:
	var banner: Control = get_node_or_null(assemble_banner_path) as Control
	if banner != null:
		banner.visible = not assemblable


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
		lbl.text = "Voltage: %.2f V" % value


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("torque_up"):
		_bump_voltage(0.25)
	elif event.is_action_pressed("torque_down"):
		_bump_voltage(-0.25)
	elif event.is_action_pressed("reset_level"):
		var bc: Node = get_node_or_null("/root/Bridge")
		if bc != null:
			bc.send_action("reset", {})


func _bump_voltage(delta: float) -> void:
	var v_slider: Range = get_node(voltage_slider_path) as Range
	if v_slider != null:
		v_slider.value = clamp(v_slider.value + delta, 0.0, _max_voltage)
