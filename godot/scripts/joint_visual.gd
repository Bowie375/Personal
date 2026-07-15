extends MeshInstance3D

## An abstracted joint (gearbox housing) of Act 2.4 — a small cylinder along
## the joint axis at a pivot. The gearbox is no longer drawn as visible gears:
## it is a black-box ACTUATOR. The two levers the player has tuned since 1.1
## (reduction ratio + motor voltage) are now exposed on a control panel that
## pops up when the joint is clicked.
##
## Clickability: an Area3D with a sphere collider (orientation-agnostic)
## catches the mouse; clicking emits `joint_selected(id)`. The scene positions
## this node; this script builds the mesh + the collider.

signal joint_selected(joint_id: int)

@export var joint_id: int = 0
@export var housing_radius: float = 0.12
@export var housing_height: float = 0.16
@export var housing_color: Color = Color(0.7, 0.7, 0.75, 1.0)
@export var highlight_color: Color = Color(1.0, 0.85, 0.3, 1.0)


func _ready() -> void:
	_build_housing()


func _build_housing() -> void:
	# A short cylinder — the joint "knob". The planar arm spins around world Z,
	# so the housing's long axis is along Z: bake that by giving the instance a
	# 90° rotation around X (CylinderMesh is along Y by default). We compose
	# onto the scene's transform so the scene can still place the pivot.
	var cyl := CylinderMesh.new()
	cyl.top_radius = housing_radius
	cyl.bottom_radius = housing_radius
	cyl.height = housing_height
	mesh = cyl
	var mat := StandardMaterial3D.new()
	mat.albedo_color = housing_color
	mat.roughness = 0.5
	mat.metallic = 0.3
	material_override = mat
	# Orient the housing's long axis along Z (the joint axis). Apply ONLY the
	# basis (rotation), preserving the node's existing position so a parent
	# (e.g. the arm assembly) can position this joint freely — don't bake the
	# position into a static transform that would fight later position writes.
	var pos := transform.origin
	transform = Transform3D(Basis(Vector3.RIGHT, PI / 2.0), pos)
	# Clickable collider: a sphere so it works from any view angle without
	# needing to match the cylinder's orientation.
	var area := Area3D.new()
	var col := CollisionShape3D.new()
	var shape := SphereShape3D.new()
	shape.radius = housing_radius * 1.5
	col.shape = shape
	area.add_child(col)
	area.transform = Transform3D(Basis(), Vector3.ZERO)
	area.connect("input_event", _on_input_event)
	add_child(area)


func set_selected(selected: bool) -> void:
	var mat := material_override as StandardMaterial3D
	if mat != null:
		mat.albedo_color = highlight_color if selected else housing_color


func _on_input_event(
	_camera: Camera3D, event: InputEvent, _pos: Vector3, _normal: Vector3, _shape_idx: int
) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		joint_selected.emit(joint_id)
