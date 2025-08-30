set_default_segments(100)

sphere = Sphere(10)

add_object(sphere, material='glass')

sphere = sphere.translate([-15, 0, 0])
add_object(sphere, material='normal')

@add('checkerboard')
def gbox():
	return (Sphere(10) ^ (Box(5) + [10, 0, 0])) + [20, 0, 0]
