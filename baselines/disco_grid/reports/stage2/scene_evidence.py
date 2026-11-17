"""Render saved executed states using the existing teacher's native geometry.

No planning, post-restore integration, GPU rendering, or invented trajectories.
Native model construction can initialize with integration steps; these are
counted separately and discarded when the saved state is restored. 3D vertices come from the native compiled MuJoCo model after restoring saved qpos.
"""
import argparse, itertools, json, pickle, sys
from pathlib import Path
HERE=Path(__file__).resolve().parents[2];sys.path.insert(0,str(HERE))
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon
from matplotlib.lines import Line2D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import collect as C, data as D, env as E


def local_faces(model,g,mj):
    typ=int(model.geom_type[g]);sz=model.geom_size[g]
    if typ==int(mj.mjtGeom.mjGEOM_MESH):
        idx=int(model.geom_dataid[g]);va=int(model.mesh_vertadr[idx]);vn=int(model.mesh_vertnum[idx]);fa=int(model.mesh_faceadr[idx]);fn=int(model.mesh_facenum[idx])
        return model.mesh_vert[va:va+vn][model.mesh_face[fa:fa+fn]]
    if typ==int(mj.mjtGeom.mjGEOM_BOX):
        v=np.array(list(itertools.product((-1,1),repeat=3)))*sz
        return [v[list(ix)] for ix in [(0,1,3,2),(4,6,7,5),(0,4,5,1),(2,3,7,6),(0,2,6,4),(1,5,7,3)]]
    if typ in [int(mj.mjtGeom.mjGEOM_CYLINDER),int(mj.mjtGeom.mjGEOM_CAPSULE),int(mj.mjtGeom.mjGEOM_SPHERE),int(mj.mjtGeom.mjGEOM_ELLIPSOID)]:
        theta=np.linspace(0,2*np.pi,33)
        if typ==int(mj.mjtGeom.mjGEOM_CYLINDER):
            rings=[np.column_stack((sz[0]*np.cos(theta),sz[0]*np.sin(theta),np.full_like(theta,z))) for z in (-sz[1],sz[1])]
        else:
            phi=np.linspace(-np.pi/2,np.pi/2,17);rings=[]
            sections=[(p,-1) for p in np.linspace(-np.pi/2,0,9)]+[(p,1) for p in np.linspace(0,np.pi/2,9)] if typ==int(mj.mjtGeom.mjGEOM_CAPSULE) else [(p,0) for p in phi]
            for p,side in sections:
                x=sz[0]*np.cos(p)*np.cos(theta);y=sz[0]*np.cos(p)*np.sin(theta);z=np.full_like(theta,sz[0]*np.sin(p))
                if typ==int(mj.mjtGeom.mjGEOM_CAPSULE):z+=side*sz[1]
                elif typ==int(mj.mjtGeom.mjGEOM_ELLIPSOID):y*=sz[1]/sz[0];z*=sz[2]/sz[0]
                rings.append(np.column_stack((x,y,z)))
        faces=[np.array([a[i],a[i+1],b[i+1],b[i]]) for a,b in zip(rings,rings[1:]) for i in range(32)]
        if typ==int(mj.mjtGeom.mjGEOM_CYLINDER):faces.extend([rings[0],rings[-1]])
        return faces
    if typ==int(mj.mjtGeom.mjGEOM_PLANE):return []
    raise ValueError(f'Unsupported native geom type {typ}; never silently omit robot geometry')


def render3d(ax,state,env):
    row,raw=env._get_row_and_raw(state.root_id);b=env.backend;b.boot();initialization_steps=0;original_step=b.mujoco.mj_step
    def count_step(*args,**kwargs):
        nonlocal initialization_steps
        initialization_steps+=int(kwargs.get('nstep',args[2] if len(args)>2 else 1))
        return original_step(*args,**kwargs)
    b.mujoco.mj_step=count_step
    try:scene=b._get_env(state.root_id,raw)
    finally:b.mujoco.mj_step=original_step
    b._restore_env(scene,state.physics_payload)
    model,data=scene.model,scene.data;bounds=[];moving_bounds=[];geoms=0;mesh_hashes={}
    for g in range(model.ngeom):
        color=model.geom_rgba[g].copy()
        if color[3]<=0:continue
        faces=local_faces(model,g,b.mujoco)
        if not len(faces):continue
        rotation=data.geom_xmat[g].reshape(3,3);position=data.geom_xpos[g]
        world=[np.asarray(f)@rotation.T+position for f in faces]
        alpha=min(.8,float(color[3]))
        # Translucent structural walls leave the native arm and objects visible.
        if int(model.geom_bodyid[g])==0:alpha=min(alpha,.18)
        ax.add_collection3d(Poly3DCollection(world,facecolors=color[:3],edgecolors='none',alpha=alpha,rasterized=True))
        bounds.append(np.concatenate(world));geoms+=1
        if int(model.geom_bodyid[g])!=0:moving_bounds.append(np.concatenate(world))
        if int(model.geom_type[g])==int(b.mujoco.mjtGeom.mjGEOM_MESH):
            import hashlib;mesh_hashes[str(g)]=hashlib.sha256(np.asarray(faces).tobytes()).hexdigest()
    points=np.concatenate(moving_bounds or bounds);low=points.min(0);high=points.max(0);span=high-low
    for setter,lo,hi in zip((ax.set_xlim,ax.set_ylim,ax.set_zlim),low-.03,high+.03):setter(lo,hi)
    ax.set_box_aspect(span);ax.view_init(elev=24,azim=-130)
    ax.set_xlabel('x (m)');ax.set_ylabel('y (m)');ax.set_zlabel('z (m)')
    return dict(native_geoms=geoms,native_model_initialization_steps=initialization_steps,post_restore_steps=0,native_mesh_vertex_hashes=mesh_hashes,display_only='curved primitives tessellated; all native mesh faces retained; view cropped to robot/object extents')


