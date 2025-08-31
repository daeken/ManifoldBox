# ManifoldBox

A 3D model compiler and real-time viewer that executes Python scripts to generate 3D models using manifold3d. Features both interactive web-based development and command-line export capabilities.

## Features

- **Dual-Mode Operation**: Interactive web viewer for development + CLI export for production
- **Live Python Script Execution**: Watch files for changes with automatic recompilation
- **Advanced 3D Viewer**: Z-up coordinate system with smart camera positioning and controls
- **Multiple Export Formats**: STL, OBJ, and GLB with full material support
- **Powerful DSL**: High-level `boxy.py` modeling language with 2D/3D primitives
- **Material System**: PBR materials (basic, normal, checkerboard, glass) with double-sided rendering
- **Large Object Support**: Handles models with thousands of units and automatic scaling

## Quick Start

### Interactive Development

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Run with an example:
   ```bash
   python main.py --file models/foilerParts.py
   ```

3. Open http://localhost:8000 in your browser

4. Edit the script and see live updates

### Command-Line Export

```bash
# Export to single file
python main.py --export models/donut.py --output spaceship.glb

# Export each named object to separate files
python main.py --export models/foilerParts.py --output parts%.stl
```

## Viewer Controls

- **WASD + Shift/Space**: Camera movement (speed auto-scales with object size)
- **Mouse drag**: Camera rotation (with pointer lock and separate X/Y sensitivity)
- **P**: Toggle perspective/orthographic cameras
- **O**: Toggle wireframe mode  
- **[ ]**: Adjust movement speed scaling

## Example Scripts

### Basic Shapes (example.py)
```python
# Create geometric objects with materials
sphere = m3d.Manifold.sphere(1.0, 32)
metal_cylinder = m3d.Manifold.cylinder(0.5, 0.5, 2.0, 16)
glass_cube = m3d.Manifold.cube([1.0, 1.0, 1.0])

add_object(sphere)
add_object(metal_cylinder.translate([5, 0, 0]), material='metal')
add_object(glass_cube.translate([-5, 0, 0]), material='glass')
```

### Advanced Modeling (models/foilerParts.py)
```python
# Parametric design with precise dimensions
@add('normal')
def foilHolder():
    plate = Cylinder(h=plateThickness, d1=plateDiameter, center=False)
    foilHub = Cylinder(h=newFoilThickness, d1=hubRimDiameter, center=False) - \
              Cylinder(h=newFoilThickness, d1=hubRimDiameter - hubRimThickness, center=False)
    return (plate + hub) - Cylinder(h=100, d1=postHoleDiameter)
```

### 2D Revolution (models/donut.py)
```python
# Create complex shapes using 2D primitives
@add('glass')
def windows():
    panel = Box(hullThickness, width, height, center=False)
    return union(buildWindows(panel))

@add('normal') 
def superhull():
    cs = RoundedRectangle(roundness, width, height, center=True)
    return (cs.rotate(90) + [16000, 0]).revolve(1, insideOut=True).rotate(y=90)
```

## Export Formats

- **STL**: Perfect for 3D printing (single or multi-part)
- **OBJ**: Standard mesh format with material support  
- **GLB**: Full-featured with materials, normals, and UV mapping
- **Separate Files**: Use `%` in filename to export each named object individually

## Architecture

- **FastAPI**: Web server and API endpoints
- **manifold3d**: Robust 3D geometry processing
- **trimesh**: Mesh processing, normal calculation, and export
- **Three.js**: Hardware-accelerated 3D rendering with PBR materials
- **boxy.py DSL**: High-level modeling language with 2D/3D primitives

## Advanced Features

- **Smart Camera**: Only repositions on significant model changes (>10% volume change)
- **Proportional Movement**: Camera speed scales automatically with object size
- **Extended Precision**: Handles objects up to 1,000,000 units
- **Double-Sided Materials**: All surfaces render properly from any angle
- **Named Object Export**: Organize complex models with automatic file separation