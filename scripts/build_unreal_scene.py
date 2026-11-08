"""Run inside Unreal Python to author an original coastal rescue level.

Uses engine primitives, original generated meshes and checked CC0 scans. Hidden
collision proxies are explicit and match the mission's conservative map. Human
meshes are purpose-built simulation proxies, not claimed photorealistic patients.
"""
from pathlib import Path
import json
import math
import sys
import unreal as ue

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from unreal_cinematic_materials import ocean_material
CONTENT='/Game/SKYFORGE'
actors=ue.get_editor_subsystem(ue.EditorActorSubsystem)
levels=ue.get_editor_subsystem(ue.LevelEditorSubsystem)
assets=ue.AssetToolsHelpers.get_asset_tools()
scene=json.loads((ROOT/'configs/scenes/coastal-rescue.json').read_text())
labels=[];collision_manifest=[]
ue.EditorAssetLibrary.make_directory(CONTENT)
level_path=CONTENT+'/CoastalRescue'
if ue.EditorAssetLibrary.does_asset_exist(level_path):
    if not levels.load_level(level_path):raise RuntimeError('Cannot load coastal rescue level')
    for existing_actor in actors.get_all_level_actors():
        if isinstance(existing_actor,(ue.StaticMeshActor,ue.PlayerStart,ue.DirectionalLight,ue.SkyAtmosphere,ue.SkyLight,ue.ExponentialHeightFog)):
            actors.destroy_actor(existing_actor)
elif not levels.new_level(level_path):raise RuntimeError('Cannot create coastal rescue level')


