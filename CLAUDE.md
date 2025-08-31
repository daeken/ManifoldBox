# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ManifoldBox is a 3D model compiler and real-time viewer that executes Python scripts to generate 3D models using manifold3d. It features both a web-based viewer with real-time editing and command-line export capabilities for batch processing.

## Development Commands

### Web Viewer Mode
```bash
# Run the web application with file watching
python main.py --file <script_file>

# Examples
python main.py --file example.py
python main.py --file models/donut.py
python main.py --file models/foilerParts.py
```

### Command-Line Export Mode
```bash
# Export to single file
python main.py --export <script_file> --output <filename>

# Export to separate files by object name (use % in filename)
python main.py --export <script_file> --output <filename%>

# Examples
python main.py --export models/donut.py --output spaceship.stl
python main.py --export models/foilerParts.py --output parts%.glb
python main.py --export example.py -o model.obj
```

### Package Management
```bash
# Install dependencies (uses uv)
uv sync

# Add new dependencies
uv add <package_name>
```

## Architecture

### Core Components

**main.py** - FastAPI application and CLI tool with:
- File watching using `watchfiles` for real-time updates
- WebSocket server for live viewer communication
- Python script execution with manifold3d integration
- Advanced mesh processing (normals, UV mapping, centering)
- Multi-format export (STL, OBJ, GLB) with material support
- Command-line export functionality
- Web API endpoints

**boxy.py** - 3D modeling DSL providing:
- High-level geometric primitives (Box, Sphere, Cylinder with diameter support)
- 2D primitives (Rectangle, RoundedRectangle, Circle) with revolution operations
- Object decorator system with `@add` for material and naming
- Manifold operations (union, intersection, difference, hull)
- Coordinate system utilities and transformations
- Global object collection and management

**static/index.html** - Interactive Z-up 3D viewer featuring:
- Three.js-based rendering with Z-up coordinate system
- Dual camera modes (perspective/orthographic) with smart positioning
- WASD + mouse controls with pointer lock and proportional speed scaling
- WebSocket client for live script updates
- Advanced material system (basic, normal, checkerboard, glass, all double-sided)
- Wireframe toggle with automatic restoration
- Smart camera repositioning (only on significant bounding box changes)
- Extended clip planes for large objects (up to 1,000,000 units)
- Adjustable movement speed scaling with [ ] keys

### Key Technologies
- **FastAPI**: Web server and API endpoints
- **manifold3d**: 3D geometry processing and manifold operations
- **trimesh**: Mesh processing, normal calculation, UV mapping, and export
- **Three.js**: Client-side 3D rendering with PBR materials
- **WebSockets**: Real-time file change notifications

### Export Formats and Features
- **STL**: Single mesh or multi-mesh export for 3D printing
- **OBJ**: Mesh export with material support
- **GLB**: Full scene export with materials, normals, UV mapping, and PBR support
- **Separate file export**: Use `%` in filename to export each named object separately
- **Material preservation**: Materials are maintained in GLB exports
- **Automatic mesh processing**: Normal calculation, UV mapping, and cleanup

### Material System
- **basic**: Standard Lambert shading (white)
- **normal**: Visualizes surface normals as colors
- **checkerboard**: Procedural checkerboard pattern with UV mapping
- **glass**: 50% translucent material with blue tint
- All materials are double-sided for proper rendering

### Data Flow
1. Python scripts are executed with full `boxy` DSL environment
2. Objects are collected with materials and names via `boxy.objects`
3. Manifolds are converted to trimesh with processing (normals, UVs, cleanup)
4. For viewer: Scene exported to GLB and sent via WebSocket
5. For export: Files written in requested format(s) to disk
6. Viewer automatically centers and scales camera based on object bounds

### API Endpoints
- `GET /` - Main viewer interface
- `GET /compile` - Execute script and return GLB as base64
- `GET /glb/{filename}` - Alternative GLB serving endpoint
- `GET /export/{filename}` - Export to file (supports % for separate files)
- `WebSocket /ws` - Real-time file change notifications

### Viewer Controls
- **WASD + Shift/Space**: Camera movement (speed scales with object size)
- **Mouse drag**: Camera rotation with pointer lock and separate X/Y sensitivity
- **P**: Toggle perspective/orthographic cameras
- **O**: Toggle wireframe mode
- **[ ]**: Decrease/increase movement speed scaling factor

### Script Examples and Capabilities

**models/donut.py** - Complex architectural example:
- Multi-part spaceship hull with windows, bezels, and floors
- Uses RoundedRectangle 2D primitives with revolution
- Demonstrates named objects for separate export
- Boolean operations (difference) for window cutouts
- Material assignment (glass, basic, normal)

**models/foilerParts.py** - Precision manufacturing example:
- Parametric design with precise dimensions
- Cylinder primitives with diameter specification
- Multiple related components (holder and guide)
- Demonstrates real-world CAD-style modeling

**example.py** - Basic primitives demonstration:
- Simple geometric shapes with different materials
- Material assignment examples

### Development Notes

The system provides both interactive development (web viewer) and batch processing (CLI export). The `boxy.py` DSL offers intuitive 3D modeling while maintaining access to the full manifold3d API.

**Script Environment**:
- `manifold3d` / `m3d`: Core manifold operations
- `boxy`: High-level DSL with primitives and operations
- `trimesh`: Direct mesh processing access
- `numpy` / `np`: Numerical operations
- All boxy functions available directly (Box, Sphere, @add, etc.)

**Coordinate System**: Z-up

**Performance**: Handles large objects (thousands of units) with automatic camera scaling and movement speed adjustment