"""Self-contained coastal simulation generator, physical X3 rotor backend."""
from pathlib import Path
import copy
import json
import math
import shutil
import xml.etree.ElementTree as ET
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
COLORS = {1: (0.04,0.65,0.85), 2:(0.24,0.40,0.08), 3:(0.13,0.12,0.14),
          4:(0.95,0.31,0.035), 5:(0.35,0.10,0.62)}
CLASSES = {1:"waste", 2:"mine", 3:"weapon", 4:"injured_person", 5:"hostile_unit"}


def child(parent, tag, text=None, **attrs):
    node=ET.SubElement(parent,tag,attrs)
    if text is not None: node.text=str(text)
    return node


def shape(link, name, kind, dimensions, pose, color, collision=False):
    visual=child(link,"visual",name=name)
    child(visual,"pose"," ".join(map(str,pose)))
    geo=child(visual,"geometry")
    primitive=child(geo,kind)
    if kind=="box": child(primitive,"size"," ".join(map(str,dimensions)))
    elif kind=="sphere": child(primitive,"radius",dimensions[0])
    elif kind in ("cylinder","capsule"):
        child(primitive,"radius",dimensions[0]); child(primitive,"length",dimensions[1])
    material=child(visual,"material")
    child(material,"ambient"," ".join(map(str,[*color,1])))
    child(material,"diffuse"," ".join(map(str,[*color,1])))
    if collision:
        col=child(link,"collision",name=name+"_collision")
        col.append(copy.deepcopy(visual.find("pose"))); col.append(copy.deepcopy(geo))
    return visual


def model(world,name,position,static=True,label=None):
    m=child(world,"model",name=name)
    child(m,"static",str(static).lower())
    child(m,"pose"," ".join(map(str,[*position,0,0,0])))
    link=child(m,"link",name="body")
    if label is not None:
        p=child(m,"plugin",filename="gz-sim-label-system",name="gz::sim::systems::Label")
        child(p,"label",label)
    return m,link


def camera(link, name="downward", annotations=False, pose="0 0 -0.12 0 1.57079632679 0"):
    sensor=child(link,"sensor",name=name,type="rgbd_camera")
    child(sensor,"pose",pose); child(sensor,"topic","/skyforge/camera")
    child(sensor,"always_on","true"); child(sensor,"update_rate",20)
    cam=child(sensor,"camera"); child(cam,"horizontal_fov",1.2)
    image=child(cam,"image"); child(image,"width",640); child(image,"height",480); child(image,"format","R8G8B8")
    clip=child(cam,"clip"); child(clip,"near",0.08); child(clip,"far",60)
    if annotations:
        bbox=child(link,"sensor",name="annotation_camera",type="boundingbox_camera")
        child(bbox,"pose",pose); child(bbox,"topic","/skyforge/labels")
        child(bbox,"always_on","true"); child(bbox,"update_rate",20)
        bc=copy.deepcopy(cam); child(bc,"box_type","visible_2d"); bbox.append(bc)


