"""Build the team's editable ten-minute pitch from measured release results."""
import json
from pathlib import Path
from PIL import Image
from pptx import Presentation
from pptx.util import Inches,Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE,MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN,MSO_ANCHOR
from pptx.oxml.xmlchemy import OxmlElement

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'deliverables';OUT.mkdir(exist_ok=True)
BG='F6F1E8';FG='253340';MUTED='62727A';ORANGE='946426';CYAN='387E83';GREEN='557C65'
prs=Presentation();prs.slide_width=Inches(13.333333);prs.slide_height=Inches(7.5)
summary=json.loads((ROOT/'validation/submission-summary.json').read_text())
audit=summary['mission'];timing=summary['timing'];schedule=[]


def text(slide,value,x,y,w,h,size=22,color=FG,bold=False,align=None):
    shape=slide.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h));tf=shape.text_frame
    tf.word_wrap=True;tf.margin_left=0;tf.margin_right=0;tf.margin_top=0;tf.margin_bottom=0
    for i,line in enumerate(str(value).split('\n')):
        p=tf.paragraphs[0] if i==0 else tf.add_paragraph();p.text=line;p.font.name='Segoe UI';p.font.size=Pt(size);p.font.bold=bold;p.font.color.rgb=RGBColor.from_string(color)
        if align is not None:p.alignment=align
    return shape


def slide(title,seconds,notes,backup=False):
    s=prs.slides.add_slide(prs.slide_layouts[6]);s.background.fill.solid();s.background.fill.fore_color.rgb=RGBColor.from_string(BG)
    text(s,title,.65,.48,12,1,34,bold=True)
    text(s,'SKYFORGE  /  DRONATHON 3.0',.65,7.06,8,.25,10,MUTED)
    text(s,('BACKUP  /  ' if backup else '')+str(len(prs.slides)).zfill(2),11.2,7.06,1.45,.25,10,MUTED,align=PP_ALIGN.RIGHT)
    s.notes_slide.notes_text_frame.text=f"Suggested time: {seconds} seconds.\n{notes}\nSources: dronathon.pdf; validation/submission-summary.json; configs/airframes/x500-research.json. All simulation images are actual renderer outputs."
    schedule.append({'slide':len(prs.slides),'title':title,'seconds':seconds,'backup':backup});return s


def bullets(s,items,x=.8,y=1.7,w=5.4,size=23):
    box=s.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(4.8));tf=box.text_frame;tf.word_wrap=True;tf.margin_left=0;tf.margin_top=0
    for i,item in enumerate(items):
        p=tf.paragraphs[0] if i==0 else tf.add_paragraph();p.text=item;p.font.name='Segoe UI';p.font.size=Pt(size);p.font.color.rgb=RGBColor.from_string(FG);p.space_after=Pt(18)
        properties=p._p.get_or_add_pPr();properties.set('marL','228600');properties.set('indent','-114300');bullet=OxmlElement('a:buChar');bullet.set('char','•');properties.append(bullet)


def picture(s,path,x,y,w,h):
    path=Path(path)
    if not path.exists():return
    iw,ih=Image.open(path).size;scale=min(w/iw,h/ih);ww,hh=iw*scale,ih*scale
    s.shapes.add_picture(str(path),Inches(x+(w-ww)/2),Inches(y+(h-hh)/2),width=Inches(ww),height=Inches(hh))


def box(s,label,x,y,w=2.05,h=.85,color='243847'):
    color={'243847':'E9E1D5','22515B':'DCE9E3'}.get(color,color)
    shape=s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,Inches(x),Inches(y),Inches(w),Inches(h));shape.fill.solid();shape.fill.fore_color.rgb=RGBColor.from_string(color);shape.line.color.rgb=RGBColor.from_string(CYAN)
    tf=shape.text_frame;tf.clear();tf.word_wrap=True;tf.vertical_anchor=MSO_ANCHOR.MIDDLE
    p=tf.paragraphs[0];p.text=label;p.alignment=PP_ALIGN.CENTER;p.font.name='Segoe UI';p.font.size=Pt(18);p.font.color.rgb=RGBColor.from_string(FG)
    return shape


