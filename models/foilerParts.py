ogFoilThickness = 5.8
newFoilThickness = 5.1
hubHoleDiameter = 79 # new is 77.3
hubRimDiameter = 76 + 1 # added padding by vibes
hubRimThickness = 6
totalDepth = 12.71
postHoleDiameter = 11.36 + 0.5 # added additional padding because really, we need it
insideHubDiameter = 17.35
outsideHubDiameter = 18.25
outsideHubDepth = 5.55
plateThickness = 2.65 + 1.5 # added thickness by vibes
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
	guide = Cylinder(h=newFoilThickness, d1=overallDiameter - foilDepth * 1.5, center=False)
	topCone = Cylinder(h=halfSide, d1=overallDiameter, d2=bottomDiameter, center=False)
	stack = bottomCone + (guide + (topCone + [0, 0, newFoilThickness]) + [0, 0, halfSide])
	return stack - Cylinder(h=100, d1=postHoleDiameter)

@add('normal')
def foilGuideAlt():
	bottomCone = Cylinder(h=halfSide, d1=bottomDiameter, d2=overallDiameter, center=False)
	guideBottom = Cylinder(h=newFoilThickness / 2, d1=overallDiameter - foilDepth, d2=overallDiameter - foilDepth * 3, center=False)
	guideTop = Cylinder(h=newFoilThickness / 2, d1=overallDiameter - foilDepth * 3, d2=overallDiameter - foilDepth, center=False)
	topCone = Cylinder(h=halfSide, d1=overallDiameter, d2=bottomDiameter, center=False)
	stack = bottomCone + ((guideBottom + (guideTop + [0, 0, newFoilThickness / 2])) + (topCone + [0, 0, newFoilThickness]) + [0, 0, halfSide])
	return stack - Cylinder(h=100, d1=postHoleDiameter)

# these should always relate
hexSideToSide = 11
hexSideWidth = 6

nutHoleDiameter = 5.16 # this includes the threads
nutHeight = 6.34
baseHeight = 1.3
threads = 5
