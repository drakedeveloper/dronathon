"""Offline native RGB/instance-mask capture. Never used by flight agents.

Pauses and teleports the simulator explicitly for data generation. This is not
flight evidence. Split seeds/positions are recorded; held-out test stays unused
until a final model is frozen. Same authored scene remains a domain limitation.
"""
import argparse
import json
import math
from pathlib import Path
import time
import cv2
import numpy as np
from skyforge.airsim_backend import AirSimBackend,binary_data
from skyforge.scene import ROOT

# First instance colours from the pinned Cosys colour generator. Background 0
# is white; captures are rejected if assigned entity colours cannot be found.
PALETTE=np.array([(255,255,255),(255,255,127),(255,127,255),(255,127,127),
    (127,255,255),(127,255,127),(127,127,255),(127,127,127),
    (255,255,191),(255,127,191),(127,255,191)],np.int16)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--train',type=int,default=100)
    parser.add_argument('--val',type=int,default=25);parser.add_argument('--test',type=int,default=25)
    args=parser.parse_args();out=ROOT/'data/native';(out/'images').mkdir(parents=True,exist_ok=True)
    scene=json.loads((ROOT/'runtime/unreal/SKYFORGE/scene-manifest.json').read_text())
    backend=AirSimBackend(port=41461);rpc=backend.commands
    settings=json.loads(rpc.call('getSettingsString'))
    if settings.get('SkyforgeScenario')!='coastal-rescue':raise RuntimeError('Wrong simulator scene')
    if rpc.call('isApiControlEnabled','SKYFORGE'):
        state=backend.state()
        if np.linalg.norm(state['v'])>.15 or abs(state['p'][2])>.5:raise RuntimeError('Land mission before dataset mode')
    home=rpc.call('simGetVehiclePose','SKYFORGE')
    spawn=settings['Vehicles']['SKYFORGE'];records=[];assigned=[]
    try:
        rpc.call('armDisarm',False,'SKYFORGE');rpc.call('simPause',True)
        names=rpc.call('simListInstanceSegmentationObjects')
        for name in names:
            if not rpc.call('simSetSegmentationObjectID',name,0,False):raise RuntimeError('Cannot reset annotation: '+name)
        for identity,entity in enumerate(scene['annotation_entities'],1):
            matches=[name for name in names if any('_'+actor+'_' in name for actor in entity['actor_names'])]
            if not matches:raise RuntimeError('Missing annotation meshes: '+entity['id'])
            for name in matches:
                if not rpc.call('simSetSegmentationObjectID',name,identity,False):raise RuntimeError('Cannot annotate '+name)
            assigned.append((identity,entity))
        for split,seed,count in [('train',811,args.train),('val',822,args.val),('test',833,args.test)]:
            rng=np.random.default_rng(seed)
            for index in range(count):
                entity=scene['annotation_entities'][index%len(assigned)]
                x,y,_=entity['position']
                if index%6==0:x,y=rng.uniform(-14,14),rng.uniform(-11,11)
                else:x+=rng.uniform(-3,3);y+=rng.uniform(-2,2)
                z=float(rng.uniform(4,10));angle=float(rng.uniform(-math.pi,math.pi))
                pose={'position':{'x_val':float(y-spawn['X']),'y_val':float(x-spawn['Y']),'z_val':float(-z-spawn['Z'])},
                      'orientation':{'x_val':0.,'y_val':0.,'z_val':math.sin(angle/2),'w_val':math.cos(angle/2)}}
                rpc.call('simSetVehiclePose',pose,True,'SKYFORGE')
                rpc.call('simPause',False);time.sleep(.07);rpc.call('simPause',True)
                requests=[{'camera_name':'downward','image_type':kind,'pixels_as_float':False,'compress':True} for kind in (0,5)]
                images=backend.images(requests)
                rgb,mask=[cv2.imdecode(np.frombuffer(binary_data(item['image_data_uint8']),np.uint8),cv2.IMREAD_COLOR) for item in images]
                if rgb is None or mask is None or rgb.shape!=mask.shape:raise RuntimeError('RGB/annotation calibration mismatch')
                if abs(images[0]['time_stamp']-images[1]['time_stamp'])>75_000_000:raise RuntimeError('Unsynchronized annotation capture')
                annotations=[]
                for identity,target in assigned:
                    match=np.max(abs(mask.astype(np.int16)-PALETTE[identity][::-1]),axis=2)<=3
                    ys,xs=np.where(match)
                    if len(xs)<12:continue
                    box=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
                    if box[2]-box[0]<4 or box[3]-box[1]<4:continue
                    annotations.append({'label':target['label'],'bbox_xyxy':box,'entity':target['id'],'visible_pixels':int(len(xs))})
                filename=f'images/{split}-{index:04}.jpg';cv2.imwrite(str(out/filename),rgb,[cv2.IMWRITE_JPEG_QUALITY,94])
                records.append({'image':filename,'split':split,'pose_seed':seed,'camera_pose':pose,'boxes':annotations,
                                'image_size_wh':[rgb.shape[1],rgb.shape[0]],'scene':'coastal-rescue-v2'})
                if index%10==0:print(split,index,'visible objects',len(annotations),flush=True)
                (out/'manifest.json').write_text(json.dumps(records,indent=2))
        if not any(item['boxes'] for item in records):raise RuntimeError('No annotations matched; verify palette before training')
    finally:
        rpc.call('simSetVehiclePose',home,True,'SKYFORGE');rpc.call('simPause',False)
        backend.close()
    print('Captured',len(records),'offline images; inspect overlays before training',flush=True)


if __name__=='__main__':main()