def arrow(s,x1,y1,x2,y2,color=CYAN):
    shape=s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,Inches(x1),Inches(y1),Inches(x2),Inches(y2));shape.line.color.rgb=RGBColor.from_string(color);shape.line.width=Pt(2)
    end=OxmlElement('a:tailEnd');end.set('type','triangle');shape._element.spPr.get_or_add_ln().append(end)


def table(s,rows,x=.8,y=1.65,w=11.75,h=4.7,widths=None,size=20):
    t=s.shapes.add_table(len(rows),len(rows[0]),Inches(x),Inches(y),Inches(w),Inches(h)).table
    if widths:
        for col,width in zip(t.columns,widths):col.width=Inches(width)
    for r,row in enumerate(rows):
        for c,value in enumerate(row):
            cell=t.cell(r,c);cell.text=str(value);cell.fill.solid();cell.fill.fore_color.rgb=RGBColor.from_string('E8DDCB' if r==0 else BG)
            cell.margin_left=Inches(.14);cell.margin_right=Inches(.12);cell.margin_top=Inches(.08);cell.vertical_anchor=MSO_ANCHOR.MIDDLE
            for p in cell.text_frame.paragraphs:
                p.font.name='Segoe UI';p.font.size=Pt(size);p.font.bold=r==0;p.font.color.rgb=RGBColor.from_string(ORANGE if r==0 else FG)
    return t


s=slide('SKYFORGE',15,'Open with the mission: autonomous humanitarian reconnaissance and medical support. The objective is to detect hazards, support casualties and return safely.')
picture(s,ROOT/'station/dist/assets/site-aerial.jpg',6.6,0,6.75,7.5)
text(s,'SKYFORGE',.75,2.0,6,1,50,bold=True)
text(s,'Autonomous humanitarian\nreconnaissance & rescue support',.8,3.35,5.7,1.4,26)
text(s,'IEEE RAS & AESS ENSIT  /  DRONATHON 3.0',.8,5.6,5.7,.65,14,ORANGE)
# Remove the repeated default cover title; retain the minimal central composition.
s.shapes[0].text=''

s=slide('The mission',30,'Describe the humanitarian scenario. Mines and weapons are inert mapped hazards; hostile units are avoided. Medical delivery is simulated. Scoring prioritizes autonomy and decision intelligence, 20% each.')
bullets(s,['Explore the coastal environment and map hazards.','Locate casualties and prioritize feasible aid.','Continue through radio loss and return with reserve.'])
picture(s,ROOT/'artifacts/tactical-map-mission.png',6.8,1.55,5.8,4.9)

s=slide('Two agents. Independent flight protection.',55,'Follow the editable diagram from sensors to control. Exactly two deterministic LangGraph nodes: PerceptionAgent and PlannerAgent. No language model runs in the control loop. The radio module is asynchronous and is not a third agent.')
labels=['RGB + depth','Two detectors','Perception\nAgent','Planner\nAgent','Route shield']
for i,label in enumerate(labels):
    x=.65+i*2.55;box(s,label,x,1.9,2.05,.9,'22515B' if 'Agent' in label else '243847')
    if i<4:arrow(s,x+2.05,2.35,x+2.5,2.35)
box(s,'Classical reflex',10.85,4.25,1.85);arrow(s,11.88,2.8,11.88,4.2)
box(s,'Physical simulator',.65,4.25,2.6);arrow(s,10.8,4.68,3.3,4.68)
text(s,'bounded velocity commands',6.0,4.1,3.8,.4,16,MUTED)
box(s,'Journal + radio',6.0,5.55,2.5);box(s,'Ground station',9.1,5.55,2.5);arrow(s,8.55,5.97,9.05,5.97)
text(s,'CRC/HMAC  •  buffered replay',.8,5.6,4.7,.7,20,ORANGE)

