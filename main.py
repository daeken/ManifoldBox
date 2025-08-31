import argparse
import asyncio
import base64
import json
import os
import importlib
import importlib.util
import io
import sys
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
            
            # Calculate UVs
            mesh = mobj.uvMapper(mesh)
            
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

@app.get("/export/{filename}")
async def export_file(filename: str):
    """Export models to STL, OBJ, or GLB file(s)"""
    if not watched_file or not os.path.exists(watched_file):
        return JSONResponse({"error": "No file being watched or file not found"})
    
    try:
        # Determine file format from extension
        file_ext = filename.lower().split('.')[-1]
        if file_ext not in ['stl', 'obj', 'glb']:
            return JSONResponse({"error": "Unsupported file format. Use .stl, .obj, or .glb"})
        
        # Execute script and collect objects
        importlib.reload(boxy)
        boxy.clear_objects()
        
        try:
            spec = importlib.util.spec_from_file_location("user_script", watched_file)
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
        except Exception as import_error:
            return JSONResponse({"error": f"Script execution failed: {str(import_error)}"})
        
        if len(boxy.objects) == 0:
            return JSONResponse({"error": "No objects found in script"})
        
        # Check if we should create separate files
        separate_files = '%' in filename
        
        if separate_files:
            # Group objects by name
            grouped_objects = {}
            for mobj, material, name in boxy.objects:
                group_name = name if name else 'unnamed'
                if group_name not in grouped_objects:
                    grouped_objects[group_name] = []
                grouped_objects[group_name].append((mobj, material))
            
            # Create separate files for each group
            exported_files = []
            base_filename = filename.replace('%', '')
            
            for group_name, objects in grouped_objects.items():
                group_filename = base_filename.replace('.', f'_{group_name}.')
                scene = trimesh.Scene()
                
                for mobj, material in objects:
                    mesh_data = mobj.to_mesh()
                    vertices = np.array(mesh_data.vert_properties)[:, :3]
                    faces = np.array(mesh_data.tri_verts).reshape(-1, 3)
                    mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
                    mesh.update_faces(mesh.unique_faces())
                    mesh.remove_unreferenced_vertices()
                    
                    # Calculate normals and UVs for GLB export
                    if file_ext == 'glb':
                        mesh = calculate_vertex_normals(mesh)
                        mesh = mobj.uvMapper(mesh)
                        tmat = trimesh.visual.material.PBRMaterial()
                        tmat.name = material
                        mesh.visual = trimesh.visual.TextureVisuals(uv=mesh.vertex_attributes['uv'], material=tmat)
                    
                    scene.add_geometry(mesh)
                
                # Export the group
                try:
                    if len(objects) == 1 and file_ext in ['stl', 'obj']:
                        # Single mesh export
                        mesh_data = objects[0][0].to_mesh()
                        vertices = np.array(mesh_data.vert_properties)[:, :3]
                        faces = np.array(mesh_data.tri_verts).reshape(-1, 3)
                        mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
                        mesh.update_faces(mesh.unique_faces())
                        mesh.remove_unreferenced_vertices()
                        file_data = mesh.export(file_type=file_ext)
                    else:
                        # Scene export
                        file_data = scene.export(file_type=file_ext)
                    
                    # Write file to disk
                    with open(group_filename, 'wb') as f:
                        f.write(file_data)
                    exported_files.append(group_filename)
                    
                except Exception as e:
                    return JSONResponse({"error": f"Failed to export {group_filename}: {str(e)}"})
            
            return JSONResponse({
                "success": True,
                "message": f"Exported {len(exported_files)} files",
                "files": exported_files
            })
            
        else:
            # Single file export
            scene = trimesh.Scene()
            
            for mobj, material, name in boxy.objects:
                mesh_data = mobj.to_mesh()
                vertices = np.array(mesh_data.vert_properties)[:, :3]
                faces = np.array(mesh_data.tri_verts).reshape(-1, 3)
                mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
                mesh.update_faces(mesh.unique_faces())
                mesh.remove_unreferenced_vertices()
                
                # Calculate normals and UVs for GLB export
                if file_ext == 'glb':
                    mesh = calculate_vertex_normals(mesh)
                    mesh = mobj.uvMapper(mesh)
                    tmat = trimesh.visual.material.PBRMaterial()
                    tmat.name = material
                    mesh.visual = trimesh.visual.TextureVisuals(uv=mesh.vertex_attributes['uv'], material=tmat)
                
                scene.add_geometry(mesh, node_name=name)
            
            # Export single file
            try:
                if len(boxy.objects) == 1 and file_ext in ['stl', 'obj']:
                    # Single mesh export
                    mobj, material, name = boxy.objects[0]
                    mesh_data = mobj.to_mesh()
                    vertices = np.array(mesh_data.vert_properties)[:, :3]
                    faces = np.array(mesh_data.tri_verts).reshape(-1, 3)
                    mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
                    mesh.update_faces(mesh.unique_faces())
                    mesh.remove_unreferenced_vertices()
                    file_data = mesh.export(file_type=file_ext)
                else:
                    # Scene export
                    file_data = scene.export(file_type=file_ext)
                
                # Write file to disk
                with open(filename, 'wb') as f:
                    f.write(file_data)
                
                return JSONResponse({
                    "success": True,
                    "message": f"Exported to {filename}",
                    "file": filename
                })
            except Exception as e:
                return JSONResponse({"error": f"Failed to export {filename}: {str(e)}"})
    
    except Exception as e:
        return JSONResponse({"error": f"Export failed: {str(e)}"})

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

