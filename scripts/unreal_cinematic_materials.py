"""Unreal material graphs for animated coastal water; no external shader code."""
import unreal as ue


def ocean_material(folder):
    path=folder+'/CoastalWaterV2';existing=ue.load_asset(path)
    if existing:return existing
    mat=ue.AssetToolsHelpers.get_asset_tools().create_asset('CoastalWaterV2',folder,ue.Material,ue.MaterialFactoryNew())
    mat.set_editor_property('two_sided',True)
    lib=ue.MaterialEditingLibrary
    def node(kind,x=0,y=0):return lib.create_material_expression(mat,kind,x,y)
    position=node(ue.MaterialExpressionWorldPosition,-700,0)
    clock=node(ue.MaterialExpressionTime,-700,150)
    def custom(code,x,y):
        expression=node(ue.MaterialExpressionCustom,x,y)
        expression.set_editor_property('code',code)
        expression.set_editor_property('output_type',ue.CustomMaterialOutputType.CMOT_FLOAT3)
        inputs=[]
        for name in ('P','T'):
            pin=ue.CustomInput();pin.set_editor_property('input_name',name);inputs.append(pin)
        expression.set_editor_property('inputs',inputs)
        lib.connect_material_expressions(position,'XYZ',expression,'P')
        lib.connect_material_expressions(clock,'',expression,'T')
        return expression
    waves=custom('float a=P.x*0.012+P.y*0.008-T*1.1; float b=P.x*-0.021+P.y*0.016-T*1.6; return float3(0,0,7*sin(a)+3*sin(b));',-350,0)
    normal=custom('float a=P.x*0.012+P.y*0.008-T*1.1; float b=P.x*-0.021+P.y*0.016-T*1.6; return normalize(float3(-0.16*cos(a)+0.09*cos(b),-0.11*cos(a)-0.07*cos(b),1));',-350,180)
    lib.connect_material_property(waves,'',ue.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    lib.connect_material_property(normal,'',ue.MaterialProperty.MP_NORMAL)
    fresnel=node(ue.MaterialExpressionFresnel,-500,350)
    lerp=node(ue.MaterialExpressionLinearInterpolate,-100,350)
    for pin,color in [('A',(.008,.075,.09)),('B',(.04,.27,.31))]:
        c=node(ue.MaterialExpressionConstant3Vector,-350,400 if pin=='A' else 500)
        c.set_editor_property('constant',ue.LinearColor(*color,1))
        lib.connect_material_expressions(c,'',lerp,pin)
    lib.connect_material_expressions(fresnel,'',lerp,'Alpha')
    lib.connect_material_property(lerp,'',ue.MaterialProperty.MP_BASE_COLOR)
    for prop,value in [(ue.MaterialProperty.MP_ROUGHNESS,.10),(ue.MaterialProperty.MP_SPECULAR,.75),(ue.MaterialProperty.MP_METALLIC,.18)]:
        c=node(ue.MaterialExpressionConstant);c.set_editor_property('r',value);lib.connect_material_property(c,'',prop)
    lib.recompile_material(mat);ue.EditorAssetLibrary.save_loaded_asset(mat)
    return mat