s=slide('INIT → autonomous mission',30,'Initialization checks stationary launch, odometry, sensors, model availability and energy. Show the mission state sequence. Priority interrupts handle low energy, radio loss and revised station objectives.')
names=['INIT','EXPLORER','DÉTECTER','TRIAGE','POSÉ','RETOUR BASE','LIVRER','NAVIGUER']
for i,name in enumerate(names):
    col=i%4;row=i//4;x=.8+col*3.1;y=1.9+row*2.1;box(s,name,x,y,2.4,1)
for i in range(3):arrow(s,3.25+i*3.1,2.4,3.85+i*3.1,2.4)
arrow(s,11.3,2.95,11.3,3.95)
for i in range(3):arrow(s,10.05-i*3.1,4.5,9.4-i*3.1,4.5)
text(s,'Priority interrupts: energy reserve • link loss • authenticated goal update',.85,5.8,11.7,.8,23,ORANGE)

s=slide('DÉTECTER / from pixels to mapped objects',55,'Explain the five classes and two models. RGB letterbox preprocessing, class-wise NMS, depth and aligned pose produce ENU positions. Persistent tracks and role votes reduce unstable classifications. The displayed image is a real recorded simulator frame.')
frames=list((ROOT/'artifacts/demo-recording').glob('camera-*.jpg')); example=min(frames,key=lambda p:abs(int(p.stem.split('-')[-1])-160)) if frames else ROOT/'artifacts/live/camera.jpg'; picture(s,example,.8,1.65,6.2,4.8)
bullets(s,['Primary: waste, mines and weapons.','Secondary: injured people and hostile units.','Depth + timestamp-aligned pose localize detections.','Repeated observations maintain persistent tracks.'],7.4,1.8,5.0,21)

s=slide('TRIAGE / urgency before proximity',45,'Rank confirmed feasible casualties by urgency, then travel time. A distress beacon guides search; visual confirmation is still required. The example priorities are the scenario inputs, not a medical diagnosis from the image.')
table(s,[['Decision gate','Rule'],['1 / Confirmation','Repeated visual evidence; conservative role voting'],['2 / Feasibility','Rescue + return + landing + reserve must fit'],['3 / Medical priority','Urgency 3 → urgency 2 → urgency 1'],['4 / Tie breaker','Lower predicted travel time']],size=21)

s=slide('NAVIGUER / checked routes and local reflex',55,'A* inflates hazards and obstacles. Every shortcut and route is checked independently by the safety shield. The reflex applies bounded feedback, acceleration/jerk limits and lidar braking. It can stop a planner command without waiting for inference.')
bullets(s,['A* with inflated obstacle and exclusion geometry.','Independent route shield checks bounds and intersections.','Lidar braking, wind compensation and stale-data holds.','Authenticated goal changes preempt the current objective.'],.8,1.7,5.4,22)
picture(s,ROOT/'artifacts/tactical-map-island.png',6.9,1.6,5.6,4.9)

s=slide('Physics / an auditable X500 reference',55,'These are source-backed simulation parameters plus explicitly selected payload and battery assumptions. PX4 source hashes are in the reference JSON. Explain thrust balance and energy, rather than claiming measured physical calibration. Sources: https://github.com/PX4/PX4-gazebo-models ; configs/airframes/x500-research.json.')
text(s,'2.2543 kg',.85,1.7,5,.65,37,ORANGE,True)
text(s,'Airframe, rotors, three 50 g kits\nand a 40 g payload mount',.85,2.5,5,1.2,23)
text(s,'T = kT ω²   /   4T = mg',.85,4.1,5.7,.7,27,CYAN)
text(s,'Hover ≈ 804 rad/s\nMaximum thrust / weight = 1.547',.85,5.0,5.8,1.25,22)
text(s,'74 Wh nominal',7.2,1.7,5.4,.65,37,ORANGE,True)
text(s,'14.8 V × 5 Ah\n59.2 Wh usable assumption',7.2,2.5,5.2,1.2,23)
text(s,'E = ∫ P(t) dt / 3600',7.2,4.1,5.2,.7,27,CYAN)
text(s,'Wind-relative drag, climb and electronics\n20 Wh declared mission allowance',7.2,5.0,5.2,1.25,22)

