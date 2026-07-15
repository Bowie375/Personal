extends Node3D

## Builds and drives the 2-link arm of Act 2.4 from two abstracted joints.
##
## The arm is planar, swinging in the XY plane (joint axes along Z), with the
## shoulder pivot at PIVOT_Y above the floor. Both joints hang straight down at
## q=0. Joint angles are RELATIVE (q1 = link 1 from straight down; q2 = link 2
## relative to link 1) — the real-robot convention, and what makes joint 1's
## load depend on joint 2 (the coupling the level teaches).
##
## Layout:
##
##     Shoulder (joint 0) at origin + PIVOT_Y
##       └─ Link1 pivot ── link 1 hangs down, rotates by q1
##          └─ Elbow (joint 1) at the end of link 1
##             └─ Link2 pivot ── link 2 hangs down from the elbow, rotates by q2
##                └─ Tip marker (FK end-effector)
##
## Links are translucent boxes (rod style) so the joints + target show through.
## Each link is built in WORLD units and parented to a scale-1.0 pivot so it
## doesn't inherit any scale (the 2.3 lesson).

@export var state_path: NodePath
@export var shoulder_path: NodePath  # MeshInstance3D w/ joint_visual.gd (id 0)
@export var elbow_path: NodePath  # MeshInstance3D w/ joint_visual.gd (id 1)
@export var link1_pivot_path: NodePath  # Node3D — rotates by q1
@export var link2_pivot_path: NodePath  # Node3D — rotates by q2 (child of link1)
@export var tip_marker_path: NodePath  # MeshInstance3D — the end-effector dot
@export var link_length: float = 1.4  # world units per link (matches rod scale)
@export var link_thickness: float = 0.06
@export var pivot_y: float = 1.0

var _state: Node
var _shoulder: MeshInstance3D
var _elbow: MeshInstance3D
var _link1_pivot: Node3D
var _link2_pivot: Node3D
var _tip: MeshInstance3D


func _ready() -> void:
	_state = get_node_or_null(state_path)
	_shoulder = get_node_or_null(shoulder_path) as MeshInstance3D
	_elbow = get_node_or_null(elbow_path) as MeshInstance3D
	_link1_pivot = get_node_or_null(link1_pivot_path) as Node3D
	_link2_pivot = get_node_or_null(link2_pivot_path) as Node3D
	_tip = get_node_or_null(tip_marker_path) as MeshInstance3D
	if _state == null or _link1_pivot == null or _link2_pivot == null:
		push_error("TwoLinkAssembly: missing state or pivots")
		return
	# Place the shoulder at the pivot; link 1 hangs straight down from it.
	_link1_pivot.position = Vector3(0.0, pivot_y, 0.0)
	# Link2Pivot's origin IS the link-1/link-2 intersection: it sits at the end
	# of link 1 (offset -link_length within link 1), and link 2 hangs down from
	# it. Rotating it by q2 swings link 2 about this intersection.
	_link2_pivot.position = Vector3(0.0, -link_length, 0.0)
	# The elbow joint housing must sit AT that intersection to drive link 2, so
	# as a child of Link2Pivot its local offset is zero (the pivot's origin).
	if _elbow != null:
		_elbow.position = Vector3(0.0, 0.0, 0.0)
	if _shoulder != null:
		_shoulder.position = Vector3(0.0, 0.0, 0.0)
	# The link meshes (rod_visual.gd) and tip marker live at -link_length too;
	# force their offsets to track link_length so the scene's static offsets
	# can't drift out of sync with the runtime value.
	if _tip != null:
		_tip.position = Vector3(0.0, -link_length, 0.0)
	var link1_mesh: MeshInstance3D = _link1_pivot.get_node_or_null("Link1")
	if link1_mesh != null and link1_mesh.get("world_length") != null:
		link1_mesh.world_length = link_length
		link1_mesh.world_thickness = link_thickness
	var link2_mesh: MeshInstance3D = _link2_pivot.get_node_or_null("Link2")
	if link2_mesh != null and link2_mesh.get("world_length") != null:
		link2_mesh.world_length = link_length
		link2_mesh.world_thickness = link_thickness
	if _state.has_signal("joint_changed"):
		_state.connect("joint_changed", _on_joint)
	if _shoulder != null and _shoulder.has_signal("joint_selected"):
		_shoulder.connect("joint_selected", _on_joint_selected)
	if _elbow != null and _elbow.has_signal("joint_selected"):
		_elbow.connect("joint_selected", _on_joint_selected)
	_update_pose()


func _process(_delta: float) -> void:
	_update_pose()


func _on_joint(jid: int, _rpm: float, _angle: float) -> void:
	if jid == 0 or jid == 1:
		_update_pose()


func _update_pose() -> void:
	if _state == null or _link1_pivot == null or _link2_pivot == null:
		return
	var q1: float = _joint_angle(0)
	var q2: float = _joint_angle(1)
	# Rotate each link pivot around world Z by its joint angle. Compose onto
	# Basis.from_scale(live_scale) to preserve scale (the 2.3 lesson).
	_link1_pivot.transform = _rotated_z(_link1_pivot, q1)
	_link2_pivot.transform = _rotated_z(_link2_pivot, q2)
	# The tip rides at the end of link 2 (a child of link2_pivot), so it is
	# positioned by the chain automatically; but we also place a world-space
	# tip marker from the backend's FK (joint id 2 carries tip_x/tip_y) so the
	# region check is the backend's, not the visuals'.


func _joint_angle(jid: int) -> float:
	var joints = _state.get("joints")
	if joints == null:
		return 0.0
	var j = joints.get(str(jid))
	if j == null:
		return 0.0
	return float(j.get("angle", 0.0))


func _rotated_z(pivot: Node3D, ang: float) -> Transform3D:
	var live_scale: Vector3 = pivot.transform.basis.get_scale()
	var spin := Quaternion(Vector3.BACK, ang)
	var basis := Basis(spin) * Basis.from_scale(live_scale)
	return Transform3D(basis, pivot.position)


func _on_joint_selected(jid: int) -> void:
	# Forward to a JointControlPanel if one is a sibling (the scene wires it).
	var panel = get_node_or_null("../JointControlPanel")
	if panel != null and panel.has_method("select_joint"):
		panel.select_joint(jid)
	if _shoulder != null:
		_shoulder.set_selected(jid == 0)
	if _elbow != null:
		_elbow.set_selected(jid == 1)
