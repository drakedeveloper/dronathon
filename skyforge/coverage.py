"""Depth-checked observed-ground map for the declared flat coastal scenario.

Reports geometric observation, not detection recall or a certified safe area.
Occluded ground remains unknown. Calibration/flat-ground assumptions are explicit.
"""
import numpy as np
from .geometry import rotation_xyzw


class CoverageGrid:
    def __init__(self,bounds=(-15.,-12.,15.,12.),cell_m=.5,max_ground_m_per_pixel=.04):
        self.bounds=bounds;self.cell_m=cell_m;self.max_gsd=max_ground_m_per_pixel
        xmin,ymin,xmax,ymax=bounds
        x,y=np.meshgrid(np.arange(xmin+cell_m/2,xmax,cell_m),np.arange(ymin+cell_m/2,ymax,cell_m))
        self.centers=np.c_[x.ravel(),y.ravel(),np.zeros(x.size)]
        self.hits=np.zeros(x.size,dtype=np.uint32);self.last_frame=None

    def update(self,frame):
        if frame is None or frame.get('pose') is None or frame.get('depth') is None:return
        if frame['frame_id']==self.last_frame:return
        pose=frame['pose'];depth=np.asarray(frame['depth']);h,w=depth.shape
        if w<2 or h<2:return
        rotation=rotation_xyzw(pose['q'])
        pitch=np.array([[0,0,1],[0,1,0],[-1,0,0]],float)
        optical=np.array([[0,0,1],[-1,0,0],[0,-1,0]],float)
        world_optical=rotation@pitch@optical
        origin=np.asarray(pose['p'])+rotation@np.array([0,0,-.12])
        if origin[2]<.5:return
        points=(self.centers-origin)@world_optical
        z=points[:,2];positive=z>.1;fx=w/(2*np.tan(.6))
        safe_z=np.where(positive,z,1.)
        u=fx*points[:,0]/safe_z+(w-1)/2;v=fx*points[:,1]/safe_z+(h-1)/2
        cosine=abs(world_optical[2,2])
        gsd=z/fx/max(.05,cosine*cosine)
        selected=positive&(u>=2)&(u<w-2)&(v>=2)&(v<h-2)&(gsd<=self.max_gsd)
        indices=np.flatnonzero(selected)
        if len(indices):
            measured=depth[np.rint(v[indices]).astype(int),np.rint(u[indices]).astype(int)]
            consistent=np.isfinite(measured)&(measured>0)&(abs(measured-z[indices])<.30)
            self.hits[indices[consistent]]+=1
        self.last_frame=frame['frame_id']

    def summary(self):
        observed=int(np.count_nonzero(self.hits));total=len(self.hits)
        return {'observed_cells':observed,'total_cells':total,'observed_fraction':observed/max(1,total),
                'observed_ground_m2':observed*self.cell_m**2,'cell_m':self.cell_m,
                'maximum_ground_m_per_pixel':self.max_gsd,
                'scope':'Flat-ground camera projection with depth occlusion/resolution checks; not semantic completeness or safe-space certification.'}

    def cells(self):
        return [[round(float(self.centers[i,0]),2),round(float(self.centers[i,1]),2),min(10,int(self.hits[i]))]
                for i in np.flatnonzero(self.hits)]