def render2d(ax,state,env):
    row,raw=env._get_row_and_raw(state.root_id);b=env.backend;b.boot();inp=row['inputs']
    legal=D.legal_static_destinations(inp)
    if legal:
        points=np.array([inp['cell_xy'][str(cell)] for cell in legal])
        ax.scatter(points[:,0],points[:,1],s=9,c='#b8b8b8',marker='+',zorder=0)
    movable=set(D.movable_object_indices(inp,'2d'))
    for i,(oid,cell,attr) in enumerate(zip(inp['ids'],state.cells,inp['attrs'])):
        xy=inp['cell_xy'][str(cell)];color='#bf423b' if i==inp['tid'] else '#5685a6' if i in movable else '#8b8b8b'
        ax.add_patch(Circle(xy,float(attr[0]),facecolor=color,alpha=.8));ax.text(*xy,oid,ha='center',fontsize=6)
    for name,(core,radius) in b.ge.bodies(b.E['robot'],state.q_t,state.gripper_state['gap']).items():
        core=np.asarray(core)
        if len(core)==1:ax.add_patch(Circle(core[0],radius,color='#343a40'))
        elif len(core)==2:
            delta=core[1]-core[0];normal=np.array([-delta[1],delta[0]])/np.linalg.norm(delta)*radius
            ax.add_patch(Polygon([core[0]+normal,core[1]+normal,core[1]-normal,core[0]-normal],color='#343a40'))
            for point in core:ax.add_patch(Circle(point,radius,color='#343a40'))
        else:ax.add_patch(Polygon(core,color='#343a40'))
    ax.plot(*inp['goal'][:2],'*',color='#bf423b',ms=12)
    ax.legend(handles=[Line2D([],[],marker='o',linestyle='none',color='#bf423b',label='Target'),
        Line2D([],[],marker='o',linestyle='none',color='#5685a6',label='Movable obstacle'),
        Line2D([],[],marker='o',linestyle='none',color='#8b8b8b',label='Fixed obstacle'),
        Line2D([],[],marker='*',linestyle='none',color='#bf423b',label='Target goal'),
        Line2D([],[],marker='+',linestyle='none',color='#b8b8b8',label='Originally empty legal cell')],fontsize=6,loc='upper left')
    ax.set_aspect('equal');ax.autoscale_view();ax.set_xlabel('x (m)');ax.set_ylabel('y (m)')
    return dict(native_robot_geometry=str(b.E['robot']),original_legal_cells=legal,display_only='native collision cores and radii; originally empty legal cells marked; no invented motion paths')


def run(paths,out):
    C.require_headroom();out.mkdir(parents=True,exist_ok=False);manifest=[]
    for i,path in enumerate(paths):
        state=pickle.loads(path.read_bytes());env=E.RepairEnv(state.domain)
        fig=plt.figure(figsize=(7,5));ax=fig.add_subplot(111,projection='3d' if state.domain=='3d' else None)
        detail=(render3d if state.domain=='3d' else render2d)(ax,state,env)
        ax.set_title(f'{state.root_id} | executed depth {state.depth}\nq/state from {path.name} | {D.sha256_file(path)[:12]}',fontsize=9)
        for ext in ('png','svg'):fig.savefig(out/f'{i:02d}_{state.domain}_depth{state.depth}.{ext}',dpi=200,bbox_inches='tight')
        plt.close(fig)
        manifest.append(dict(path=str(path),state_sha256=D.sha256_file(path),state_hash=state.state_hash(),root_id=state.root_id,
            domain=state.domain,executed_prefix=state.prefix,q_t=state.q_t,geometry=detail,teacher_sources=C.teacher_sources(state.domain),
            physics_initialization_steps=detail.get('native_model_initialization_steps',0),post_restore_physics_steps=0,physical_planner_calls=0,render_backend='matplotlib Agg CPU; native forward kinematics only'))
    (out/'scene_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--states',type=Path,nargs='+',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.states,a.out)
