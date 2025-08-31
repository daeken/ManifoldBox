ogFoilThickness = 5.8
newFoilThickness = 5.1
hubHoleDiameter = 79 # new is 77.3
hubRimDiameter = 76
hubRimThickness = 6
totalDepth = 12.71
postHoleDiameter = 11.36
insideHubDiameter = 17.35
outsideHubDiameter = 18.25
outsideHubDepth = 5.55
plateThickness = 2.65
plateDiameter = 133

set_default_segments(360)

@add('normal')
def foilHolder():
	plate = Cylinder(h=plateThickness, d1=plateDiameter, center=False)
	foilHub = Cylinder(h=newFoilThickness, d1=hubRimDiameter, center=False) - Cylinder(h=newFoilThickness, d1=hubRimDiameter - hubRimThickness, center=False)
	innerHub = Cylinder(h=newFoilThickness, d1=insideHubDiameter, center=False)
	hub = foilHub + innerHub
	full = plate + (hub + [0, 0, plateThickness])
	return full - Cylinder(h=100, d1=postHoleDiameter)

totalThickness = 18
foilDepth = 1.19
overallDiameter = 45.5
# same post hole diameter
halfSide = (totalThickness - ogFoilThickness) / 2
bottomDiameter = 33

@add('normal')
def foilGuide():
	bottomCone = Cylinder(h=halfSide, d1=bottomDiameter, d2=overallDiameter, center=False)
	guide = Cylinder(h=newFoilThickness, d1=overallDiameter - foilDepth, center=False)
	topCone = Cylinder(h=halfSide, d1=overallDiameter, d2=bottomDiameter, center=False)
	stack = bottomCone + (guide + (topCone + [0, 0, newFoilThickness]) + [0, 0, halfSide])
	return stack - Cylinder(h=100, d1=postHoleDiameter)
