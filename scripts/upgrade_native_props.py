"""Unreal commandlet: replace the block proxy with the original exterior prop."""
import json
from pathlib import Path
import unreal as ue

ROOT=Path(__file__).resolve().parents[1]
actors=ue.get_editor_subsystem(ue.EditorActorSubsystem)
levels=ue.get_editor_subsystem(ue.LevelEditorSubsystem)
levels.load_level('/Game/SKYFORGE/CoastalRescue')
manifest_path=ROOT/'runtime/unreal/SKYFORGE/scene-manifest.json'
manifest=json.loads(manifest_path.read_text())
entity=next(e for e in manifest['annotation_entities'] if e['class']=='weapon')
task=ue.AssetImportTask();task.filename=str(ROOT/'runtime/unreal/source_assets/inert_field_prop_v1.obj')
task.destination_path='/Game/SKYFORGE/Meshes';task.destination_name='inert_field_prop_v1';task.automated=True;task.replace_existing=True;task.save=True
options=ue.FbxImportUI();options.import_mesh=True;options.import_as_skeletal=False;options.import_materials=False;options.import_textures=False
options.mesh_type_to_import=ue.FBXImportType.FBXIT_STATIC_MESH
data=options.static_mesh_import_data;data.combine_meshes=True;data.import_uniform_scale=100.;data.convert_scene=False;data.convert_scene_unit=False;data.auto_generate_collision=False;task.options=options
ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
mesh=ue.load_asset(task.imported_object_paths[0])
for old in actors.get_all_level_actors():
    if old.get_name() in entity['actor_names']:actors.destroy_actor(old)
p=entity['position'];actor=actors.spawn_actor_from_class(ue.StaticMeshActor,ue.Vector(p[1]*100,p[0]*100,4),ue.Rotator(pitch=0,yaw=73,roll=0))
actor.set_actor_label('Inert exterior weapon prop / detection only')
component=actor.static_mesh_component;component.set_mobility(ue.ComponentMobility.STATIC);component.set_static_mesh(mesh)
component.set_collision_enabled(ue.CollisionEnabled.NO_COLLISION);actor.set_actor_enable_collision(False)
for i,slot in enumerate(mesh.get_editor_property('static_materials')):
    name=str(slot.material_slot_name);material=ue.load_asset('/Game/SKYFORGE/Materials/'+('Steel' if 'metal' in name else 'Dark'))
    if material:component.set_material(i,material)
entity['actor_names']=[actor.get_name()];manifest['weapon_visual']='Original exterior mesh v1; no functional mechanics'
levels.save_current_level();ue.EditorAssetLibrary.save_directory('/Game/SKYFORGE',only_if_is_dirty=True,recursive=True)
manifest_path.write_text(json.dumps(manifest,indent=2));(ROOT/'configs/scenes/native-scene-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
ue.log('Upgraded inert prop: '+actor.get_name())
