set_default_segments(100)

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

@add('basic')
def bezels():
	return union(buildWindows(flatBezel))

@add('normal')
def superhull():
	width = 500
	height = 150
	roundness = 15
	cs = RoundedRectangle(roundness, width + hullThickness * 2, height + hullThickness * 2, center=True) - RoundedRectangle(roundness, width, height, center=True)
	sh = (cs.rotate(90) + [16000, 0]).revolve(1, insideOut=True).rotate(y=90)
	return sh - glass()

@add('normal')
def floors():
	cs = Rectangle(500, 5, center=True) - [0, 2.5]
	cs += Rectangle(500, 5, center=True) - [0, 2.5 + 5 + 30]
	obj = (cs.rotate(90) + [16000, 0]).revolve(1, insideOut=True).rotate(y=90)
	return obj# - superhull()

#@add('normal')
def cyltest():
	return Cylinder(100, 10)

#@add('checkerboard')
def gbox():
	return (Sphere(10) ^ (Box(5) + [10, 0, 0])) * [5, 3, 3] + [10, 0, 0]
