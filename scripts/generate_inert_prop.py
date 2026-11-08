"""Original, nonfunctional game-prop mesh. Exterior visual geometry only."""
import numpy as np
from scripts.generate_unreal_geometry import Mesh


def generate():
    mesh=Mesh()
    def prism(points,width,material):
        sides=[]
        for y in (-width/2,width/2):
            sides.append([mesh.vertex([x,y,z]) for x,z in points])
        for i in range(1,len(points)-1):
            mesh.face(sides[0][0],sides[0][i+1],sides[0][i],material)
            mesh.face(sides[1][0],sides[1][i],sides[1][i+1],material)
        for i in range(len(points)):
            j=(i+1)%len(points);mesh.face(sides[0][i],sides[0][j],sides[1][j],material);mesh.face(sides[0][i],sides[1][j],sides[1][i],material)
    def box(a,b,material):prism([(a[0],a[2]),(b[0],a[2]),(b[0],b[2]),(a[0],b[2])],b[1]-a[1],material)
    prism([(-.15,-.015),(.14,-.015),(.17,.025),(.13,.085),(-.12,.085),(-.17,.045)],.065,'metal')
    prism([(-.15,.065),(-.36,.045),(-.40,.08),(-.40,-.07),(-.34,-.07),(-.28,.015),(-.14,.025)],.055,'polymer')
    prism([(-.07,-.01),(-.015,-.02),(-.055,-.15),(-.115,-.145)],.046,'polymer')
    prism([(.025,-.01),(.09,-.01),(.075,-.105),(.035,-.17),(-.015,-.15),(.015,-.08)],.045,'metal')
    box([.14,-.025,.012],[.285,.025,.07],'polymer')
    mesh.cylinder([.25,0,.04],[.425,0,.04],.009,'metal',16)
    mesh.cylinder([.40,0,.04],[.438,0,.04],.015,'metal',16)
    for x in np.arange(-.13,.285,.016):box([x,-.028,.08],[x+.008,.028,.09],'metal')
    # Decorative vent grooves, sight and trigger-guard silhouette.
    for x in np.arange(.16,.28,.025):mesh.cylinder([x,-.027,.025],[x,-.027,.06],.003,'rubber',8)
    for a,b in [([-.015,0,-.025],[.025,0,-.025]),([.025,0,-.025],[.015,0,-.065]),([.015,0,-.065],[-.04,0,-.065])]:mesh.cylinder(a,b,.004,'metal',8)
    mesh.cylinder([-.07,0,.12],[.065,0,.12],.019,'metal',20)
    mesh.cylinder([-.075,0,.12],[-.055,0,.12],.024,'rubber',20)
    mesh.cylinder([.05,0,.12],[.075,0,.12],.024,'rubber',20)
    # Lay the prop on its side so its exterior silhouette is visible from above.
    mesh.vertices=[[x,z,y+.036] for x,y,z in mesh.vertices]
    mesh.normals=[[x,z,y] for x,y,z in mesh.normals]
    return mesh.write('inert_field_prop_v1')


if __name__=='__main__':generate()