s=slide('LIVRER → RETOUR BASE',30,'Delivery requires a confirmed casualty, a stable hover and fresh visual or depth corroboration. The evaluator checks actual position against ground truth after the flight. Delivery is virtual. The dynamic reserve includes return, descent, landing and margin.')
items=['Confirm target','Stable hover','Virtual aid','Audit position']
for i,label in enumerate(items):
    box(s,label,.8+3.1*i,1.9,2.4,1)
    if i<3:arrow(s,3.25+3.1*i,2.4,3.85+3.1*i,2.4)
bullets(s,['Recompute return energy for wind, distance and landing.','Return when reserve is threatened or supplies are delivered.','Verify touchdown before disarming.'],.85,3.65,11.7,24)

s=slide('Recorded autonomous mission',90,'Play the embedded 90-second cut. It contains actual simulator camera frames and synchronized station telemetry. The full recording is supplied separately. The telemetry panel is composed from recorded station JSON, not a browser screen capture. The clip is sped up; the source and speed factor are retained in artifacts/demo-recording/recording.json.')
movie=OUT/'SKYFORGE-pitch-edited.mp4';poster=min((ROOT/'artifacts/demo-recording').glob('observer-*.jpg'),key=lambda p:abs(int(p.stem.split('-')[-1])-400))
if movie.exists():s.shapes.add_movie(str(movie),Inches(.8),Inches(1.5),Inches(11.75),Inches(4.95),poster_frame_image=str(poster),mime_type='video/mp4')
else:picture(s,poster,.8,1.5,11.75,4.95)
text(s,'Actual simulation + synchronized station telemetry  /  accelerated replay',.85,6.55,11.5,.35,15,MUTED)

s=slide('Resilience / autonomy survives the outage',55,'Describe the recorded 20-second radio blackout, buffering and ordered replay. CRC detects modeled corruption; HMAC authenticates packets. Sequence/TTL reject replay and stale control. The modeled bit-flip test is not an arbitrary hardware error guarantee.')
for i,label in enumerate(['Event journal','Link unavailable','Buffer onboard','Replay + ACK']):
    box(s,label,.8+i*3.1,1.9,2.4,1)
    if i<3:arrow(s,3.25+i*3.1,2.4,3.85+i*3.1,2.4)
bullets(s,['Versioned JSON: at most 999 wire bytes.','CRC32 + HMAC-SHA256; sequence and expiry checks.','4,096-event ring, persistent journal and receiver cursor.','State corruption triggers a reflex hold.'],.85,3.6,11.5,23)

s=slide('Measured mission results',45,'Read the values from the accepted flight. Distinguish software command dispatch from simulator RPC completion. Model metrics come from 100 unseen views in the same scene, not an unseen-world or real-image benchmark. Source: validation/submission-summary.json.')
duration=audit['geometry']['duration_sim_s'];energy=audit['last_sample']['energy'];maximum=max(d['horizontal_error_m'] for d in audit['deliveries'])*100
table(s,[['Acceptance measure','Recorded result'],['Virtual deliveries + return',f"{audit['unique_geometrically_valid_deliveries']}/3  •  {duration:.1f} s"],['Hazard entries / static collision segments',f"{sum(audit['geometry']['zone_entries'].values())} / {audit['geometry']['static_collision_segments']}"],['Largest delivery position error',f'{maximum:.1f} cm'],['Energy remaining',f'{energy:.2f} Wh from 20 Wh'],['Command dispatch / RPC completion p95',f"{timing.get('command_dispatch_p95_ms',0):.1f} / {timing['pipeline_p95_ms']:.1f} ms"]],size=21)