def material(name,color,texture=None,normal=None,roughness=.8,metallic=0.):
    path=CONTENT+'/Materials/'+name
    mat=ue.load_asset(path)
    if mat:return mat
    ue.EditorAssetLibrary.make_directory(CONTENT+'/Materials')
    mat=assets.create_asset(name,CONTENT+'/Materials',ue.Material,ue.MaterialFactoryNew())
    mat.set_editor_property('two_sided',True)
    library=ue.MaterialEditingLibrary
    if texture:
        expression=library.create_material_expression(mat,ue.MaterialExpressionTextureSample,-350,0)
        expression.set_editor_property('texture',texture)
        library.connect_material_property(expression,'RGB',ue.MaterialProperty.MP_BASE_COLOR)
    else:
        expression=library.create_material_expression(mat,ue.MaterialExpressionConstant3Vector,-350,0)
        expression.set_editor_property('constant',ue.LinearColor(*color,1))
        library.connect_material_property(expression,'',ue.MaterialProperty.MP_BASE_COLOR)
    if normal:
        expression=library.create_material_expression(mat,ue.MaterialExpressionTextureSample,-350,180)
        expression.set_editor_property('texture',normal)
        expression.set_editor_property('sampler_type',ue.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        library.connect_material_property(expression,'RGB',ue.MaterialProperty.MP_NORMAL)
    for prop,value in [(ue.MaterialProperty.MP_ROUGHNESS,roughness),(ue.MaterialProperty.MP_METALLIC,metallic)]:
        expression=library.create_material_expression(mat,ue.MaterialExpressionConstant,-120,320)
        expression.set_editor_property('r',value);library.connect_material_property(expression,'',prop)
    library.recompile_material(mat);ue.EditorAssetLibrary.save_loaded_asset(mat)
    return mat


def import_asset(path,name=None,scale=1.,mesh=False):
    folder=CONTENT+('/Meshes' if mesh else '/Textures')
    name=name or path.stem;existing=ue.load_asset(folder+'/'+name)
    if existing:return existing
    ue.EditorAssetLibrary.make_directory(folder)
    task=ue.AssetImportTask();task.set_editor_property('filename',str(path))
    task.set_editor_property('destination_path',folder);task.set_editor_property('destination_name',name)
    task.set_editor_property('automated',True);task.set_editor_property('replace_existing',True);task.set_editor_property('save',True)
    if mesh:
        options=ue.FbxImportUI();options.set_editor_property('import_mesh',True)
        options.set_editor_property('import_as_skeletal',False);options.set_editor_property('import_materials',False)
        options.set_editor_property('import_textures',False);options.set_editor_property('mesh_type_to_import',ue.FBXImportType.FBXIT_STATIC_MESH)
        data=options.get_editor_property('static_mesh_import_data')
        data.set_editor_property('combine_meshes',True);data.set_editor_property('import_uniform_scale',scale)
        data.set_editor_property('convert_scene',False);data.set_editor_property('convert_scene_unit',False)
        data.set_editor_property('auto_generate_collision',False)
        task.set_editor_property('options',options)
    assets.import_asset_tasks([task])
    paths=task.get_editor_property('imported_object_paths')
    if not paths:raise RuntimeError('Import failed: '+str(path))
    result=ue.load_asset(paths[0])
    if not mesh and ('normal' in name or 'nor_gl' in name):
        result.set_editor_property('compression_settings',ue.TextureCompressionSettings.TC_NORMALMAP)
        result.set_editor_property('srgb',False);ue.EditorAssetLibrary.save_loaded_asset(result)
    return result


def location(p):return ue.Vector(p[1]*100,p[0]*100,p[2]*100)


def spawn(name,mesh,p,scale=(1,1,1),yaw=0,mat=None,collision=False,hidden=False,movable=False,pitch=0):
    actor=actors.spawn_actor_from_class(ue.StaticMeshActor,location(p),ue.Rotator(pitch=pitch,yaw=90-yaw,roll=0))
    actor.set_actor_label(name);component=actor.static_mesh_component
    component.set_mobility(ue.ComponentMobility.MOVABLE if movable else ue.ComponentMobility.STATIC)
    component.set_static_mesh(mesh);actor.set_actor_scale3d(ue.Vector(*scale))
    if collision:component.set_collision_profile_name('BlockAll')
    component.set_collision_enabled(ue.CollisionEnabled.QUERY_AND_PHYSICS if collision else ue.CollisionEnabled.NO_COLLISION)
    actor.set_actor_enable_collision(collision);actor.set_actor_hidden_in_game(hidden)
    if mat:
        for slot in range(max(1,component.get_num_materials())):component.set_material(slot,mat)
    return actor


cube=ue.load_asset('/Engine/BasicShapes/Cube.Cube');cylinder=ue.load_asset('/Engine/BasicShapes/Cylinder.Cylinder')
def box(name,p,size,mat,**kwargs):return spawn(name,cube,p,size,mat=mat,**kwargs)

# Original geometry was generated in metres; imported meshes are converted to cm.
generated=ROOT/'runtime/unreal/source_assets'
terrain=import_asset(generated/'cinematic_island_v2.obj',mesh=True,scale=100)
person=import_asset(generated/'rescue_person_proxy.obj',mesh=True,scale=100)
roof=import_asset(generated/'hangar_roof.obj',mesh=True,scale=100)
palm=import_asset(generated/'coastal_palm.obj',mesh=True,scale=100)
inert_prop=import_asset(generated/'inert_field_prop_v1.obj',mesh=True,scale=100)
people_root=ROOT/'sim/assets/rescue_people'
clothed_prone=import_asset(people_root/'injured_person_clothed.obj',mesh=True,scale=100)
clothed_standing=import_asset(people_root/'casual_shirt_standing.obj',mesh=True,scale=100)
human_document=json.loads((people_root/'casual_shirt_standing.gltf').read_text())
human_diffuse=import_asset(people_root/human_document['images'][0]['uri'],'human_clothed_diffuse')
human_normal=import_asset(people_root/human_document['images'][1]['uri'],'human_clothed_normal')
human_material=material('ClothedHumanV2',(.5,.4,.3),human_diffuse,human_normal)
rock=import_asset(ROOT/'sim/assets/rock_face_01/rock_face_01.obj',mesh=True,scale=100)
barrier=import_asset(ROOT/'sim/assets/concrete_road_barrier_02/concrete_road_barrier_02.obj',mesh=True,scale=100)
sand_diff=import_asset(ROOT/'sim/assets/coast_sand_02/diffuse.jpg','sand_diffuse')
sand_normal=import_asset(ROOT/'sim/assets/coast_sand_02/normal.jpg','sand_normal')
rock_diff=import_asset(ROOT/'sim/assets/rock_face_01/textures/rock_face_01_diff_1k.jpg')
rock_normal=import_asset(ROOT/'sim/assets/rock_face_01/textures/rock_face_01_nor_gl_1k.jpg')
concrete_diff=import_asset(ROOT/'sim/assets/concrete_road_barrier_02/textures/concrete_road_barrier_02_diff_1k.jpg')
concrete_normal=import_asset(ROOT/'sim/assets/concrete_road_barrier_02/textures/concrete_road_barrier_02_nor_gl_1k.jpg')
mat={}
mat['sand']=material('CoastalSand',(.6,.5,.3),sand_diff,sand_normal)
mat['rock']=material('ScannedRock',(.4,.4,.4),rock_diff,rock_normal)
mat['concrete']=material('WeatheredConcrete',(.4,.4,.37),concrete_diff,concrete_normal)
for key,asset in [('ground','coast_sand_rocks_02'),('hills','aerial_grass_rock'),('cliff','aerial_rocks_02')]:
    diffuse=import_asset(ROOT/'sim/assets'/asset/'diffuse.jpg',asset+'_diffuse')
    normal=import_asset(ROOT/'sim/assets'/asset/'normal.jpg',asset+'_normal')
    mat[key]=material(asset+'_V2',(.4,.4,.35),diffuse,normal)
for name,color,rough,metal in [
    ('steel',(.12,.15,.17),.55,.7),('roof',(.22,.25,.27),.65,.55),('road',(.075,.085,.09),.95,0),
    ('white',(.78,.79,.72),.8,0),('orange',(.88,.23,.015),.85,0),('skin',(.55,.35,.22),.9,0),
    ('dark',(.035,.045,.05),.8,0),('purple',(.32,.065,.55),.85,0),('mine',(.20,.30,.045),.85,.1),
    ('plastic',(.025,.58,.78),.4,0),('green',(.05,.35,.15),.8,0),('water',(.015,.15,.21),.13,.35),
    ('trunk',(.20,.13,.07),.95,0),('leaves',(.055,.19,.025),.85,0),('yellow',(.7,.43,.025),.6,.15)]:
    mat[name]=material(name.title(),color,roughness=rough,metallic=metal)

land=spawn('Sculpted coastal plateau and ridgeline',terrain,[0,0,0],yaw=90)
for slot in range(land.static_mesh_component.get_num_materials()):
    name=str(terrain.get_editor_property('static_materials')[slot].material_slot_name)
    key='cliff' if 'rock' in name else 'hills' if 'grass' in name else 'ground'
    land.static_mesh_component.set_material(slot,mat[key])
box('Mission ground collision proxy',[0,0,-.5],[40,32,1],mat['concrete'],collision=True,hidden=True)
box('Animated coastal water',[0,0,-11.75],[3000,3000,.15],ocean_material(CONTENT+'/Materials'))

# Scanned cliffs, original palms and a road around the evacuation base.
scans={}
for scan_name in ('coastal_cliff_02','coast_line_02','coast_rocks_03','island_tree_02'):
    mesh=import_asset(ROOT/'sim/assets'/scan_name/(scan_name+'.obj'),mesh=True,scale=100)
    scans[scan_name]=mesh
    for slot in range(len(mesh.get_editor_property('static_materials'))):
        slot_name=str(mesh.get_editor_property('static_materials')[slot].material_slot_name)
        texture_root=ROOT/'sim/assets'/scan_name/'textures'
        diffuse_path=texture_root/(slot_name+'_diff_1k.jpg');normal_path=texture_root/(slot_name+'_nor_gl_1k.jpg')
        if diffuse_path.exists():
            diffuse=import_asset(diffuse_path);normal=import_asset(normal_path) if normal_path.exists() else None
            surface=material(slot_name+'_scan_V2',(.3,.4,.25),diffuse,normal)
            mesh.set_material(slot,surface)
    ue.EditorAssetLibrary.save_loaded_asset(mesh)
for i in range(18):
    angle=2*math.pi*i/18;x=91*math.cos(angle);y=72*math.sin(angle)
    name='coastal_cliff_02' if i%3 else 'coast_line_02'
    spawn('Scanned coastline '+str(i),scans[name],[x,y,-10.9],(.85,.85,.85),yaw=math.degrees(angle)+90)
for i,(x,y,z,scale) in enumerate([(-28,19,0,1.1),(30,18,0,1.2),(-32,-18,0,1.),(28,-24,0,1.),(-42,32,9,.9),(40,35,12,1.1)]):
    spawn('Weathered coastal rock cluster '+str(i),scans['coast_rocks_03'],[x,y,z],(scale,scale,scale),yaw=i*63)
for i,(x,y,z) in enumerate([(-27,9,2),(-31,-10,3),(28,-4,3),(31,12,6),(-29,28,8),(-43,27,13),(33,31,15),(46,32,19),(-42,-24,4),(42,-29,3),(-62,6,4),(61,15,6)]):
    scale=.65+(i%3)*.13
    spawn('Scanned island tree '+str(i),scans['island_tree_02'],[x,y,z],(scale,scale,scale),yaw=i*47)
for a,b in [((-14,-10),(14,-10)),((14,-10),(14,13)),((14,13),(-14,13)),((-14,13),(-14,-10))]:
    dx,dy=b[0]-a[0],b[1]-a[1]
    box('Evacuation road',[(a[0]+b[0])/2,(a[1]+b[1])/2,.018],[math.hypot(dx,dy),2.4,.035],mat['road'],yaw=math.degrees(math.atan2(dy,dx)))

# Architectural detail is visual; conservative hidden collision envelopes match
# the prior navigation map within the mission area.
box('Ruin collision proxy',[-2,-2,1.5],[3,3,3],mat['concrete'],hidden=True,collision=True)
for x in (-3.38,-.62):box('Damaged wall',[x,-2,1.35],[.22,3,2.7],mat['concrete'])
box('Ruin back wall',[-2,-.62,1.45],[3,.22,2.9],mat['concrete'])
for x in (-3.08,-.92):box('Ruin entrance pillar',[x,-3.38,1.3],[.7,.22,2.6],mat['concrete'])
box('Ruin entrance lintel',[-2,-3.38,2.48],[1.5,.25,.45],mat['concrete'])
for i in range(9):box('Scattered masonry',[-3.1+(i%3)*.6,-3.25+(i//3)*.35,.12],[.4,.25,.2],mat['concrete'],yaw=i*19)
box('Watchtower collision proxy',[5,4,4.5],[2.5,2.5,9],mat['concrete'],hidden=True,collision=True)
box('Watchtower shaft',[5,4,3.6],[1.8,1.8,7.2],mat['concrete'])
box('Watchtower cabin',[5,4,7.9],[2.35,2.35,1.4],mat['white'])
box('Watchtower roof',[5,4,8.85],[2.5,2.5,.18],mat['steel'])
for sign in (-1,1):
    for offset in (-.65,0,.65):
        box('Watchtower window',[5+offset,4+sign*1.18,8.0],[.45,.025,.65],mat['dark'])
        box('Watchtower side window',[5+sign*1.18,4+offset,8.0],[.025,.45,.65],mat['dark'])

# Background harbour/hangars/tents are outside the active mission geofence.
for index,x in enumerate((-21,-3,15)):
    y=24
    box('Hangar side wall',[x,y-4,1.6],[14,.22,3.2],mat['concrete'],collision=True)
    box('Hangar side wall',[x,y+4,1.6],[14,.22,3.2],mat['concrete'],collision=True)
    box('Hangar rear wall',[x-7,y,1.6],[.22,8,3.2],mat['concrete'],collision=True)
    spawn('Arched hangar roof',roof,[x,y,3.2],mat=mat['roof'])
    for off in (-3,-1,1,3):box('Hangar rear window',[x-7.13,y+off,2.2],[.025,1.1,.7],mat['dark'])
    for off in (-5,0,5):box('Roof structural rib',[x+off,y,3.16],[.12,8.15,.12],mat['steel'])
for index,x in enumerate((-22,-15,-8)):
    y=-22
    box('Medical tent wall',[x,y,1.1],[5,3,2.2],mat['green'],collision=True)
    box('Medical tent pitched roof',[x,y-.78,2.43],[5.3,1.8,.14],mat['green'],pitch=0)
    box('Medical tent door',[x+2.51,y,1.0],[.025,1.1,1.9],mat['dark'])
for i in range(9):spawn('Harbour road barrier',barrier,[-14+i*3.8,15.5,.05],mat=mat['concrete'])
box('Pier deck',[37,18,-.2],[3,18,.5],mat['concrete'],collision=True)
for y in (10,14,18,22,26):
    for x in (35.8,38.2):spawn('Pier piling',cylinder,[x,y,-2.5],(.25,.25,5),mat=mat['steel'])
for i,(x,y) in enumerate(((-20,15),(-20,18),(-24,18),(20,-21),(24,-21))):
    box('Relief cargo container',[x,y,1.3],[5.8,2.4,2.6],mat['steel'],collision=True)
    for rib in range(10):box('Container corrugation',[x-2.6+rib*.55,y-1.22,1.3],[.08,.04,2.45],mat['concrete'])

# Landing area and scene-domain entities. Role colours are declared cues.
spawn('Landing pad',cylinder,[-12,-9,.025],(2.8,2.8,.05),mat=mat['dark'])
box('Pad marking H1',[-12.45,-9,.057],[.16,1.5,.015],mat['white'])
box('Pad marking H2',[-11.55,-9,.057],[.16,1.5,.015],mat['white'])
box('Pad marking H3',[-12,-9,.057],[.9,.16,.015],mat['white'])
for entity in scene['simulator_and_evaluator_only']['entities']:
    p=entity['position'];name=entity['id'];kind=entity['class'];entity_actors=[]
    if kind in ('injured_person','hostile_unit'):
        standing=kind=='hostile_unit'
        actor=spawn(name,clothed_standing if standing else clothed_prone,[p[0],p[1],.025],yaw=0,mat=human_material)
        entity_actors=[actor]
    elif kind=='waste':
        entity_actors=[box(name,[p[0],p[1],.12],[.5,.32,.24],mat['plastic'])]
    elif kind=='mine':
        entity_actors=[spawn(name,cylinder,[p[0],p[1],.06],(.46,.46,.12),mat=mat['mine']),
                       spawn(name+' center',cylinder,[p[0],p[1],.14],(.15,.15,.08),mat=mat['mine'])]
        for detail in range(8):
            angle=detail*math.pi/4
            entity_actors.append(spawn(name+' inert casing detail '+str(detail),cylinder,
                [p[0]+.18*math.cos(angle),p[1]+.18*math.sin(angle),.126],(.024,.024,.015),mat=mat['steel']))
    else:
        entity_actors=[spawn(name,inert_prop,[p[0],p[1],.04],yaw=17)]
        for slot,entry in enumerate(inert_prop.get_editor_property('static_materials')):
            key='steel' if 'metal' in str(entry.material_slot_name) else 'dark'
            entity_actors[0].static_mesh_component.set_material(slot,mat[key])
    labels.append({**entity,'actor_names':[a.get_name() for a in entity_actors]})

# Mobile loading mast: physically collidable but not a hostile or weapon.
moving=box('Mobile loading mast',[0,-6,3.5],[1.2,1.2,7],mat['yellow'],collision=True,movable=True)

player=actors.spawn_actor_from_class(ue.PlayerStart,ue.Vector(0,0,0),ue.Rotator())
player.set_actor_label('World coordinate origin; vehicle position supplied by settings')
sun=actors.spawn_actor_from_class(ue.DirectionalLight,ue.Vector(0,0,15000),ue.Rotator(pitch=-38,yaw=-28,roll=0))
light=sun.get_component_by_class(ue.DirectionalLightComponent);light.set_mobility(ue.ComponentMobility.MOVABLE)
light.set_editor_property('intensity',10.);light.set_editor_property('atmosphere_sun_light',True)
actors.spawn_actor_from_class(ue.SkyAtmosphere,ue.Vector(0,0,0),ue.Rotator())
sky=actors.spawn_actor_from_class(ue.SkyLight,ue.Vector(0,0,12000),ue.Rotator())
sky_component=sky.get_component_by_class(ue.SkyLightComponent);sky_component.set_mobility(ue.ComponentMobility.MOVABLE)
sky_component.set_editor_property('intensity',1.0)
fog=actors.spawn_actor_from_class(ue.ExponentialHeightFog,ue.Vector(0,0,-300),ue.Rotator())
fog_component=fog.get_component_by_class(ue.ExponentialHeightFogComponent)
fog_component.set_editor_property('fog_density',.006);fog_component.set_editor_property('start_distance',2000.)
levels.save_current_level();ue.EditorAssetLibrary.save_directory(CONTENT,only_if_is_dirty=True,recursive=True)
manifest={**scene,'annotation_entities':labels,'moving_obstacle_actor':moving.get_name(),
          'rendering_scope':'Sculpted island, CC0 coastal scans and textured MakeHuman-derived clothed people; inert hazard props',
          'map_asset':CONTENT+'/CoastalRescue'}
output=ROOT/'runtime/unreal/SKYFORGE/scene-manifest.json';output.write_text(json.dumps(manifest,indent=2))
config=ROOT/'runtime/unreal/SKYFORGE/Config/DefaultEngine.ini'
text=config.read_text().replace('/Engine/Maps/Entry',CONTENT+'/CoastalRescue');config.write_text(text)
ue.log('SKYFORGE coastal level saved: '+str(output))
