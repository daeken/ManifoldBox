# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ManifoldBox is a 3D model compiler and real-time viewer that executes Python scripts to generate 3D models using manifold3d and displays them in a web-based viewer. It features file watching, WebSocket communication, and an interactive Three.js-powered viewer with advanced material support.

## Development Commands

### Running the Application
```bash
# Run the main application with file watching
python main.py --file <script_file>

# Example with example script
python main.py --file example.py

# Example with model script
python main.py --file models/donut.py
```

### Package Management
```bash
# Install dependencies (uses uv)
uv sync

# Add new dependencies
uv add <package_name>
```

### Testing and Development
```bash
# The application runs a FastAPI server on port 8000
# Access the web interface at http://localhost:8000
```

## Architecture

### Core Components

**main.py** - FastAPI application with key responsibilities:
- File watching using `watchfiles` for Python script changes
- WebSocket server for real-time updates
- Python script execution with manifold3d integration
- Advanced mesh processing (normals, UV mapping)
- GLB export using `trimesh` with PBR material support
- Static file serving

**boxy.py** - 3D modeling DSL providing:
- High-level geometric primitives (Box, Sphere, Cylinder)
- Object decorator system with `@add` for material assignment
- Manifold operations (union, intersection, difference)
- Material system integration
- Global object collection and management

**static/index.html** - Interactive 3D viewer featuring:
- Three.js-based rendering with dual camera modes (perspective/orthographic)
- WASD + mouse camera controls with natural movement
- WebSocket client for live script updates
- GLTF/GLB model loading and display
- Advanced material system (basic, normal, checkerboard, glass)
- Wireframe toggle and detailed mesh statistics
- Automatic wireframe mode restoration after model updates

### Key Technologies
- **FastAPI**: Web server and API endpoints
- **manifold3d**: 3D geometry processing and manifold operations
- **trimesh**: Mesh processing, normal calculation, UV mapping, and GLB export
- **Three.js**: Client-side 3D rendering with PBR materials
- **WebSockets**: Real-time file change notifications

### Material System
The application supports multiple material types:
- **basic**: Standard Lambert shading (white)
- **normal**: Visualizes surface normals as colors
- **checkerboard**: Procedural checkerboard pattern with UV mapping
- **glass**: 50% translucent material with blue tint

### Data Flow
1. Python scripts are watched for changes using `watchfiles`
2. On change, script is executed with `boxy` DSL available
3. Generated manifold objects are collected via `boxy.objects`
4. Each manifold is converted to trimesh with calculated normals and UVs
5. Materials are applied based on object metadata
6. Scene is exported to GLB format with PBR materials
7. WebSocket notifies connected clients
8. Client fetches updated GLB data and renders with material-specific shaders

### API Endpoints
- `GET /` - Serves the main viewer interface
- `GET /compile` - Executes watched script and returns GLB as base64-encoded data
- `GET /glb/{filename}` - Alternative GLB serving endpoint (binary response)
- `WebSocket /ws` - Real-time file change notifications

### Viewer Controls
- **WASD + Shift/Space**: Camera movement (forward/back, left/right, up/down)
- **Mouse drag**: Camera rotation (yaw/pitch with natural controls)
- **P**: Toggle between perspective and orthographic cameras
- **O**: Toggle wireframe mode

### Script Examples
- **models/donut.py**: Advanced example using boxy DSL with decorators and operations

## Development Notes

The system executes Python scripts directly using manifold3d for solid geometry operations. The `boxy.py` DSL provides a higher-level interface for common operations while maintaining access to the full manifold3d API.

Scripts have access to:
- `manifold3d` / `m3d`: Core manifold operations
- `boxy`: High-level DSL (Box, Sphere, add_object, @add decorator)
- `trimesh`: Mesh processing utilities
- `numpy` / `np`: Numerical operations

The viewer automatically handles mesh processing including normal calculation and UV mapping for proper material rendering.