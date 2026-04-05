from fastapi import APIRouter


router = APIRouter(tags=["render"])


@router.get("/render/scenes")
def render_scenes() -> dict:
    return {
        "items": [
            {"label": "scene_test_merl_accelerated.xml", "path": "scene/dj_xml/scene_test_merl_accelerated.xml"},
            {"label": "scene_test_nbrdf_npy.xml", "path": "scene/dj_xml/scene_test_nbrdf_npy.xml"},
            {"label": "scene_universal.xml", "path": "scene/dj_xml/scene_universal.xml"},
        ]
    }
