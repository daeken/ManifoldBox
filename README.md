# ManifoldBox

A 3D model compiler and real-time viewer that executes Python scripts to generate 3D models using manifold3d and displays them in a web-based viewer.

## Features

- **Live Python Script Execution**: Watch Python files for changes and automatically recompile 3D models
- **Interactive 3D Viewer**: Web-based viewer with perspective/orthographic cameras and full navigation
- **Material System**: Support for multiple material types (basic, normal, checkerboard, glass)
- **High-Level DSL**: `boxy.py` provides intuitive 3D modeling primitives and operations
- **Real-Time Updates**: WebSocket-based live reloading when scripts change

## Quick Start

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Run with an example:
   ```bash
   python main.py --file models/donut.py
   ```

3. Open http://localhost:8000 in your browser

4. Edit `models/donut.py` and see live updates in the viewer

## Controls

- **WASD + Shift/Space**: Move camera
- **Mouse drag**: Rotate view  
- **P**: Toggle perspective/orthographic camera
- **O**: Toggle wireframe mode

## Example Script

```python
# Create geometric objects with materials
sphere = Sphere(10)
add_object(sphere, material='glass')

# Use the decorator syntax
@add('checkerboard')
def complex_shape():
    return Sphere(10) ^ (Box(5) + [10, 0, 0])
```

## Architecture

- **FastAPI** backend with file watching and WebSocket support
- **manifold3d** for solid geometry operations
- **Three.js** frontend with PBR materials
- **trimesh** for mesh processing and GLB export