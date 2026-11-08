"""Simulator-independent coordinate transforms."""
import numpy as np


def rotation_xyzw(q):
    q=np.asarray(q,float)
    if q.shape!=(4,) or not np.all(np.isfinite(q)) or np.linalg.norm(q)<1e-9:
        raise ValueError("Invalid quaternion")
    x,y,z,w=q/np.linalg.norm(q)
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                     [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                     [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
