extends Node

## Handles win → menu navigation. Lives on each level scene.

@export var win_panel_path: NodePath
@export var next_button_path: NodePath

func _ready() -> void:
	var bc: Node = get_node_or_null("/root/Bridge")
	if bc == null:
		return
	bc.connect("sim_state_received", _on_state)

func _on_state(state: Dictionary) -> void:
	var extras: Dictionary = state.get("extras", {})
	if not bool(extras.get("won", false)):
		return
	var panel: Control = get_node_or_null(win_panel_path)
	if panel != null:
		panel.visible = true
	var btn: Button = get_node_or_null(next_button_path)
	if btn != null and not btn.pressed.is_connected(_on_return):
		btn.pressed.connect(_on_return)

func _on_return() -> void:
	get_tree().change_scene_to_file("res://scenes/main.tscn")

func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_cancel"):
		get_tree().change_scene_to_file("res://scenes/main.tscn")
