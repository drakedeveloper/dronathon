"""Author distance LODs for downloaded scans; preserve full near-view geometry."""
import json
from pathlib import Path
import unreal as ue

root=Path(__file__).resolve().parents[1]
ue.load_module('StaticMeshEditor')
subsystem=ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem);records=[]
if subsystem is None:raise RuntimeError('StaticMeshEditor subsystem not available in this authoring mode')
for name in ('coastal_cliff_02','coast_line_02','coast_rocks_03','island_tree_02'):
    mesh=ue.load_asset('/Game/SKYFORGE/Meshes/'+name)
    if mesh is None:raise RuntimeError('Missing imported scan: '+name)
    options=ue.StaticMeshReductionOptions();options.set_editor_property('auto_compute_lod_screen_size',False)
    reductions=[]
    for fraction,screen in [(1.,1.),(.15,.65),(.03,.30)]:
        setting=ue.StaticMeshReductionSettings();setting.set_editor_property('percent_triangles',fraction)
        setting.set_editor_property('screen_size',screen);reductions.append(setting)
    options.set_editor_property('reduction_settings',reductions)
    count=subsystem.set_lods(mesh,options)
    if count<3:raise RuntimeError('LOD generation failed: '+name)
    ue.EditorAssetLibrary.save_loaded_asset(mesh)
    record={'mesh':name,'lod_count':count,'triangle_fractions':[1.,.15,.03],'screen_sizes':[1.,.65,.30]}
    records.append(record);ue.log('SKYFORGE LOD '+json.dumps(record))
(root/'runtime/unreal/SKYFORGE/mesh-lods.json').write_text(json.dumps(records,indent=2))