def create_world(seed=11, dataset=False, rich=True):
    rng=np.random.default_rng(seed)
    target=ROOT/"sim"/"generated"; target.mkdir(parents=True,exist_ok=True)
    tree=ET.parse(ROOT/"sim/smoke/multicopter-upstream.sdf")
    tree.getroot().set("version","1.9")
    world=tree.getroot().find("world"); world.set("name","skyforge")
    for include in list(world.findall("include")): world.remove(include)
    world.find("physics/max_step_size").text="0.004"
    # The sea is a visual plane outside the navigable sand patch.
    ground=world.find("model[@name='ground_plane']")
    material=ground.find("link/visual/material")
    material.find("ambient").text="0.56 0.47 0.31 1"
    material.find("diffuse").text="0.75 0.65 0.44 1"
    m,l=model(world,"sea",[0,30,-0.08])
    shape(l,"water","box",[120,34,0.1],[0,0,0,0,0,0],[0.025,0.26,0.40])
    if not dataset:
        m,l=model(world,"observer_camera",[25,-30,28])
        sensor=child(l,"sensor",name="observer",type="camera")
        child(sensor,"pose","0 0 0 0 0.62 2.2655");child(sensor,"topic","/skyforge/observer")
        child(sensor,"always_on","true");child(sensor,"update_rate",8)
        cam=child(sensor,"camera");child(cam,"horizontal_fov",1.05)
        image=child(cam,"image");child(image,"width",800);child(image,"height",450);child(image,"format","R8G8B8")
        clip=child(cam,"clip");child(clip,"near",.1);child(clip,"far",150)
    m,l=model(world,"base",[-12,-9,0.01])
    shape(l,"landing_pad","cylinder",[1.4,0.04],[0,0,0,0,0,0],[0.16,0.19,0.23])
    shape(l,"cross1","box",[1.6,0.2,0.05],[0,0,0.04,0,0,0],[0.9,0.95,0.95])
    shape(l,"cross2","box",[0.2,1.6,0.05],[0,0,0.04,0,0,0],[0.9,0.95,0.95])
    obstacles=[{"id":"ruin_a","center":[-2,-2,1.5],"size":[3,3,3]},
               {"id":"tower","center":[5,4,4.5],"size":[2.5,2.5,9]}]
    for ob in obstacles:
        m,l=model(world,ob["id"],ob["center"])
        shape(l,"concrete","box",ob["size"],[0,0,0,0,0,0],[0.35,0.36,0.35],True)
    entities=[]
    positions={1:[(-8,-2),(10,6),(0,9)],2:[(1,0),(7,-7)],3:[(-7,6)],4:[(-7,-5),(9,-3),(3,9)],5:[(10,9)]}
    for label,points in positions.items():
        for i,(x,y) in enumerate(points):
            if dataset:
                x+=float(rng.uniform(-1,1)); y+=float(rng.uniform(-1,1))
            name=f"{CLASSES[label]}_{i}"
            m,l=model(world,name,[x,y,0.03],label=label)
            color=np.clip(np.array(COLORS[label])*rng.uniform(0.88,1.12,3),0,1).tolist()
            if label==1:
                shape(l,"plastic_container","box",[0.5,0.32,0.18],[0,0,0.09,0,0,0.2],color)
            elif label==2:
                shape(l,"passive_hazard_disc","cylinder",[0.23,0.10],[0,0,0.05,0,0,0],color)
                shape(l,"center","cylinder",[0.08,0.08],[0,0,0.12,0,0,0],color)
            elif label==3:
                shape(l,"passive_prop_body","box",[0.68,0.12,0.10],[0,0,0.07,0,0,0.3],color)
                shape(l,"passive_prop_grip","box",[0.12,0.24,0.10],[-0.1,-0.12,0.07,0,0,0.3],color)
            elif label==4:
                # Orange emergency clothing is an explicit scenario role cue.
                shape(l,"torso","capsule",[0.17,0.45],[0,0,0.18,0,math.pi/2,0],color)
                shape(l,"head","sphere",[0.14],[0.47,0,0.18,0,0,0],[0.65,0.44,0.31])
                for sign in (-1,1):
                    shape(l,f"leg{sign}","capsule",[0.07,0.43],[-0.50,sign*0.12,0.11,0,math.pi/2,0],color)
                    shape(l,f"arm{sign}","capsule",[0.065,0.36],[0.02,sign*0.27,0.11,0,math.pi/2,sign*0.2],color)
            else:
                shape(l,"uniform","capsule",[0.20,0.6],[0,0,0.8,0,0,0],color)
                shape(l,"head","sphere",[0.14],[0,0,1.3,0,0,0],[0.65,0.44,0.31])
                for sign in (-1,1):
                    shape(l,f"leg{sign}","capsule",[0.08,0.5],[0,sign*0.12,0.3,0,0,0],color)
            entities.append({"id":name,"class":CLASSES[label],"label":label,"position":[x,y,0],
                             "urgency": (1,3,2)[i] if label==4 else None})
    # A physical moving obstacle driven by a separate known control script.
    m,l=model(world,"moving_obstacle",[0,-6,3.5],static=False)
    child(l,"gravity","false")
    inertial=child(l,"inertial"); child(inertial,"mass",20)
    inertia=child(inertial,"inertia")
    for key in ("ixx","iyy","izz"): child(inertia,key,5)
    shape(l,"body","box",[1.2,1.2,7],[0,0,0,0,0,0],[0.62,0.61,0.56],True)
    child(m,"plugin",filename="gz-sim-velocity-control-system",name="gz::sim::systems::VelocityControl")
    if rich and not dataset:
        from .scenery import enrich
        enrich(world,ROOT,child,model,shape)
    # Independent world pose publishing supports the evaluator, not mission vision.
    for m in world.findall("model"):
        p=child(m,"plugin",filename="gz-sim-pose-publisher-system",name="gz::sim::systems::PosePublisher")
        child(p,"publish_model_pose","true"); child(p,"publish_link_pose","false")
        child(p,"use_pose_vector_msg","true"); child(p,"update_frequency",20)
    child(world,"plugin",filename="gz-sim-apply-link-wrench-system",name="gz::sim::systems::ApplyLinkWrench")
    if dataset:
        m,l=model(world,"dataset_camera",[0,0,7])
        camera(l,annotations=True,pose="0 0 0 0 1.57079632679 0")
    else:
        source=Path("/root/.gz/fuel/fuel.gazebosim.org/openrobotics/models/x3 uav/4")
        destination=ROOT/"sim/models/x3"
        if not destination.exists(): shutil.copytree(source,destination)
        drone=ET.parse(destination/"model.sdf").getroot().find("model")
        drone.find("pose").text="-12 -9 0.055 0 0 0"
        upstream=ET.parse(ROOT/"sim/smoke/multicopter-upstream.sdf").getroot().find("world/include")
        for plugin in upstream.findall("plugin"): drone.append(copy.deepcopy(plugin))
        base=drone.find("link[@name='X3/base_link']")
        for visual in drone.findall(".//visual"):child(visual,"visibility_flags",2)
        camera(base)
        scan=child(base,"sensor",name="safety_lidar",type="gpu_lidar")
        child(scan,"topic","/skyforge/lidar");child(scan,"always_on","true");child(scan,"update_rate",20)
        lidar=child(scan,"lidar");scan_def=child(lidar,"scan");horizontal=child(scan_def,"horizontal")
        child(lidar,"visibility_mask",1)
        for key,value in (("samples",180),("resolution",1),("min_angle",-math.pi),("max_angle",math.pi)):
            child(horizontal,key,value)
        ranges=child(lidar,"range")
        for key,value in (("min",.15),("max",30),("resolution",.02)):child(ranges,key,value)
        shape(base,"medical_pod_visual","box",[0.32,0.24,0.10],[0,0,-0.02,0,0,0],[0.92,0.94,0.93])
        world.append(drone)
        if Path("/opt/skyforge/plugins/libSkyforgeWind.so").exists():
            wind=child(world,"plugin",filename="libSkyforgeWind.so",name="SkyforgeWind")
            child(wind,"model_name","x3");child(wind,"cd_area",.045)
    path=target/(f"dataset-{seed}.sdf" if dataset else "coast.sdf")
    tree.write(path,encoding="unicode")
    manifest={"seed":seed,"bounds":[-15,-12,15,12],"base":[-12,-9,0.055],"entities":entities,"obstacles":obstacles,
              "note":"Evaluator/dataset ground truth. Never supply hidden target positions to runtime AI."}
    path.with_suffix(".json").write_text(json.dumps(manifest,indent=2))
    return path,manifest


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser(); parser.add_argument("--dataset",action="store_true"); parser.add_argument("--seed",type=int,default=11)
    args=parser.parse_args(); print(create_world(args.seed,args.dataset)[0])