s=slide('Applications and operating model',25,'These are proposed applications and commercial directions, not market or deployment claims. Initial users include civil protection and environmental teams. Budget the complete system: airframe, propulsion, flight controller, sensors, compute, battery, integration and testing. Do not present an unquoted full-system price or invented ROI.')
bullets(s,['Civil protection: reconnaissance and casualty support.','Environmental teams: coastal litter and hazard mapping.','Offer: mission software, integration, training and maintenance.','Budget: aircraft + sensors + compute + power + validation.'],.85,1.8,11.5,25)

s=slide('SKYFORGE',15,'Close on the actual mission: observe, prioritize, deliver and return. Invite questions on planning, physics, detection, resilience and deployment. Main talk including the video is exactly ten minutes; the following slides are backup.')
picture(s,ROOT/'station/dist/assets/site-aerial.jpg',6.65,1.45,6,5.2)
text(s,'Observe. Prioritize.\nDeliver. Return.',.85,2.2,5.8,2,36,bold=True)
text(s,'Autonomous humanitarian mission support',.85,4.8,5.5,1,22,ORANGE)
text(s,'github.com/drakedeveloper/dronathon',.85,6.2,8,.5,18,MUTED)

s=slide('Backup / vision evaluation',0,'Sources: validation/native-v2-primary-map.json, validation/native-v2-secondary-map.json and the frozen v2 point evaluations. Do not combine AP50 with fixed-threshold recall; they describe different measurements.',True)
primary=json.loads((ROOT/'validation/native-v2-primary-map.json').read_text())['classes'];secondary=json.loads((ROOT/'validation/native-v2-secondary-map.json').read_text())['classes']
rows=[['Native simulation class','AP50','Test domain']]
for name,values in {**primary,**secondary}.items():rows.append([name.replace('_',' ').title(),f"{100*values['ap50']:.1f}%",'100 unseen scene views'])
table(s,rows,size=21)

s=slide('Backup / separate real-image work',0,'Team-supplied charts: 39bd966f-17a3-414f-b5ba-f3bfadab54c7.jpg; cf9d2047-4e13-4252-b0ba-7317d16a1f3d.jpg; e846daec-091d-457b-a8de-7a98c4f588f7.jpg. These are reported dataset results from separate notebooks and were not used in the flight runtime. Their inference speed is not end-to-end mission timing.',True)
table(s,[['Team dataset model','Precision','Recall','mAP50'],['Gun detection','88.0%','73.0%','81.0%'],['Waste segmentation','84.3%','81.0%','83.8%']],h=2.6,size=23)
text(s,'Separate model track — not used by the simulator',.85,4.8,11.7,.7,25,ORANGE)
text(s,'Notebook checkpoints and reported image timings remain separate from mission acceptance.',.85,5.7,11.7,.8,20,MUTED)

s=slide('Backup / dashboard controls',0,'Optional 32-second demonstration outside the ten-minute main sequence. The clip records actual camera frames and station telemetry. Objective and blackout requests use the same authenticated HTTP endpoints as the dashboard buttons; the clip is not a browser screen recording. Explain: Map objective, choose a safe point, watch the checked route and motion; blackout buffers events while autonomy continues.',True)
controls=OUT/'SKYFORGE-controls-32s.mp4'
if controls.exists():s.shapes.add_movie(str(controls),Inches(.8),Inches(1.5),Inches(11.75),Inches(4.95),poster_frame_image=str(poster),mime_type='video/mp4')
text(s,'Map objective  /  checked rerouting  /  radio blackout and autonomous continuation',.85,6.55,11.5,.35,15,MUTED)

assert sum(x['seconds'] for x in schedule if not x['backup'])==600
destination=OUT/'SKYFORGE-FINAL-10min.pptx';prs.save(destination)
(OUT/'pitch-timing.json').write_text(json.dumps(schedule,indent=2)+'\n')
print(destination)
