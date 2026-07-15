extends Control

## HUD overlay for Act 2.4 (Two-Link Arm). Shows the tip position vs the target
## region, both joint angles, the win banner, and the diagnostic panel. The
## per-joint ratio + voltage live on the JointControlPanel (which binds to the
## clicked joint); this HUD is the read-only status strip.

@export var tip_label_path: NodePath
@export var target_label_path: NodePath
@export var joint1_angle_label_path: NodePath
@export var joint2_angle_label_path: NodePath
@export var in_region_label_path: NodePath
@export var diagnostic_panel_path: NodePath
@export var diagnostic_message_label_path: NodePath
@export var diagnostic_hint_label_path: NodePath
@export var win_panel_path: NodePath

var _state: Node


func bind(state: Node) -> void:
	_state = state
	if state.has_signal("diagnostic_changed"):
		state.connect("diagnostic_changed", _on_diagnostic)
	if state.has_signal("won_changed"):
		state.connect("won_changed", _on_won)
	if state.has_signal("joint_changed"):
		state.connect("joint_changed", _on_joint)


func _ready() -> void:
	# The HUD is a non-interactive status strip overlaid on the 3D scene. A
	# Control with STOP/PASS mouse_filter eats the click during the GUI input
	# phase, so Area3D._input_event (physics picking) never fires and the
	# clickable joints become unclickable. Make this panel and every
	# non-interactive child IGNORE so clicks fall through to the 3D scene.
	_make_click_through(self)
	var owner_node: Node = get_parent()
	if owner_node != null:
		var candidate: Node = owner_node.get_node_or_null("LevelState")
		if candidate != null and candidate.has_signal("won_changed"):
			bind(candidate)


func _make_click_through(node: Node) -> void:
	if node is Control:
		# Sliders / buttons keep their default STOP so they still capture their
		# own clicks; everything else (panels, containers, labels) lets clicks
		# pass through to the 3D scene behind.
		if not (node is Range or node is Button or node is OptionButton):
			node.mouse_filter = Control.MOUSE_FILTER_IGNORE
	for c in node.get_children():
		_make_click_through(c)


func _on_joint(joint_id: int, _rpm: float, _angle: float) -> void:
	if joint_id == 2:  # the FK tip pseudo-joint arrived
		_refresh_tip()


func _refresh_tip() -> void:
	if _state == null:
		return
	var tx: float = float(_state.get("tip_x")) if _state.get("tip_x") != null else 0.0
	var ty: float = float(_state.get("tip_y")) if _state.get("tip_y") != null else 0.0
	var tgx: float = float(_state.get("target_x")) if _state.get("target_x") != null else 0.0
	var tgy: float = float(_state.get("target_y")) if _state.get("target_y") != null else 0.0
	var in_region: bool = bool(_state.get("tip_in_region")) if _state.get("tip_in_region") != null else false
	var j1: float = rad_to_deg(float(_state.get("joint_angle_1")) if _state.get("joint_angle_1") != null else 0.0)
	var j2: float = rad_to_deg(float(_state.get("joint_angle_2")) if _state.get("joint_angle_2") != null else 0.0)
	var lbl: Label = get_node(tip_label_path) as Label
	if lbl != null:
		lbl.text = "Tip: (%.2f, %.2f)" % [tx, ty]
	var tlbl: Label = get_node(target_label_path) as Label
	if tlbl != null:
		tlbl.text = "Target: (%.2f, %.2f)" % [tgx, tgy]
	var j1lbl: Label = get_node(joint1_angle_label_path) as Label
	if j1lbl != null:
		j1lbl.text = "J1 (shoulder): %.1f°" % j1
	var j2lbl: Label = get_node(joint2_angle_label_path) as Label
	if j2lbl != null:
		j2lbl.text = "J2 (elbow): %.1f°" % j2
	var inlbl: Label = get_node(in_region_label_path) as Label
	if inlbl != null:
		inlbl.text = "In region: " + ("YES" if in_region else "no")
		inlbl.modulate = Color(0.4, 1.0, 0.4) if in_region else Color(1.0, 0.7, 0.5)


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


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("reset_level"):
		var bc: Node = get_node_or_null("/root/Bridge")
		if bc != null:
			bc.send_action("reset", {})