def export_from_script(script_path: str, output_filename: str):
    """Export models from script to file without running the server"""
    try:
        # Determine file format from extension
        file_ext = output_filename.lower().split('.')[-1]
        if file_ext not in ['stl', 'obj', 'glb']:
            print(f"Error: Unsupported file format. Use .stl, .obj, or .glb")
            return False
        
        # Execute script and collect objects
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
                
                print(f"Executed script: {script_path}")
            else:
                print(f"Error: Could not load script {script_path}")
                return False
                
        except Exception as import_error:
            print(f"Error executing script: {import_error}")
            import traceback
            traceback.print_exc()
            return False
        
        if len(boxy.objects) == 0:
            print("Error: No objects found in script")
            return False
        
        print(f"Found {len(boxy.objects)} objects")
        
        # Check if we should create separate files
        separate_files = '%' in output_filename
        
        if separate_files:
            # Group objects by name
            grouped_objects = {}
            for mobj, material, name in boxy.objects:
                group_name = name if name else 'unnamed'
                if group_name not in grouped_objects:
                    grouped_objects[group_name] = []
                grouped_objects[group_name].append((mobj, material))
            
            print(f"Exporting to {len(grouped_objects)} separate files:")
            
            # Create separate files for each group
            exported_files = []
            base_filename = output_filename.replace('%', '')
            
            for group_name, objects in grouped_objects.items():
                group_filename = base_filename.replace('.', f'_{group_name}.')
                scene = trimesh.Scene()
                
                for mobj, material in objects:
                    mesh_data = mobj.to_mesh()
                    vertices = np.array(mesh_data.vert_properties)[:, :3]
                    faces = np.array(mesh_data.tri_verts).reshape(-1, 3)
                    mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
                    mesh.update_faces(mesh.unique_faces())
                    mesh.remove_unreferenced_vertices()
                    
                    # Calculate normals and UVs for GLB export
                    if file_ext == 'glb':
                        mesh = calculate_vertex_normals(mesh)
                        mesh = mobj.uvMapper(mesh)
                        tmat = trimesh.visual.material.PBRMaterial()
                        tmat.name = material
                        mesh.visual = trimesh.visual.TextureVisuals(uv=mesh.vertex_attributes['uv'], material=tmat)
                    
                    scene.add_geometry(mesh)
                
                # Export the group
                try:
                    if len(objects) == 1 and file_ext in ['stl', 'obj']:
                        # Single mesh export
                        mesh_data = objects[0][0].to_mesh()
                        vertices = np.array(mesh_data.vert_properties)[:, :3]
                        faces = np.array(mesh_data.tri_verts).reshape(-1, 3)
                        mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
                        mesh.update_faces(mesh.unique_faces())
                        mesh.remove_unreferenced_vertices()
                        file_data = mesh.export(file_type=file_ext)
                    else:
                        # Scene export
                        file_data = scene.export(file_type=file_ext)
                    
                    # Write file to disk
                    with open(group_filename, 'wb') as f:
                        f.write(file_data)
                    exported_files.append(group_filename)
                    print(f"  → {group_filename} ({len(objects)} objects)")
                    
                except Exception as e:
                    print(f"Error exporting {group_filename}: {e}")
                    return False
            
            print(f"Successfully exported {len(exported_files)} files")
            return True
            
        else:
            # Single file export
            scene = trimesh.Scene()
            
            for mobj, material, name in boxy.objects:
                mesh_data = mobj.to_mesh()
                vertices = np.array(mesh_data.vert_properties)[:, :3]
                faces = np.array(mesh_data.tri_verts).reshape(-1, 3)
                mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
                mesh.update_faces(mesh.unique_faces())
                mesh.remove_unreferenced_vertices()
                
                # Calculate normals and UVs for GLB export
                if file_ext == 'glb':
                    mesh = calculate_vertex_normals(mesh)
                    mesh = mobj.uvMapper(mesh)
                    tmat = trimesh.visual.material.PBRMaterial()
                    tmat.name = material
                    mesh.visual = trimesh.visual.TextureVisuals(uv=mesh.vertex_attributes['uv'], material=tmat)
                
                scene.add_geometry(mesh, node_name=name)
            
            # Export single file
            try:
                if len(boxy.objects) == 1 and file_ext in ['stl', 'obj']:
                    # Single mesh export
                    mobj, material, name = boxy.objects[0]
                    mesh_data = mobj.to_mesh()
                    vertices = np.array(mesh_data.vert_properties)[:, :3]
                    faces = np.array(mesh_data.tri_verts).reshape(-1, 3)
                    mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
                    mesh.update_faces(mesh.unique_faces())
                    mesh.remove_unreferenced_vertices()
                    file_data = mesh.export(file_type=file_ext)
                else:
                    # Scene export
                    file_data = scene.export(file_type=file_ext)
                
                # Write file to disk
                with open(output_filename, 'wb') as f:
                    f.write(file_data)
                
                print(f"Successfully exported to {output_filename}")
                return True
                
            except Exception as e:
                print(f"Error exporting {output_filename}: {e}")
                return False
                
    except Exception as e:
        print(f"Export failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ManifoldBox - 3D Model Compiler and Viewer")
    parser.add_argument("--file", type=str, help="File to watch for changes (server mode)")
    parser.add_argument("--export", type=str, help="Script file to export")
    parser.add_argument("--output", "-o", type=str, help="Output filename (use % for separate files by name)")
    args = parser.parse_args()
    
    if args.export and args.output:
        # Command-line export mode
        script_path = os.path.abspath(args.export)
        if not os.path.exists(script_path):
            print(f"Error: Script file {script_path} not found")
            sys.exit(1)
        
        success = export_from_script(script_path, args.output)
        sys.exit(0 if success else 1)
    
    elif args.export or args.output:
        print("Error: Both --export and --output are required for export mode")
        print("Usage: python main.py --export script.py --output model.stl")
        print("       python main.py --export script.py --output parts%.glb  # separate files")
        sys.exit(1)
    
    else:
        # Server mode
        if args.file:
            watched_file = os.path.abspath(args.file)
            print(f"Watching file: {watched_file}")
        
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
