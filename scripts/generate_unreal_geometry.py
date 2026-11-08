"""Original island/architecture/proxy geometry in metres, no game assets."""
from pathlib import Path
import math
import numpy as np

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'runtime/unreal/source_assets';OUT.mkdir(parents=True,exist_ok=True)


class Mesh:
    def __init__(self):self.vertices=[];self.uv=[];self.normals=[];self.faces=[]
    def vertex(self,p,uv=(0,0),normal=(0,0,1)):
        self.vertices.append(p);self.uv.append(uv);self.normals.append(normal);return len(self.vertices)
    def face(self,a,b,c,material='surface'):self.faces.append((a,b,c,material))
    def ellipsoid(self,center,radii,material='garment',rings=12,sectors=20):
        grid=[];center=np.asarray(center);radii=np.asarray(radii)
        for i in range(rings+1):
            phi=math.pi*i/rings;row=[]
            for j in range(sectors+1):
                theta=2*math.pi*j/sectors
                unit=np.array([math.sin(phi)*math.cos(theta),math.sin(phi)*math.sin(theta),math.cos(phi)])
                n=unit/radii;n/=np.linalg.norm(n)
                row.append(self.vertex(center+radii*unit,(j/sectors,i/rings),n))
            grid.append(row)
        for i in range(rings):
            for j in range(sectors):
                self.face(grid[i][j],grid[i+1][j],grid[i][j+1],material)
                self.face(grid[i][j+1],grid[i+1][j],grid[i+1][j+1],material)
    def cylinder(self,a,b,radius,material='garment',sectors=16):
        a=np.asarray(a,float);b=np.asarray(b,float);axis=b-a;axis/=np.linalg.norm(axis)
        cross=np.cross(axis,[0,0,1])
        if np.linalg.norm(cross)<.1:cross=np.cross(axis,[0,1,0])
        cross/=np.linalg.norm(cross);up=np.cross(axis,cross);rows=[]
        for k,p in enumerate((a,b)):
            row=[]
            for j in range(sectors+1):
                theta=2*math.pi*j/sectors;n=math.cos(theta)*cross+math.sin(theta)*up
                row.append(self.vertex(p+radius*n,(j/sectors,k),n))
            rows.append(row)
        for j in range(sectors):
            self.face(rows[0][j],rows[1][j],rows[0][j+1],material)
            self.face(rows[0][j+1],rows[1][j],rows[1][j+1],material)
        for k,p in enumerate((a,b)):
            center=self.vertex(p,(.5,.5),axis*(1 if k else -1))
            for j in range(sectors):
                first,second=rows[k][j],rows[k][j+1]
                self.face(center,first if k else second,second if k else first,material)
    def write(self,name):
        colors={'surface':(.6,.55,.42),'garment':(.9,.25,.025),'skin':(.55,.35,.22),
                'boots':(.055,.065,.07),'metal':(.10,.11,.12),'roof':(.20,.23,.25),
                'trunk':(.24,.16,.09),'leaves':(.08,.22,.035)}
        materials=[]
        for material in dict.fromkeys(f[3] for f in self.faces):
            materials += ['newmtl '+material,'Kd '+' '.join(map(str,colors.get(material,(.4,.4,.4)))),'Ks 0.05 0.05 0.05','Ns 15']
        (OUT/(name+'.mtl')).write_text('\n'.join(materials)+'\n')
        lines=['mtllib '+name+'.mtl','o '+name]
        lines += ['v '+' '.join(f'{float(x):.7g}' for x in p) for p in self.vertices]
        lines += ['vt '+' '.join(f'{float(x):.7g}' for x in p) for p in self.uv]
        lines += ['vn '+' '.join(f'{float(x):.7g}' for x in p) for p in self.normals]
        active=None
        for a,b,c,material in self.faces:
            if material!=active:lines.append('usemtl '+material);active=material
            lines.append('f '+' '.join(f'{i}/{i}/{i}' for i in (a,b,c)))
        path=OUT/(name+'.obj');path.write_text('\n'.join(lines)+'\n')
        print(name,len(self.vertices),'vertices',len(self.faces),'triangles',flush=True)
        return path


def island():
    mesh=Mesh();xs=np.arange(-62,63,2.);ys=np.arange(-56,57,2.);x,y=np.meshgrid(xs,ys)
    theta=np.arctan2(y,x);r=np.sqrt((x/52)**2+(y/44)**2)/(1+.065*np.sin(3*theta)+.03*np.sin(7*theta))
    slope=np.clip((r-.72)/.28,0,1);z=-6*slope**1.65
    z+=np.where((r>.65)&(r<.96),.15*np.sin(x*.55)*np.cos(y*.4),0)
    z=np.where(r>1,-8,z);z=np.where((abs(x)<18)&(abs(y)<15),0,z)
    dy,dx=np.gradient(z,2.,2.);normal=np.stack([-dx,-dy,np.ones_like(z)],axis=-1)
    normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    grid=[]
    for i in range(len(ys)):
        grid.append([mesh.vertex([x[i,j],y[i,j],z[i,j]],[x[i,j]/4,y[i,j]/4],normal[i,j]) for j in range(len(xs))])
    for i in range(len(ys)-1):
        for j in range(len(xs)-1):
            a,b,c,d=grid[i][j],grid[i][j+1],grid[i+1][j],grid[i+1][j+1]
            mesh.face(a,b,c);mesh.face(b,d,c)
    mesh.write('island_terrain')


