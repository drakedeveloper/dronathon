from concurrent.futures import ThreadPoolExecutor
import numpy as np
from skyforge.neural_vision import NeuralVisionSystem


class Session:
    def get_inputs(self):return [type('Input',(),{'name':'images'})()]
    def run(self,*_):
        # A detection occupies the centre of the zoomed-out secondary input.
        return [np.array([[[256.],[256.],[50.],[100.],[.9],[.1]]],dtype=np.float32)]


def test_low_altitude_zoom_out_remaps_boxes_to_the_original_camera_image():
    model=object.__new__(NeuralVisionSystem);model.size=512
    model.sizes={'primary':512,'secondary':512};model.models=[('secondary',['injured_person','hostile_unit'],Session())]
    model.pool=ThreadPoolExecutor(max_workers=1);model.confidence=.35
    try:
        result=model.infer(np.zeros((384,512,3),np.uint8),{'frame_id':1,'t_sim_ns':0},secondary_zoom_out=True)
        box=result['detections'][0]['bbox_xyxy']
        np.testing.assert_allclose(box,[206,92,306,292])
    finally:model.pool.shutdown()


def test_half_precision_export_receives_half_tensor_without_changing_box_mapping():
    class HalfSession(Session):
        def get_inputs(self):return [type('Input',(),{'name':'images','type':'tensor(float16)'})()]
        def run(self,outputs,feed):
            assert feed['images'].dtype==np.float16
            assert feed['images'].shape==(1,3,512,512)
            return super().run()
    model=object.__new__(NeuralVisionSystem);model.size=512
    model.sizes={'primary':512,'secondary':512};model.models=[('secondary',['injured_person','hostile_unit'],HalfSession())]
    model.pool=ThreadPoolExecutor(max_workers=1);model.confidence=.35
    try:
        result=model.infer(np.zeros((384,512,3),np.uint8),{'frame_id':1,'t_sim_ns':0},secondary_zoom_out=True)
        np.testing.assert_allclose(result['detections'][0]['bbox_xyxy'],[206,92,306,292])
    finally:model.pool.shutdown()
