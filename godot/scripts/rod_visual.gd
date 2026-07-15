extends MeshInstance3D

## The rod (joint arm) of Act 2.3 — a rigid link fixed to the planetary's
## CARRIER, hanging straight down at angle 0 and swinging up as the gearbox
## lifts it against gravity.
##
## Translucent (alpha ~0.45) so the player can see the gears turning behind it:
## the rod is the moving part the player watches, but the planetary (sun +
## planets + ring) is the mechanism, and it must stay visible through the rod.
##
## The rod is parented to a pivot (the carrier node, positioned by the
## assembly); this script builds the MESH only. The pivot's rotation (joint id 1
## = carrier angle) is driven by the assembly, so the rod swings with the joint.
##
## IMPORTANT — the mesh is built directly in WORLD units at `world_length`
## (default 0.7, ≈ the ring radius). Do NOT rely on the pivot's scale for the
## rod's length: the earlier version scaled a normalized mesh by
## ROD_LENGTH * VISUAL_SCALE = 0.012 world units, making the rod an invisible
## speck next to the 0.9-world-unit ring. The pivot only carries ROTATION (no
## scale), and the rod's own geometry carries its real length.

@export var world_length: float = 1.4
# Cross-section (world units) — thick enough to be unmistakably visible.
@export var world_thickness: float = 0.06
@export var rod_color: Color = Color(0.6, 0.72, 0.95, 0.45)


func _ready() -> void:
	_build_rod()


func _build_rod() -> void:
	# A thin translucent box laid along -Y (the top end at the pivot y=0, the rod
	# hanging DOWN). Length = world_length, cross-section = world_thickness.
	var st: SurfaceTool = SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var w: float = world_thickness * 0.5
	var y_top: float = 0.0
	var y_bot: float = -world_length
	# Eight corners.
	var v000: Vector3 = Vector3(-w, y_bot, -w)
	var v001: Vector3 = Vector3(-w, y_bot, w)
	var v010: Vector3 = Vector3(-w, y_top, -w)
	var v011: Vector3 = Vector3(-w, y_top, w)
	var v100: Vector3 = Vector3(w, y_bot, -w)
	var v101: Vector3 = Vector3(w, y_bot, w)
	var v110: Vector3 = Vector3(w, y_top, -w)
	var v111: Vector3 = Vector3(w, y_top, w)

	var n_down: Vector3 = Vector3(0, -1, 0)
	var n_up: Vector3 = Vector3(0, 1, 0)
	var n_left: Vector3 = Vector3(-1, 0, 0)
	var n_right: Vector3 = Vector3(1, 0, 0)
	var n_back: Vector3 = Vector3(0, 0, -1)
	var n_fwd: Vector3 = Vector3(0, 0, 1)

	# Bottom face (-Y, points down — the rod tip).
	_add_quad(st, v100, v000, v001, v101, n_down)
	# Top face (+Y, points up — at the pivot).
	_add_quad(st, v010, v110, v111, v011, n_up)
	# -X face.
	_add_quad(st, v000, v010, v011, v001, n_left)
	# +X face.
	_add_quad(st, v110, v100, v101, v111, n_right)
	# -Z face.
	_add_quad(st, v000, v100, v110, v010, n_back)
	# +Z face.
	_add_quad(st, v001, v011, v111, v101, n_fwd)

	st.index()
	st.generate_normals()
	mesh = st.commit()

	# Translucent material: see-through so the planetary shows behind it. Alpha
	# 0.45 — visible but you can clearly see the gears through it.
	var mat: StandardMaterial3D = StandardMaterial3D.new()
	mat.albedo_color = rod_color
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.roughness = 0.4
	mat.metallic = 0.0
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL
	material_override = mat


func _add_quad(st: SurfaceTool, a: Vector3, b: Vector3, c: Vector3, d: Vector3, n: Vector3) -> void:
	st.set_normal(n)
	st.add_vertex(a)
	st.set_normal(n)
	st.add_vertex(b)
	st.set_normal(n)
	st.add_vertex(c)
	st.set_normal(n)
	st.add_vertex(a)
	st.set_normal(n)
	st.add_vertex(c)
	st.set_normal(n)
	st.add_vertex(d)