def cinematic_island():
    mesh=Mesh();xs=np.arange(-125,126,1.);ys=np.arange(-110,111,1.);x,y=np.meshgrid(xs,ys)
    theta=np.arctan2(y,x)
    r=np.sqrt((x/108)**2+(y/86)**2)/(1+.09*np.sin(3*theta)+.045*np.cos(7*theta))
    distance=np.maximum(np.maximum(abs(x)-19,abs(y)-16),0)
    blend=np.clip(distance/20,0,1);blend=blend*blend*(3-2*blend)
    hills=4+16*np.exp(-((x+37)**2+(y-36)**2)/650)+24*np.exp(-((x-30)**2+(y-45)**2)/900)
    hills+=2*np.sin(x*.085)*np.cos(y*.095)+.6*np.sin(x*.31+y*.13)
    z=hills*blend
    cliff=np.clip((r-.77)/.22,0,1);cliff=cliff*cliff*(3-2*cliff)
    z=z*(1-cliff)-12*cliff
    z=np.where(r>1,-13,z)
    dy,dx=np.gradient(z);normal=np.stack([-dx,-dy,np.ones_like(z)],axis=-1)
    normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    grid=[]
    for i in range(len(ys)):
        grid.append([mesh.vertex([x[i,j],y[i,j],z[i,j]],[x[i,j]/3,y[i,j]/3],normal[i,j]) for j in range(len(xs))])
    for i in range(len(ys)-1):
        for j in range(len(xs)-1):
            a,b,c,d=grid[i][j],grid[i][j+1],grid[i+1][j],grid[i+1][j+1]
            material='terrain_rock' if normal[i,j,2]<.82 or r[i,j]>.79 else 'terrain_grass' if distance[i,j]>7 else 'surface'
            mesh.face(a,b,c,material);mesh.face(b,d,c,material)
    mesh.write('cinematic_island_v2')


def person():
    mesh=Mesh();mesh.ellipsoid([0,0,.18],[.34,.18,.14])
    mesh.ellipsoid([.43,0,.18],[.145,.12,.13],'skin')
    mesh.ellipsoid([.38,0,.265],[.14,.13,.055],'garment')
    mesh.ellipsoid([-.34,0,.15],[.16,.18,.11])
    for sign in (-1,1):
        mesh.cylinder([-.35,sign*.11,.13],[-.69,sign*.14,.11],.075)
        mesh.cylinder([-.69,sign*.14,.11],[-.98,sign*.12,.10],.06)
        mesh.ellipsoid([-1.02,sign*.12,.11],[.105,.075,.08],'boots')
        mesh.cylinder([.15,sign*.18,.15],[-.03,sign*.31,.11],.065)
        mesh.cylinder([-.03,sign*.31,.11],[.23,sign*.38,.10],.05)
        mesh.ellipsoid([.26,sign*.39,.105],[.07,.045,.035],'skin')
    mesh.write('rescue_person_proxy')


def hangar_roof():
    mesh=Mesh();nx=8;nt=28;grid=[]
    for i in range(nx+1):
        x=-7+14*i/nx;row=[]
        for j in range(nt+1):
            t=math.pi*j/nt
            row.append(mesh.vertex([x,4*math.cos(t),2.8*math.sin(t)],(x/3,t*2),[0,math.cos(t),math.sin(t)]))
        grid.append(row)
    for i in range(nx):
        for j in range(nt):
            mesh.face(grid[i][j],grid[i+1][j],grid[i][j+1],'roof')
            mesh.face(grid[i][j+1],grid[i+1][j],grid[i+1][j+1],'roof')
    mesh.write('hangar_roof')


def palm():
    mesh=Mesh()
    for i in range(10):
        a=[.008*i*i,0,i*.5];b=[.008*(i+1)**2,0,(i+1)*.5]
        mesh.cylinder(a,b,.16-.007*i,'trunk',12)
    crown=np.array([.8,0,5.])
    for leaf in range(10):
        angle=2*math.pi*leaf/10;direction=np.array([math.cos(angle),math.sin(angle),0]);side=np.array([-direction[1],direction[0],0])
        def stem(t):return crown+2.25*t*direction+np.array([0,0,.65*math.sin(math.pi*t)-.65*t*t])
        for i in range(1,12):
            t=i/12;center=stem(t);tip=stem(t+.07)
            length=.58*math.sin(math.pi*t)
            for sign in (-1,1):
                edge=center+sign*side*length-.2*direction*length+[0,0,-.13]
                a=mesh.vertex(center,(0,t));b=mesh.vertex(edge,(.5,t));c=mesh.vertex(tip,(1,t))
                mesh.face(a,b,c,'leaves');mesh.face(c,b,a,'leaves')
    mesh.write('coastal_palm')


if __name__=='__main__':island();cinematic_island();person();hangar_roof();palm()
