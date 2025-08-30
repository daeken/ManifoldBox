import manifold3d as m3d

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

def add(material='basic', name=None):
	def sub(func):
		add_object(func(), material=material, name=name or func.__name__)
		return func
	if isinstance(material, str):
		return sub
	else:
		func = material
		material = 'basic'
		return sub(func)

def rewrite_coords(x, y, z):
	if isinstance(x, int) or isinstance(x, float):
		y = x if y is None else y
		z = x if z is None else z
	else:
		assert y is None and z is None
		x, y, z = x
	return x, y, z

class O3D:
	def __init__(self, manifold):
		self.manifold = manifold

	def to_mesh(self):
		return self.manifold.to_mesh()

	def translate(self, x, y=None, z=None):
		return O3D(self.manifold.translate(rewrite_coords(x, y, z)))

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

class Box(O3D):
	def __init__(self, x, y=None, z=None, center=True):
		super().__init__(m3d.Manifold.cube(rewrite_coords(x, y, z), center=center))

class Sphere(O3D):
	def __init__(self, radius, segments=0):
		super().__init__(m3d.Manifold.sphere(radius, segments if segments != 0 else default_segments))

class Cylinder(O3D):
	pass

class O2D:
	pass

class Rectangle(O2D):
	pass

class Circle(O2D):
	pass
