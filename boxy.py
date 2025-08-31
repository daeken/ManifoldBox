import manifold3d as m3d
import numpy as np
import trimesh

objects = []

def add_object(obj, material='basic', name=None):
	objects.append((obj, material, name))

def clear_objects():
	global objects
	objects = []

is_compiling = False
default_segments = 0

def set_default_segments(n):
	global default_segments
	default_segments = n

def add(material='basic', name=None, uvMapper=None):
	def sub(func):
		obj = func()
		if uvMapper is not None:
			obj.uvMapper = uvMapper
		add_object(obj, material=material, name=name or func.__name__)
		return func
	if isinstance(material, str):
		return sub
	else:
		func = material
		material = 'basic'
		return sub(func)

def rewrite_coords(x, y=None, z=None):
	if isinstance(x, int) or isinstance(x, float):
		y = x if y is None else y
		z = x if z is None else z
	else:
		assert y is None and z is None
		x, y, z = x
	return x, y, z

def rewrite_coords2(x, y=None):
	if isinstance(x, int) or isinstance(x, float):
		return x, x if y is None else y
	else:
		assert y is None
		return x

def hull(*elems):
	if len(elems) == 1:
		elems = elems[0]
	if isinstance(elems[0], O3D) or isinstance(elems[0], m3d.Manifold):
		return O3D(m3d.Manifold.batch_hull([x.manifold if isinstance(x, O3D) else x for x in elems]))
	return O2D(m3d.CrossSection.batch_hull([x.crossSection if isinstance(x, O2D) else x for x in elems]))

def union(*elems):
	if len(elems) == 1:
		elems = elems[0]
	if isinstance(elems[0], O3D) or isinstance(elems[0], m3d.Manifold):
		return O3D(m3d.Manifold.batch_boolean([x.manifold if isinstance(x, O3D) else x for x in elems], m3d.OpType.Add))
	return O2D(m3d.CrossSection.batch_boolean([x.crossSection if isinstance(x, O2D) else x for x in elems], m3d.OpType.Add))

class O2D:
	def __init__(self, crossSection):
		self.crossSection = crossSection

	def translate(self, x, y=None):
		return O2D(self.crossSection.translate(rewrite_coords2(x, y)))

	def scale(self, x, y=None, z=None):
		return O2D(self.crossSection.scale(rewrite_coords2(x, y)))

	def __mul__(self, s):
		return self.scale(s)

	def __add__(self, right):
		if (isinstance(right, list) or isinstance(right, tuple)) and len(right) == 2 and (isinstance(right[0], int) or isinstance(right[0], float)):
			return self.translate(right)
		return O2D(self.crossSection + (right.crossSection if isinstance(right, O2D) else right))

	def __or__(self, right):
		return O2D(self.crossSection | (right.crossSection if isinstance(right, O2D) else right))

	def __sub__(self, right):
		if (isinstance(right, list) or isinstance(right, tuple)) and len(right) == 2 and (isinstance(right[0], int) or isinstance(right[0], float)):
			return self.translate(-right[0], -right[1])
		return O2D(self.crossSection - (right.crossSection if isinstance(right, O2D) else right))

	def __xor__(self, right):
		return O2D(self.crossSection ^ (right.crossSection if isinstance(right, O2D) else right))

	def revolve(self, degrees=360, segments=0, insideOut=False):
		obj = O3D(self.crossSection.revolve(segments if segments != 0 else default_segments, degrees))
		if insideOut:
			return obj.rotate(z=-(degrees / 2))
		return obj

	def rotate(self, degrees):
		return O2D(self.crossSection.rotate(degrees))

class Rectangle(O2D):
	def __init__(self, x, y=None, center=True):
		super().__init__(m3d.CrossSection.square(rewrite_coords2(x, y), center=center))

class RoundedRectangle(O2D):
	def __init__(self, cornerRadius, x, y=None, segments=0, center=True):
		x, y = rewrite_coords2(x, y)
		c = Circle(cornerRadius, segments=segments)
		corners = []
		if center:
			corners.append(c + [-x / 2 + cornerRadius, -y / 2 + cornerRadius])
			corners.append(c + [x / 2 - cornerRadius, -y / 2 + cornerRadius])
			corners.append(c + [-x / 2 + cornerRadius, y / 2 - cornerRadius])
			corners.append(c + [x / 2 - cornerRadius, y / 2 - cornerRadius])
		else:
			corners.append(c + [cornerRadius, cornerRadius])
			corners.append(c + [x - cornerRadius, cornerRadius])
			corners.append(c + [cornerRadius, y - cornerRadius])
			corners.append(c + [x - cornerRadius, y - cornerRadius])
		super().__init__(hull(corners).crossSection)

class Circle(O2D):
	def __init__(self, radius, segments=0):
		super().__init__(m3d.CrossSection.circle(radius, segments if segments != 0 else default_segments))

