import argparse
import asyncio
import base64
import json
import os
import importlib, io, sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, Response
from watchfiles import awatch

import manifold3d as m3d
import trimesh
import numpy as np
import boxy

app = FastAPI()

# Global state
watched_file: Optional[str] = None
connected_clients = set()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse('static/index.html')

def calculate_vertex_normals(mesh):
    """Calculate area-weighted per-vertex normals"""
    vertices = mesh.vertices
    faces = mesh.faces
    
    # Initialize vertex normals to zero
    vertex_normals = np.zeros_like(vertices)
    
    # Calculate face normals and areas
    for face in faces:
        # Get the three vertices of the face
        v0, v1, v2 = vertices[face]
        
        # Calculate two edge vectors
        edge1 = v1 - v0
        edge2 = v2 - v0
        
        # Calculate face normal using cross product
        face_normal = np.cross(edge1, edge2)
        
        # The magnitude of the cross product gives twice the area of the triangle
        face_area = np.linalg.norm(face_normal)
        
        # Normalize the face normal
        if face_area > 0:
            face_normal = face_normal / face_area
            
            # Add the area-weighted face normal to each vertex of the face
            # The area weighting is already included since face_area is the magnitude
            for vertex_idx in face:
                vertex_normals[vertex_idx] += face_normal * face_area
    
    # Normalize all vertex normals
    for i in range(len(vertex_normals)):
        normal_length = np.linalg.norm(vertex_normals[i])
        if normal_length > 0:
            vertex_normals[i] = vertex_normals[i] / normal_length

    # Create a new mesh with the calculated normals
    mesh_with_normals = trimesh.Trimesh(
        vertices=vertices,
        faces=faces,
        vertex_normals=vertex_normals
    )
    
    # Copy over any existing visual properties
    if hasattr(mesh, 'visual'):
        mesh_with_normals.visual = mesh.visual
    
    return mesh_with_normals

def calculate_vertex_uvs(mesh):
    """Calculate per-vertex UV coordinates using box unwrapping algorithm"""
    vertices = mesh.vertices
    faces = mesh.faces
    vertex_normals = mesh.vertex_normals if hasattr(mesh, 'vertex_normals') and mesh.vertex_normals is not None else None
    
    if vertex_normals is None:
        # If no vertex normals, calculate them quickly
        vertex_normals = np.zeros_like(vertices)
        for face in faces:
            v0, v1, v2 = vertices[face]
            edge1 = v1 - v0
            edge2 = v2 - v0
            face_normal = np.cross(edge1, edge2)
            face_area = np.linalg.norm(face_normal)
            if face_area > 0:
                face_normal = face_normal / face_area
                for vertex_idx in face:
                    vertex_normals[vertex_idx] += face_normal * face_area
        
        # Normalize vertex normals
        for i in range(len(vertex_normals)):
            normal_length = np.linalg.norm(vertex_normals[i])
            if normal_length > 0:
                vertex_normals[i] = vertex_normals[i] / normal_length

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

def create_glb_from_script(script_path: str) -> bytes:
    """Execute Python script directly and create GLB from the result"""
    try:
        importlib.reload(boxy)
        boxy.clear_objects()
        try:
            spec = importlib.util.spec_from_file_location("user_script", script_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                # Add required imports to the module
                module.m3d = m3d
                module.manifold3d = m3d
                module.trimesh = trimesh
                module.boxy = boxy
                module.np = np
                module.numpy = np

                for name in dir(boxy):
                    if not name.startswith('__'):
                        setattr(module, name, getattr(boxy, name))

                spec.loader.exec_module(module)
                
                print(f"Imported Python script as module: {script_path}")
            else:
                raise ImportError("Could not create module spec")
                
        except Exception as import_error:
            print(f"Module import failed!")
            print(import_error)
        
        scene = trimesh.Scene()
        for mobj, material, name in boxy.objects:
            mesh_data = mobj.to_mesh()
            vertices = np.array(mesh_data.vert_properties)[:, :3]
            faces = np.array(mesh_data.tri_verts).reshape(-1, 3)
            mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
            mesh.update_faces(mesh.unique_faces())
            mesh.remove_unreferenced_vertices()
            
            # Calculate area-weighted per-vertex normals
            mesh = calculate_vertex_normals(mesh)
            
            # Calculate per-vertex UVs
            mesh = calculate_vertex_uvs(mesh)
            
            tmat = trimesh.visual.material.PBRMaterial()
            tmat.name = material
            mesh.visual = trimesh.visual.TextureVisuals(uv=mesh.vertex_attributes['uv'], material=tmat)
            scene.add_geometry(mesh, node_name=name)
            print(f"Found manifold: {name or 'unnamed'}")
        
        if len(boxy.objects) == 0:
            print("No manifolds or meshes found in script")
            return create_fallback_glb()
        
        # Export to GLB
        glb_data = scene.export(file_type='glb')
        return glb_data
        
    except Exception as e:
        print(f"Error creating GLB from script: {e}")
        import traceback
        traceback.print_exc()
        return create_fallback_glb()

def create_fallback_glb() -> bytes:
    """Create a simple fallback GLB"""
    mesh = trimesh.creation.box(extents=[1.0, 1.0, 1.0])
    glb_data = mesh.export(file_type='glb')
    return glb_data

@app.get("/compile")
async def compile_file():
    """Compile the watched file and return GLB data"""
    if not watched_file or not os.path.exists(watched_file):
        return JSONResponse({"error": "No file being watched or file not found"})
    
    try:
        # Execute Python script and generate GLB
        glb_bytes = create_glb_from_script(watched_file)
        
        # Return GLB as base64 encoded data
        glb_b64 = base64.b64encode(glb_bytes).decode('utf-8')
        
        return JSONResponse({
            "success": True,
            "filename": watched_file,
            "glb_data": glb_b64,
            "timestamp": asyncio.get_event_loop().time()
        })
        
    except Exception as e:
        return JSONResponse({"error": f"Failed to compile file: {str(e)}"})

@app.get("/glb/{filename}")
async def serve_glb(filename: str):
    """Serve GLB file directly (alternative endpoint)"""
    if not watched_file or not os.path.exists(watched_file):
        return JSONResponse({"error": "No file being watched or file not found"})
    
    try:
        glb_bytes = create_glb_from_script(watched_file)
        
        return Response(
            content=glb_bytes,
            media_type="model/gltf-binary",
            headers={"Content-Disposition": f"inline; filename={filename}.glb"}
        )
        
    except Exception as e:
        return JSONResponse({"error": f"Failed to serve GLB: {str(e)}"})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connected_clients.remove(websocket)

async def notify_clients():
    """Notify all connected clients of file changes"""
    if connected_clients:
        message = json.dumps({"type": "file_changed"})
        disconnected = []
        for client in connected_clients:
            try:
                await client.send_text(message)
            except:
                disconnected.append(client)
        
        # Remove disconnected clients
        for client in disconnected:
            connected_clients.discard(client)

async def watch_file():
    """Watch the specified file for changes"""
    if not watched_file:
        return
    
    async for changes in awatch(watched_file):
        print(f"File changed: {changes}")
        await notify_clients()

def start_file_watcher():
    """Start the file watcher in the background"""
    if watched_file:
        asyncio.create_task(watch_file())

@app.on_event("startup")
async def startup_event():
    start_file_watcher()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ManifoldBox - 3D Model Compiler and Viewer")
    parser.add_argument("--file", type=str, help="File to watch for changes")
    args = parser.parse_args()
    
    if args.file:
        watched_file = os.path.abspath(args.file)
        print(f"Watching file: {watched_file}")
    
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
