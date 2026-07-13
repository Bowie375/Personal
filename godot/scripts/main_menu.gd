extends Control

## Main menu. Reads the player profile (Python side writes it; we read
## JSON from disk here) and lists unlocked levels.

const LEVELS: Array = [
	{"id": "1.1", "title": "Spinning Shaft", "scene": "res://scenes/level_1_1.tscn"},
	{"id": "1.2", "title": "Two Gears", "scene": "res://scenes/level_1_2.tscn"},
	{"id": "1.3", "title": "Idler Gear", "scene": "res://scenes/level_1_3.tscn"},
]
const PROFILE_PATH: String = "user://profile_mirror.json"  # Godot side mirror
const PYTHON_PROFILE: String = "/home/xiaobowen/.local/share/robot-forge/profile.json"

@onready var _levels_box: VBoxContainer = $VBox/Levels

func _ready() -> void:
	_refresh_profile_mirror()
	_rebuild_level_buttons()

func _refresh_profile_mirror() -> void:
	# Godot 4 can't import the Python profile directly. The Python session
	# emits an "init" payload right after registration; we read from
	# PYTHON_PROFILE if accessible, otherwise fall back to defaults.
	# For now: assume fresh profile (level 1.1 unlocked).
	if FileAccess.file_exists(PYTHON_PROFILE):
		var f: FileAccess = FileAccess.open(PYTHON_PROFILE, FileAccess.READ)
		if f != null:
			var txt: String = f.get_as_text()
			f.close()
			var f2: FileAccess = FileAccess.open(PROFILE_PATH, FileAccess.WRITE)
			if f2 != null:
				f2.store_string(txt)
				f2.close()

func _rebuild_level_buttons() -> void:
	for c in _levels_box.get_children():
		c.queue_free()
	var unlocked: Dictionary = _read_unlocked()
	for lvl in LEVELS:
		var btn: Button = Button.new()
		btn.text = "%s — %s" % [lvl["id"], lvl["title"]]
		btn.custom_minimum_size = Vector2(0, 48)
		btn.disabled = not unlocked.get(lvl["id"], false)
		var scene_path: String = lvl["scene"]
		btn.pressed.connect(func() -> void: _launch(scene_path))
		_levels_box.add_child(btn)

func _read_unlocked() -> Dictionary:
	# Default: 1.1 unlocked.
	var unlocked: Dictionary = {"1.1": true}
	if not FileAccess.file_exists(PROFILE_PATH):
		return unlocked
	var f: FileAccess = FileAccess.open(PROFILE_PATH, FileAccess.READ)
	if f == null:
		return unlocked
	var raw: String = f.get_as_text()
	f.close()
	var parsed: Variant = JSON.parse_string(raw)
	if parsed is Dictionary:
		var arr: Array = parsed.get("unlocked", [])
		for id in arr:
			unlocked[str(id)] = true
	return unlocked

func _launch(scene_path: String) -> void:
	get_tree().change_scene_to_file(scene_path)
