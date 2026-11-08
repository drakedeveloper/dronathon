"""Original coastal rescue art direction; bounded architecture and CC0 scans.

Mission collision envelopes are unchanged. Scanned cliffs/harbour decorations
sit outside mission bounds. Fine architecture is contained in known obstacles.
"""
import math
from pathlib import Path


def enrich(world, root, child, model, shape):
    assets=root/'sim/assets'
    def texture(visual,albedo,normal=None,roughness=.85):
        material=visual.find('material')
        if material is None:material=child(visual,'material')
        for tag in ('ambient','diffuse'):
            element=material.find(tag)
            if element is None:element=child(material,tag)
            element.text='1 1 1 1'
        pbr=child(material,'pbr');metal=child(pbr,'metal')
        child(metal,'albedo_map',str(albedo));child(metal,'roughness',roughness);child(metal,'metalness',0)
        if normal:child(metal,'normal_map',str(normal),type='tangent')

    def scanned(name,asset,position,scale=(1,1,1),yaw=0):
        mesh=assets/asset/(asset+'.obj')
        if not mesh.exists():return
        m,l=model(world,name,position)
        visual=child(l,'visual',name='scan');child(visual,'pose',f'0 0 0 0 0 {yaw}')
        geometry=child(visual,'geometry');g=child(geometry,'mesh');child(g,'uri',str(mesh));child(g,'scale',' '.join(map(str,scale)))
        folder=assets/asset/'textures'
        texture(visual,folder/(asset+'_diff_1k.jpg'),folder/(asset+'_nor_gl_1k.jpg'))

    ground=world.find("model[@name='ground_plane']/link/visual")
    if (assets/'sand.obj').exists():
        geometry=ground.find('geometry');geometry.clear();mesh=child(geometry,'mesh');child(mesh,'uri',str(assets/'sand.obj'))
        texture(ground,assets/'coast_sand_02/diffuse.jpg',assets/'coast_sand_02/normal.jpg')
    # Facade details stay within the existing 3x3x3 m navigation obstacle.
    ruin=world.find("model[@name='ruin_a']/link")
    ruin.remove(ruin.find("visual[@name='concrete']"))
    stone=[.48,.46,.40];dark=[.10,.13,.14]
    for name,dimensions,pose in (
        ('west_wall',[.22,3,2.8],[-1.38,0,-.1,0,0,0]),
        ('east_wall',[.22,3,2.4],[1.38,0,-.3,0,0,0]),
        ('rear_wall',[3,.22,2.7],[0,1.38,-.15,0,0,0]),
        ('door_left',[.85,.22,2.5],[-1.05,-1.38,-.25,0,0,0]),
        ('door_right',[.85,.22,2.5],[1.05,-1.38,-.25,0,0,0]),
        ('lintel',[1.3,.26,.45],[0,-1.35,1,0,0,0]),
        ('broken_roof',[2.5,1.45,.16],[0,.65,1.25,0,0,.06])):
        shape(ruin,name,'box',dimensions,pose,stone)
    for i in range(6):
        shape(ruin,f'masonry_{i}','box',[.43,.26,.23],[-1.12+i*.44,-1.4,-1.35,0,0,.05*(i%3)], [.37,.35,.30])
    tower=world.find("model[@name='tower']/link")
    visual=tower.find("visual[@name='concrete']");tower.remove(visual)
    shape(tower,'shaft','box',[1.8,1.8,7.2],[0,0,-.9,0,0,0],stone)
    shape(tower,'watch_cabin','box',[2.35,2.35,1.3],[0,0,3.35,0,0,0],stone)
    shape(tower,'roof','box',[2.5,2.5,.15],[0,0,4.35,0,0,0],[.24,.26,.25])
    for sign in (-1,1):
        for x in (-.65,0,.65):
            shape(tower,f'window_{sign}_{x}','box',[.48,.025,.65],[x,sign*1.18,3.45,0,0,0],dark)
        for y in (-.65,0,.65):
            shape(tower,f'side_window_{sign}_{y}','box',[.025,.48,.65],[sign*1.18,y,3.45,0,0,0],dark)
    # Repeated scans create a rocky boundary on the shore and the western ridge.
    for i,x in enumerate(range(-23,25,5)):
        scanned(f'shore_cliff_{i}','rock_face_01',[x,16,-.3],(1.2,.8,.75),math.pi)
    for i,y in enumerate((-12,-6,0,6,12)):
        scanned(f'west_cliff_{i}','rock_face_01',[-19,y,-.4],(1,1,1.15),math.pi/2)
    for i,x in enumerate((-11,-7,-3,1,5,9)):
        scanned(f'sea_barrier_{i}','concrete_road_barrier_02',[x,13.5,.05],(.8,.8,.8))
    # Harbour architecture outside the navigable area, with distinct silhouettes.
    for i,x in enumerate((-12,1,13)):
        m,l=model(world,f'harbour_store_{i}',[x,24,1.5])
        shape(l,'walls','box',[7,5,3],[0,0,0,0,0,0],[.42,.44,.42])
        for sign in (-1,1):
            shape(l,f'pitched_roof_{sign}','box',[7.4,2.8,.18],[0,sign*1.2,1.75,sign*-.28,0,0],[.24,.27,.29])
        for xw in (-2,0,2):
            shape(l,f'opening_{xw}','box',[1.2,.03,1.6],[xw,-2.52,-.1,0,0,0],dark)
    m,l=model(world,'rescue_pier',[20,19,.3])
    shape(l,'deck','box',[3,12,.4],[0,0,0,0,0,0],[.35,.29,.21])
    for y in (-4,0,4):
        for x in (-1.2,1.2):shape(l,f'piling_{x}_{y}','cylinder',[.15,2],[x,y,-.6,0,0,0],[.22,.19,.14])
