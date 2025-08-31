import math

set_default_segments(100)

def donutUv(mesh):
	vertices = mesh.vertices
	faces = mesh.faces
	vertex_normals = mesh.vertex_normals if hasattr(mesh, 'vertex_normals') and mesh.vertex_normals is not None else None

	assert vertex_normals is not None

	angularOffset = math.pi * 2 / 360 * 0.5
	uFactor = math.pi * 2 / 360
	vertex_uvs = np.zeros((len(vertices), 2))
	minU = 10000000
	maxU = -10000000
	minV = 10000000
	maxV = -1000000
	for i, (x, y, z) in enumerate(vertices):
		ez = z + 16000
		theta = math.atan2(y, -z) # * (180 / math.pi)
		theta += angularOffset
		u = theta / uFactor * 280
		height = ez #math.sqrt(y * y + ez * ez)
		v = x + height
		minU = min(minU, u)
		maxU = max(maxU, u)
		minV = min(minV, v)
		maxV = max(maxV, v)
		vertex_uvs[i] = (u / 100, v / 100)

	#print(vertex_uvs)
	print(minU, maxU, minV, maxV)

	mesh_with_uvs = trimesh.Trimesh(
		vertices=vertices,
		faces=faces,
		vertex_normals=vertex_normals
	)
	
	# Add UV coordinates as vertex attributes
	mesh_with_uvs.vertex_attributes['uv'] = vertex_uvs
	
	# Copy over any existing visual properties
	if hasattr(mesh, 'visual'):
		mesh_with_uvs.visual = mesh.visual
	return mesh_with_uvs

hullThickness = 5

def flat_window(width, height, bezelHeight, bezelOverlap, bezelThickness):
	panel = Box(hullThickness, width, height, center=False)
	bezel = Box(bezelThickness, width + bezelHeight * 2, height + bezelHeight * 2, center=False)
	bezel -= Box(bezelThickness, width - bezelOverlap * 2, height - bezelOverlap * 2, center=False) + [0, bezelHeight + bezelOverlap, bezelHeight + bezelOverlap]
	bezel -= [0, bezelHeight, bezelHeight]
	bezels = (bezel - [bezelThickness, 0, 0]) + (bezel + [hullThickness, 0, 0])
	return panel, bezels

flatPane, flatBezel = flat_window(15, 14, 0.1, 0.05, 0.002)

def buildWindows(elem):
	elems = []
	for i in range(-8, 10):
		rot = -i / 18.25
		for j in range(4):
			elems.append((elem - [-255 + hullThickness, 0, 16000 - 0.5 - 0.25 * j - 14 * j]).rotate(x=rot))
			elems.append((elem - [255, 0, 16000 - 0.5 - 0.25 * j - 14 * j]).rotate(x=rot))
		for j in range(2):
			elems.append((elem - [-255 + hullThickness, 0, 16000 + 35 - 0.75 - 0.25 * j - 14 * j]).rotate(x=rot))
			elems.append((elem - [255, 0, 16000 + 35 - 0.75 - 0.25 * j - 14 * j]).rotate(x=rot))
	return elems

@add('glass')
def glass():
	return union(buildWindows(flatPane))

@add('checkerboard')
def bezels():
	return union(buildWindows(flatBezel))

@add('checkerboard', uvMapper=donutUv)
def superhull():
	width = 500
	height = 150
	roundness = 15
	cs = RoundedRectangle(roundness, width + hullThickness * 2, height + hullThickness * 2, center=True) - RoundedRectangle(roundness, width, height, center=True)
	sh = (cs.rotate(90) + [16000, 0]).revolve(1, insideOut=True).rotate(y=90)
	return sh - glass()

@add('checkerboard', uvMapper=donutUv)
def floors():
	cs = Rectangle(500, 5, center=True) - [0, 2.5]
	cs += Rectangle(500, 5, center=True) - [0, 2.5 + 5 + 30]
	obj = (cs.rotate(90) + [16000, 0]).revolve(1, insideOut=True).rotate(y=90)
	return obj# - superhull()