class O3D:
	def __init__(self, manifold):
		self.manifold = manifold
		self.uvMapper = uvBoxMap

	def to_mesh(self):
		return self.manifold.to_mesh()

	def translate(self, x, y=None, z=None):
		return O3D(self.manifold.translate(rewrite_coords(x, y, z)))

	def rotate(self, x=0, y=0, z=0):
		return O3D(self.manifold.rotate([x, y, z]))

	def scale(self, x, y=None, z=None):
		return O3D(self.manifold.scale(rewrite_coords(x, y, z)))

	def __mul__(self, s):
		return self.scale(s)

	def __add__(self, right):
		if (isinstance(right, list) or isinstance(right, tuple)) and len(right) == 3 and (isinstance(right[0], int) or isinstance(right[0], float)):
			return self.translate(right)
		return O3D(self.manifold + (right.manifold if isinstance(right, O3D) else right))

	def __or__(self, right):
		return O3D(self.manifold | (right.manifold if isinstance(right, O3D) else right))

	def __sub__(self, right):
		if (isinstance(right, list) or isinstance(right, tuple)) and len(right) == 3 and (isinstance(right[0], int) or isinstance(right[0], float)):
			return self.translate(-right[0], -right[1], -right[2])
		return O3D(self.manifold - (right.manifold if isinstance(right, O3D) else right))

	def __xor__(self, right):
		return O3D(self.manifold ^ (right.manifold if isinstance(right, O3D) else right))

	def refine(self, n):
		return O3D(self.manifold.refine(n))

class Box(O3D):
	def __init__(self, x, y=None, z=None, center=True):
		super().__init__(m3d.Manifold.cube(rewrite_coords(x, y, z), center=center))

class Sphere(O3D):
	def __init__(self, radius, segments=0):
		super().__init__(m3d.Manifold.sphere(radius, segments if segments != 0 else default_segments))

class Cylinder(O3D):
	def __init__(self, h, r1=None, r2=None, center=True, segments=0, d1=None, d2=None):
		if r1 is None:
			assert d1 is not None
			r1 = d1 / 2
			if r2 is None:
				r2 = d1 / 2 if d2 is None else d2 / 2
		super().__init__(m3d.Manifold.cylinder(h, r1, r1 if r2 is None else r2, segments if segments != 0 else default_segments, center))

def uvBoxMap(mesh):
	vertices = mesh.vertices
	faces = mesh.faces
	vertex_normals = mesh.vertex_normals if hasattr(mesh, 'vertex_normals') and mesh.vertex_normals is not None else None

	assert vertex_normals is not None
	
	# Calculate bounding box for normalization
	vmin = np.min(vertices, axis=0)
	vmax = np.max(vertices, axis=0)
	vrange = vmax - vmin
	
	# Avoid division by zero
	vrange = np.where(vrange == 0, 1, vrange)
	
	def gen_uv(vertex, normal):
		"""Generate UV coordinates for a vertex based on its normal (box unwrapping)"""
		# Normalize vertex to 0-1 range
		v = (vertex - vmin) / vrange
		
		# Create 2D projections
		xy = np.array([v[0], v[1]])  # X-Y plane
		yz = np.array([v[1], v[2]])  # Y-Z plane  
		xz = np.array([v[0], v[2]])  # X-Z plane
		
		# Find dominant normal axis
		abs_normal = np.abs(normal)
		max_component = np.max(abs_normal)
		
		# Create dominant axis normal
		if abs_normal[0] == max_component:  # X dominant
			dom_normal = np.array([np.sign(normal[0]), 0, 0])
		elif abs_normal[1] == max_component:  # Y dominant
			dom_normal = np.array([0, np.sign(normal[1]), 0])
		else:  # Z dominant
			dom_normal = np.array([0, 0, np.sign(normal[2])])
		
		# Blend projections based on dominant normal
		uv = xy * abs(dom_normal[2]) + yz * abs(dom_normal[0]) + xz * abs(dom_normal[1])
		
		return uv
	
	# Calculate UVs for each original vertex with area weighting from adjacent faces
	uvs = [[] for _ in vertices]
	
	for face in faces:
		# Get face vertices
		v0, v1, v2 = vertices[face]
		
		# Calculate face normal and area
		edge1 = v1 - v0
		edge2 = v2 - v0
		face_normal = np.cross(edge1, edge2)
		face_area = np.linalg.norm(face_normal) / 2.0
		
		if face_area > 0:
			face_normal = face_normal / (face_area * 2)  # Normalize
			
			# Generate UVs for each vertex of this face using face normal
			for vertex_idx in face:
				vertex = vertices[vertex_idx]
				uv = gen_uv(vertex, face_normal)
				uvs[vertex_idx].append((face_area, uv))
	
	# Calculate final UVs with area weighting
	vertex_uvs = np.zeros((len(vertices), 2))
	
	for i, uv_list in enumerate(uvs):
		if len(uv_list) == 0:
			vertex_uvs[i] = [0.0, 0.0]
		else:
			total_area = sum(area for area, _ in uv_list)
			if total_area > 0:
				u = sum(uv[0] * (area / total_area) for area, uv in uv_list)
				v = sum(uv[1] * (area / total_area) for area, uv in uv_list)
				vertex_uvs[i] = [u, v]
			else:
				vertex_uvs[i] = [0.0, 0.0]
	
	# Create a new mesh with the calculated UVs
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