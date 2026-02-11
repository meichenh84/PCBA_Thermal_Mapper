# -*- coding: utf-8 -*-
"""
PCBA Thermal Mapper — 全專案自動化測試
========================================
涵蓋 10 個模組的 Unit Test + 5 組複合 Integration Test。
執行方式：
    cd "C:\\Users\\judi-\\VS Projects\\PCBA_Thermal_Mapper\\material\\Thermal\\Thermal"
    python -m pytest src/test_all.py -v
"""

import sys
import os
import json
import math
import tempfile
import shutil

import pytest
import numpy as np

# ---------------------------------------------------------------------------
# Import 路徑設定：讓 src/ 與 src/bean/ 能直接被 import
# ---------------------------------------------------------------------------
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SRC_DIR)
sys.path.insert(0, os.path.join(_SRC_DIR, "bean"))

# ---------------------------------------------------------------------------
# 模組 imports（按測試順序）
# ---------------------------------------------------------------------------
from constants import Constants
from config import GlobalConfig
from canvas_rect_item import CanvasRectItem
from rotation_utils import (
    get_rotated_corners, rotate_point, get_rotated_anchor_positions,
    corners_to_flat, point_in_polygon, create_polygon_mask,
)
from coordinate_converter import CoordinateConverter, quick_convert
from point_transformer import PointTransformer
from temperature_config_manager import TemperatureConfigManager
from load_tempA import TempLoader
from color_range import color_ranges, get_mask_boundary

# draw_rect 會 import tkinter，headless 可能失敗，做條件匯入
_tk_available = True
try:
    import tkinter as tk  # noqa: F401
except ImportError:
    _tk_available = False

if _tk_available:
    from draw_rect import calc_name_position_for_rotated, calc_temp_text_offset


# ═══════════════════════════════════════════════════════════════════════════
#  1. TestConstants
# ═══════════════════════════════════════════════════════════════════════════
class TestConstants:
    """constants.py 路徑常數正確性"""

    def test_imageA_default_path(self):
        assert Constants.imageA_default_path == "imageA.jpg"

    def test_imageB_default_path(self):
        assert Constants.imageB_default_path == "imageB.jpg"

    def test_imageA_point_path_format(self):
        path = Constants.imageA_point_path()
        assert path == "points/imageA.jpg_points.csv"

    def test_imageB_point_path_format(self):
        path = Constants.imageB_point_path()
        assert path == "points/imageB.jpg_points.csv"

    def test_point_paths_differ(self):
        assert Constants.imageA_point_path() != Constants.imageB_point_path()


# ═══════════════════════════════════════════════════════════════════════════
#  2. TestGlobalConfig
# ═══════════════════════════════════════════════════════════════════════════
class TestGlobalConfig:
    """config.py GlobalConfig 單例、get/set/remove/clear、JSON roundtrip"""

    @pytest.fixture(autouse=True)
    def reset_singleton(self, tmp_path, monkeypatch):
        """每個 test 前重置 Singleton 並切換工作目錄到 tmp_path"""
        GlobalConfig._instance = None
        if hasattr(GlobalConfig, '_initialized'):
            del GlobalConfig._initialized
        # 讓 GlobalConfig 在 tmp_path 裡建 config/
        monkeypatch.chdir(tmp_path)

    def test_singleton_same_instance(self):
        a = GlobalConfig()
        b = GlobalConfig()
        assert a is b

    def test_set_and_get(self):
        cfg = GlobalConfig()
        cfg.set("key1", "value1")
        assert cfg.get("key1") == "value1"

    def test_get_default(self):
        cfg = GlobalConfig()
        assert cfg.get("nonexistent", 42) == 42

    def test_get_none_default(self):
        cfg = GlobalConfig()
        assert cfg.get("nonexistent") is None

    def test_remove(self):
        cfg = GlobalConfig()
        cfg.set("rm_key", 123)
        cfg.remove("rm_key")
        assert cfg.get("rm_key") is None

    def test_remove_nonexistent(self):
        cfg = GlobalConfig()
        cfg.remove("no_such_key")  # 不應 raise

    def test_clear(self):
        cfg = GlobalConfig()
        cfg.set("a", 1)
        cfg.set("b", 2)
        cfg.clear()
        assert cfg.get("a") is None
        assert cfg.get("b") is None

    def test_update(self):
        cfg = GlobalConfig()
        cfg.update({"x": 10, "y": 20})
        assert cfg.get("x") == 10
        assert cfg.get("y") == 20

    def test_save_and_load_roundtrip(self, tmp_path):
        cfg = GlobalConfig()
        cfg.set("theme", "dark")
        cfg.set("count", 99)
        json_file = str(tmp_path / "config" / "config.json")
        cfg.save_to_json(json_file)

        # 重置 singleton 再載入
        GlobalConfig._instance = None
        if hasattr(GlobalConfig, '_initialized'):
            del GlobalConfig._initialized
        cfg2 = GlobalConfig()
        cfg2.load_from_json(json_file)
        assert cfg2.get("theme") == "dark"
        assert cfg2.get("count") == 99

    def test_save_creates_directory(self, tmp_path):
        cfg = GlobalConfig()
        cfg.set("hello", "world")
        deep = str(tmp_path / "a" / "b" / "c.json")
        cfg.save_to_json(deep)
        assert os.path.exists(deep)

    def test_load_missing_file_uses_default(self):
        cfg = GlobalConfig()
        cfg.load_from_json("nonexistent_path/no.json")
        # 應該使用預設配置
        assert cfg.get("magnifier_switch") is True

    def test_default_config_keys(self):
        cfg = GlobalConfig()
        cfg._config = cfg._get_default_config()
        assert "heat_rect_color" in cfg._config
        assert "layout_temp_font_size" in cfg._config

    def test_unicode_roundtrip(self, tmp_path):
        cfg = GlobalConfig()
        cfg.set("名稱", "測試中文值")
        json_file = str(tmp_path / "config" / "unicode.json")
        cfg.save_to_json(json_file)

        GlobalConfig._instance = None
        if hasattr(GlobalConfig, '_initialized'):
            del GlobalConfig._initialized
        cfg2 = GlobalConfig()
        cfg2.load_from_json(json_file)
        assert cfg2.get("名稱") == "測試中文值"

    def test_overwrite_existing_key(self):
        cfg = GlobalConfig()
        cfg.set("k", 1)
        cfg.set("k", 2)
        assert cfg.get("k") == 2


# ═══════════════════════════════════════════════════════════════════════════
#  3. TestCanvasRectItem
# ═══════════════════════════════════════════════════════════════════════════
class TestCanvasRectItem:
    """bean/canvas_rect_item.py 資料模型"""

    def _make(self, **kw):
        defaults = dict(x1=10, y1=20, x2=110, y2=120, cx=60, cy=70,
                        max_temp=85.5, name="U1", rectId=1, nameId=2)
        defaults.update(kw)
        return CanvasRectItem(**defaults)

    def test_init_attributes(self):
        r = self._make()
        assert r.x1 == 10 and r.y2 == 120

    def test_to_dict_keys(self):
        d = self._make().to_dict()
        expected_keys = {"x1", "y1", "x2", "y2", "cx", "cy", "max_temp", "name", "rectId", "nameId"}
        assert set(d.keys()) == expected_keys

    def test_to_dict_values(self):
        r = self._make(max_temp=99.9)
        assert r.to_dict()["max_temp"] == 99.9

    def test_get_value_existing(self):
        r = self._make(name="C3")
        assert r.get_value("name") == "C3"

    def test_get_value_missing(self):
        r = self._make()
        assert r.get_value("nonexistent") is None

    def test_set_nameId(self):
        r = self._make()
        r.set_nameId(555)
        assert r.nameId == 555

    def test_set_rectId(self):
        r = self._make()
        r.set_rectId(777)
        assert r.rectId == 777

    def test_set_rect_boundary(self):
        r = self._make()
        r.set_rect_boundary(0, 0, 200, 200)
        assert (r.x1, r.y1, r.x2, r.y2) == (0, 0, 200, 200)

    def test_repr_contains_name(self):
        r = self._make(name="R1")
        assert "R1" in repr(r)

    def test_default_ids_zero(self):
        r = CanvasRectItem(0, 0, 1, 1, 0, 0, 0.0, "X")
        assert r.rectId == 0 and r.nameId == 0

    def test_to_dict_json_serializable(self):
        d = self._make().to_dict()
        s = json.dumps(d)
        assert isinstance(json.loads(s), dict)


# ═══════════════════════════════════════════════════════════════════════════
#  4. TestRotationUtils
# ═══════════════════════════════════════════════════════════════════════════
class TestRotationUtils:
    """rotation_utils.py 旋轉數學"""

    def test_corners_0_deg(self):
        corners = get_rotated_corners(100, 100, 50, 30, 0)
        assert len(corners) == 4
        # TL = (50, 70), TR = (150, 70), BR = (150, 130), BL = (50, 130)
        assert corners[0] == pytest.approx((50, 70), abs=0.01)
        assert corners[2] == pytest.approx((150, 130), abs=0.01)

    def test_corners_90_deg(self):
        """逆時針 90°：原本 TL(-50,-30) -> 旋轉後 (-30, 50)"""
        corners = get_rotated_corners(0, 0, 50, 30, 90)
        # TL offset(-50,-30): rx = cos(-90)*(-50)-sin(-90)*(-30) = 0 - 30 = -30
        #                      ry = sin(-90)*(-50)+cos(-90)*(-30) = 50 + 0 = 50
        assert corners[0] == pytest.approx((-30, 50), abs=0.01)

    def test_corners_180_deg(self):
        corners = get_rotated_corners(0, 0, 50, 30, 180)
        # TL(-50,-30) 旋轉 180° => (50, 30)
        assert corners[0] == pytest.approx((50, 30), abs=0.01)

    def test_corners_360_deg_same_as_0(self):
        c0 = get_rotated_corners(100, 200, 50, 40, 0)
        c360 = get_rotated_corners(100, 200, 50, 40, 360)
        for a, b in zip(c0, c360):
            assert a == pytest.approx(b, abs=0.01)

    def test_rotate_point_origin(self):
        # 螢幕座標系 Y 朝下，rad = -radians(90) = -π/2
        # (1,0) 繞 (0,0): rx=cos(-π/2)*1-sin(-π/2)*0=0, ry=sin(-π/2)*1+cos(-π/2)*0=-1
        rx, ry = rotate_point(1, 0, 0, 0, 90)
        assert (rx, ry) == pytest.approx((0, -1), abs=0.01)

    def test_rotate_point_identity(self):
        rx, ry = rotate_point(5, 7, 3, 4, 0)
        assert (rx, ry) == pytest.approx((5, 7), abs=0.01)

    def test_rotate_point_roundtrip(self):
        px, py = 100, 200
        cx, cy = 50, 50
        rx, ry = rotate_point(px, py, cx, cy, 45)
        bx, by = rotate_point(rx, ry, cx, cy, -45)
        assert (bx, by) == pytest.approx((px, py), abs=0.01)

    def test_anchor_positions_count(self):
        anchors = get_rotated_anchor_positions(0, 0, 50, 30, 0)
        assert len(anchors) == 8

    def test_anchor_positions_0_deg_corners(self):
        anchors = get_rotated_anchor_positions(100, 100, 50, 30, 0)
        # TL = (50, 70)
        assert anchors[0] == pytest.approx((50, 70), abs=0.01)
        # BR = (150, 130)
        assert anchors[3] == pytest.approx((150, 130), abs=0.01)

    def test_anchor_midpoints_0_deg(self):
        anchors = get_rotated_anchor_positions(100, 100, 50, 30, 0)
        # T-mid = (100, 70)
        assert anchors[6] == pytest.approx((100, 70), abs=0.01)

    def test_corners_to_flat(self):
        corners = [(1, 2), (3, 4), (5, 6)]
        assert corners_to_flat(corners) == [1, 2, 3, 4, 5, 6]

    def test_corners_to_flat_empty(self):
        assert corners_to_flat([]) == []

    def test_point_in_polygon_inside(self):
        square = [(0, 0), (10, 0), (10, 10), (0, 10)]
        assert point_in_polygon(5, 5, square) is True

    def test_point_in_polygon_outside(self):
        square = [(0, 0), (10, 0), (10, 10), (0, 10)]
        assert point_in_polygon(15, 5, square) is False

    def test_point_in_polygon_triangle(self):
        tri = [(0, 0), (10, 0), (5, 10)]
        assert point_in_polygon(5, 3, tri) is True
        assert point_in_polygon(0, 10, tri) is False

    def test_create_polygon_mask_shape(self):
        corners = [(2, 2), (8, 2), (8, 8), (2, 8)]
        mask = create_polygon_mask(corners, (10, 10))
        assert mask.shape == (10, 10)
        assert mask.dtype == bool

    def test_create_polygon_mask_center_true(self):
        corners = [(2, 2), (8, 2), (8, 8), (2, 8)]
        mask = create_polygon_mask(corners, (10, 10))
        assert mask[5, 5] is np.True_

    def test_create_polygon_mask_outside_false(self):
        corners = [(2, 2), (8, 2), (8, 8), (2, 8)]
        mask = create_polygon_mask(corners, (10, 10))
        assert mask[0, 0] is np.False_

    def test_rotate_point_45_deg(self):
        # (1,0) 繞 (0,0) 逆時針 45°
        rx, ry = rotate_point(1, 0, 0, 0, 45)
        expected_x = math.cos(math.radians(-45))  # ≈ 0.7071
        expected_y = math.sin(math.radians(-45))  # ≈ -0.7071 * 1 ...
        # Actually: rx = cos(-45)*1 - sin(-45)*0 = cos45 ≈ 0.707
        #           ry = sin(-45)*1 + cos(-45)*0 = -sin45 ≈ -0.707 ... wait
        # But screen coords: rotate_point uses rad = -radians(angle_deg)
        # angle_deg=45 => rad = -pi/4
        # dx=1, dy=0
        # rx = cos(-pi/4)*1 - sin(-pi/4)*0 = cos(pi/4) ≈ 0.707
        # ry = sin(-pi/4)*1 + cos(-pi/4)*0 = -sin(pi/4) ≈ -0.707
        # But wait, screen Y is down, so (0.707, -0.707) means it went up-right.
        # Hmm actually with cx=cy=0 it's just: rx=0.707, ry=-0.707... wait no
        # rad = -math.radians(45) = -pi/4
        # cos_a = cos(-pi/4) = cos(pi/4) ≈ 0.7071
        # sin_a = sin(-pi/4) = -sin(pi/4) ≈ -0.7071
        # dx=1, dy=0
        # rx = 0.7071*1 - (-0.7071)*0 = 0.7071
        # ry = (-0.7071)*1 + 0.7071*0 = -0.7071
        # Hmm that doesn't seem right for "逆時針" in screen coords...
        # But that's what the code does.
        assert rx == pytest.approx(math.sqrt(2)/2, abs=0.01)

    def test_rotated_corners_symmetry(self):
        """旋轉後四頂點到中心距離相等"""
        cx, cy, hw, hh = 100, 100, 40, 20
        corners = get_rotated_corners(cx, cy, hw, hh, 37)
        dists = [math.hypot(x - cx, y - cy) for x, y in corners]
        expected = math.hypot(hw, hh)
        for d in dists:
            assert d == pytest.approx(expected, abs=0.01)


# ═══════════════════════════════════════════════════════════════════════════
#  5. TestCoordinateConverter
# ═══════════════════════════════════════════════════════════════════════════
class TestCoordinateConverter:
    """coordinate_converter.py 四原點互轉"""

    def _make(self, w=800, h=600):
        return CoordinateConverter(w, h)

    def test_same_origin_identity(self):
        c = self._make()
        assert c.convert_coordinate(100, 200, "左上角", "左上角") == (100, 200)

    def test_top_left_to_top_right(self):
        c = self._make(800, 600)
        x, y = c.convert_coordinate(100, 200, "左上角", "右上角")
        assert (x, y) == (700, 200)

    def test_top_left_to_bottom_right(self):
        c = self._make(800, 600)
        x, y = c.convert_coordinate(100, 200, "左上角", "右下角")
        assert (x, y) == (700, 400)

    def test_top_left_to_bottom_left(self):
        c = self._make(800, 600)
        x, y = c.convert_coordinate(100, 200, "左上角", "左下角")
        assert (x, y) == (100, 400)

    def test_roundtrip_all_pairs(self):
        c = self._make(1024, 768)
        origins = c.get_available_origins()
        x0, y0 = 300, 250
        for o1 in origins:
            for o2 in origins:
                x1, y1 = c.convert_coordinate(x0, y0, o1, o2)
                x2, y2 = c.convert_coordinate(x1, y1, o2, o1)
                assert (x2, y2) == pytest.approx((x0, y0), abs=1e-6)

    def test_batch_convert(self):
        c = self._make(800, 600)
        pts = [(0, 0), (400, 300), (800, 600)]
        result = c.batch_convert(pts, "左上角", "右下角")
        assert result[0] == (800, 600)
        assert result[1] == (400, 300)
        assert result[2] == (0, 0)

    def test_batch_convert_empty(self):
        c = self._make()
        assert c.batch_convert([], "左上角", "右下角") == []

    def test_invalid_from_origin(self):
        c = self._make()
        with pytest.raises(ValueError):
            c.convert_coordinate(0, 0, "INVALID", "左上角")

    def test_invalid_to_origin(self):
        c = self._make()
        with pytest.raises(ValueError):
            c.convert_coordinate(0, 0, "左上角", "INVALID")

    def test_get_available_origins(self):
        c = self._make()
        origins = c.get_available_origins()
        assert len(origins) == 4
        assert "左上角" in origins

    def test_quick_convert(self):
        x, y = quick_convert(100, 200, 800, 600, "左上角", "右下角")
        assert (x, y) == (700, 400)

    def test_center_point_bottom_right(self):
        """中心點轉到右下角原點 = 自身"""
        c = self._make(800, 600)
        x, y = c.convert_coordinate(400, 300, "左上角", "右下角")
        assert (x, y) == (400, 300)

    def test_corner_zero(self):
        c = self._make(800, 600)
        x, y = c.convert_coordinate(0, 0, "左上角", "右下角")
        assert (x, y) == (800, 600)


# ═══════════════════════════════════════════════════════════════════════════
#  6. TestPointTransformer
# ═══════════════════════════════════════════════════════════════════════════
class TestPointTransformer:
    """point_transformer.py 仿射/透視變換"""

    def _make_affine(self):
        """建立 3 點仿射變換（平移 +100, +50）"""
        pA = [[100, 100], [200, 100], [100, 200]]
        pB = [[200, 150], [300, 150], [200, 250]]
        return PointTransformer(pA, pB)

    def _make_homography(self):
        """建立 4 點透視變換"""
        pA = [[0, 0], [100, 0], [100, 100], [0, 100]]
        pB = [[10, 10], [110, 10], [110, 110], [10, 110]]
        return PointTransformer(pA, pB)

    def test_affine_A2B(self):
        t = self._make_affine()
        bx, by = t.A2B(100, 100)
        assert (bx, by) == pytest.approx((200, 150), abs=1.0)

    def test_affine_B2A(self):
        t = self._make_affine()
        ax, ay = t.B2A(200, 150)
        assert (ax, ay) == pytest.approx((100, 100), abs=1.0)

    def test_affine_roundtrip(self):
        t = self._make_affine()
        bx, by = t.A2B(150, 180)
        ax, ay = t.B2A(bx, by)
        assert (ax, ay) == pytest.approx((150, 180), abs=1.0)

    def test_homography_A2B(self):
        t = self._make_homography()
        bx, by = t.A2B(0, 0)
        assert (bx, by) == pytest.approx((10, 10), abs=1.0)

    def test_homography_roundtrip(self):
        t = self._make_homography()
        bx, by = t.A2B(50, 50)
        ax, ay = t.B2A(bx, by)
        assert (ax, ay) == pytest.approx((50, 50), abs=1.0)

    def test_is_homography_flag_3pts(self):
        t = self._make_affine()
        assert t.is_homography is False

    def test_is_homography_flag_4pts(self):
        t = self._make_homography()
        assert t.is_homography is True

    def test_too_few_points(self):
        with pytest.raises(ValueError):
            PointTransformer([[0, 0], [1, 1]], [[0, 0], [1, 1]])

    def test_mismatched_point_count(self):
        with pytest.raises(ValueError):
            PointTransformer([[0, 0], [1, 1], [2, 2]], [[0, 0], [1, 1]])

    def test_A_2_oriB_compat(self):
        t = self._make_affine()
        bx1, by1 = t.A2B(120, 130)
        bx2, by2 = t.A_2_oriB(120, 130)
        assert (bx1, by1) == pytest.approx((bx2, by2), abs=0.01)

    def test_get_B2A_matrix_affine(self):
        t = self._make_affine()
        m = t.get_B2A_matrix()
        assert m.shape == (2, 3)

    def test_get_B2A_matrix_homography(self):
        t = self._make_homography()
        m = t.get_B2A_matrix()
        assert m.shape == (3, 3)

    def test_smart_matching_order_independent(self):
        """Smart matching 使打點順序不同時仍能正確變換"""
        pA = [[0, 0], [100, 0], [100, 100]]
        pB = [[10, 10], [110, 10], [110, 110]]
        # 正常順序
        t1 = PointTransformer(pA, pB)
        # 打亂 B 的順序
        pB_shuffled = [[110, 110], [10, 10], [110, 10]]
        t2 = PointTransformer(pA, pB_shuffled)
        bx1, by1 = t1.A2B(50, 50)
        bx2, by2 = t2.A2B(50, 50)
        assert (bx1, by1) == pytest.approx((bx2, by2), abs=2.0)

    def test_multiple_points_roundtrip(self):
        t = self._make_homography()
        test_pts = [(0, 0), (50, 25), (100, 100), (25, 75)]
        for px, py in test_pts:
            bx, by = t.A2B(px, py)
            ax, ay = t.B2A(bx, by)
            assert (ax, ay) == pytest.approx((px, py), abs=1.0)


# ═══════════════════════════════════════════════════════════════════════════
#  7. TestTemperatureConfigManager
# ═══════════════════════════════════════════════════════════════════════════
class TestTemperatureConfigManager:
    """temperature_config_manager.py 設定持久化"""

    @pytest.fixture
    def tmp_folder(self, tmp_path):
        return str(tmp_path / "project")

    def test_init_no_folder(self):
        mgr = TemperatureConfigManager()
        assert mgr.get("min_temp") == 50.0

    def test_init_with_folder(self, tmp_folder):
        os.makedirs(tmp_folder, exist_ok=True)
        mgr = TemperatureConfigManager(tmp_folder)
        assert mgr.folder_path == tmp_folder

    def test_set_and_get(self, tmp_folder):
        os.makedirs(tmp_folder, exist_ok=True)
        mgr = TemperatureConfigManager(tmp_folder)
        mgr.set("min_temp", 60.0)
        assert mgr.get("min_temp") == 60.0

    def test_save_and_load_roundtrip(self, tmp_folder):
        os.makedirs(tmp_folder, exist_ok=True)
        mgr = TemperatureConfigManager(tmp_folder)
        mgr.set("p_w", 300.0)
        mgr.save_config()

        mgr2 = TemperatureConfigManager(tmp_folder)
        assert mgr2.get("p_w") == 300.0

    def test_default_config_values(self):
        mgr = TemperatureConfigManager()
        assert mgr.get("p_h") == 194.0
        assert mgr.get("p_origin") == "左下"

    def test_set_file_path(self, tmp_folder):
        os.makedirs(tmp_folder, exist_ok=True)
        mgr = TemperatureConfigManager(tmp_folder)
        mgr.set_file_path("current_heat_file", "/path/to/heat.jpg")
        assert mgr.get_file_path("current_heat_file") == "/path/to/heat.jpg"

    def test_set_invalid_file_type(self, tmp_folder):
        os.makedirs(tmp_folder, exist_ok=True)
        mgr = TemperatureConfigManager(tmp_folder)
        mgr.set_file_path("invalid_type", "/path")  # 不應 raise，只 print
        assert mgr.get_file_path("invalid_type") is None

    def test_clear_file_paths(self, tmp_folder):
        os.makedirs(tmp_folder, exist_ok=True)
        mgr = TemperatureConfigManager(tmp_folder)
        mgr.set_file_path("current_heat_file", "/heat.jpg")
        mgr.clear_file_paths()
        assert mgr.get_file_path("current_heat_file") is None

    def test_get_all_file_paths(self, tmp_folder):
        os.makedirs(tmp_folder, exist_ok=True)
        mgr = TemperatureConfigManager(tmp_folder)
        paths = mgr.get_all_file_paths()
        assert "current_heat_file" in paths
        assert "current_layout_data_file" in paths

    def test_get_relative_path(self, tmp_folder):
        os.makedirs(tmp_folder, exist_ok=True)
        mgr = TemperatureConfigManager(tmp_folder)
        abs_path = os.path.join(tmp_folder, "sub", "file.jpg")
        rel = mgr.get_relative_path(abs_path)
        assert rel == os.path.join("sub", "file.jpg")

    def test_get_relative_path_none(self):
        mgr = TemperatureConfigManager()
        assert mgr.get_relative_path(None) is None

    def test_save_parameters(self, tmp_folder):
        os.makedirs(tmp_folder, exist_ok=True)
        mgr = TemperatureConfigManager(tmp_folder)
        mgr.save_parameters({"min_temp": 70.0, "max_temp": 90.0})
        mgr2 = TemperatureConfigManager(tmp_folder)
        assert mgr2.get("min_temp") == 70.0

    def test_update_kwargs(self, tmp_folder):
        os.makedirs(tmp_folder, exist_ok=True)
        mgr = TemperatureConfigManager(tmp_folder)
        mgr.update(p_w=500.0, p_h=400.0)
        assert mgr.get("p_w") == 500.0

    def test_get_all_parameters(self):
        mgr = TemperatureConfigManager()
        params = mgr.get_all_parameters()
        assert isinstance(params, dict)
        assert "min_temp" in params

    def test_get_file_info_display_no_files(self):
        mgr = TemperatureConfigManager()
        assert mgr.get_file_info_display() == "未加载文件"


# ═══════════════════════════════════════════════════════════════════════════
#  8. TestDrawRectCalc（僅純計算函式，不需 GUI）
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.skipif(not _tk_available, reason="tkinter not available")
class TestDrawRectCalc:
    """draw_rect.py calc_name_position_for_rotated / calc_temp_text_offset"""

    @pytest.fixture(autouse=True)
    def reset_config(self, tmp_path, monkeypatch):
        GlobalConfig._instance = None
        if hasattr(GlobalConfig, '_initialized'):
            del GlobalConfig._initialized
        monkeypatch.chdir(tmp_path)

    def test_name_position_axis_aligned(self):
        corners = [(0, 0), (100, 0), (100, 50), (0, 50)]
        cx, ny = calc_name_position_for_rotated(corners, scale=1.0, gap=3)
        assert ny == pytest.approx(-3.0, abs=0.01)
        assert cx == pytest.approx(50.0, abs=0.5)

    def test_name_position_single_top(self):
        """只有一個最高頂點"""
        corners = [(50, 0), (100, 30), (80, 80), (20, 50)]
        cx, ny = calc_name_position_for_rotated(corners, scale=1.0)
        assert ny == pytest.approx(-3.0, abs=0.5)
        assert cx == pytest.approx(50.0, abs=0.5)

    def test_name_position_scale(self):
        corners = [(0, 0), (100, 0), (100, 50), (0, 50)]
        _, ny1 = calc_name_position_for_rotated(corners, scale=1.0, gap=3)
        _, ny2 = calc_name_position_for_rotated(corners, scale=2.0, gap=3)
        assert ny2 < ny1  # 放大時 gap 更大，Y 更小（更高）

    def test_temp_offset_T(self):
        dx, dy = calc_temp_text_offset("T", 5, 20, 10, gap=0)
        assert dx == 0
        assert dy < 0  # 正上方

    def test_temp_offset_B(self):
        dx, dy = calc_temp_text_offset("B", 5, 20, 10, gap=0)
        assert dx == 0
        assert dy > 0  # 正下方

    def test_temp_offset_L(self):
        dx, dy = calc_temp_text_offset("L", 5, 20, 10, gap=0)
        assert dx < 0  # 左邊
        assert dy == 0

    def test_temp_offset_R(self):
        dx, dy = calc_temp_text_offset("R", 5, 20, 10, gap=0)
        assert dx > 0  # 右邊
        assert dy == 0

    def test_temp_offset_TL(self):
        dx, dy = calc_temp_text_offset("TL", 5, 20, 10)
        assert dx < 0 and dy < 0

    def test_temp_offset_TR(self):
        dx, dy = calc_temp_text_offset("TR", 5, 20, 10)
        assert dx > 0 and dy < 0

    def test_temp_offset_BL(self):
        dx, dy = calc_temp_text_offset("BL", 5, 20, 10)
        assert dx < 0 and dy > 0

    def test_temp_offset_BR(self):
        dx, dy = calc_temp_text_offset("BR", 5, 20, 10)
        assert dx > 0 and dy > 0

    def test_temp_offset_default_fallback(self):
        dx, dy = calc_temp_text_offset("INVALID", 5, 20, 10)
        assert dx == 0 and dy < 0  # 預設正上方

    def test_all_8_directions_unique(self):
        dirs = ["TL", "T", "TR", "L", "R", "BL", "B", "BR"]
        results = set()
        for d in dirs:
            dx, dy = calc_temp_text_offset(d, 5, 20, 10)
            results.add((round(dx, 2), round(dy, 2)))
        assert len(results) == 8

    def test_name_position_rotated_45(self):
        """旋轉 45° 後最高點應在頂部"""
        corners = get_rotated_corners(50, 50, 30, 20, 45)
        cx, ny = calc_name_position_for_rotated(corners, scale=1.0)
        min_y = min(c[1] for c in corners)
        assert ny < min_y  # 名稱在最高點上方

    def test_temp_offset_symmetry_LR(self):
        dxL, dyL = calc_temp_text_offset("L", 5, 20, 10)
        dxR, dyR = calc_temp_text_offset("R", 5, 20, 10)
        assert dxL == pytest.approx(-dxR, abs=0.01)
        assert dyL == pytest.approx(dyR, abs=0.01)


# ═══════════════════════════════════════════════════════════════════════════
#  9. TestLoadTempA
# ═══════════════════════════════════════════════════════════════════════════
class TestLoadTempA:
    """load_tempA.py 溫度查詢（合成 CSV 數據）"""

    @pytest.fixture(autouse=True)
    def setup_temp_csv(self, tmp_path):
        """建立 10×10 合成溫度 CSV（最高溫 99.9 在 col=5, row=3）"""
        TempLoader._instance = None
        TempLoader._current_file_path = None

        data = np.full((10, 10), 25.0)
        data[3, 5] = 99.9  # row=3, col=5
        data[7, 2] = 80.0
        csv_path = str(tmp_path / "temp_test.csv")
        import pandas as pd
        pd.DataFrame(data).to_csv(csv_path, index=False)
        self.csv_path = csv_path
        self.loader = TempLoader(csv_path)

    def test_shape(self):
        assert self.loader.get_tempA().shape == (10, 10)

    def test_max_temp_full(self):
        assert self.loader.get_max_temp(0, 0, 10, 10) == pytest.approx(99.9)

    def test_max_temp_subregion(self):
        # 區域包含 (5,3) => max=99.9
        assert self.loader.get_max_temp(4, 2, 7, 5) == pytest.approx(99.9)

    def test_max_temp_miss_region(self):
        # 不包含高溫點的區域
        assert self.loader.get_max_temp(0, 0, 2, 2) == pytest.approx(25.0)

    def test_max_temp_coords(self):
        x, y = self.loader.get_max_temp_coords(0, 0, 10, 10)
        assert (x, y) == (5, 3)

    def test_max_temp_with_scale(self):
        # scale=2: 座標 (10,6,14,10) / 2 = (5,3,7,5) 包含 (5,3)
        assert self.loader.get_max_temp(10, 6, 14, 10, scale=2) == pytest.approx(99.9)

    def test_max_temp_in_circle(self):
        # 圓心 (5, 3) 半徑 1，應包含 (5,3)
        t = self.loader.get_max_temp_in_circle(5, 3, 1.5, scale=1)
        assert t == pytest.approx(99.9)

    def test_max_temp_in_circle_miss(self):
        # 圓心 (0, 0) 半徑 1，不包含 (5,3)
        t = self.loader.get_max_temp_in_circle(0, 0, 1, scale=1)
        assert t == pytest.approx(25.0)

    def test_max_temp_coords_in_circle(self):
        x, y = self.loader.get_max_temp_coords_in_circle(5, 3, 2, scale=1)
        assert (x, y) == (5, 3)

    def test_max_temp_in_polygon(self):
        # 正方形包含 (5, 3)
        corners = [(4, 2), (7, 2), (7, 5), (4, 5)]
        t = self.loader.get_max_temp_in_polygon(corners, scale=1)
        assert t == pytest.approx(99.9)

    def test_max_temp_coords_in_polygon(self):
        corners = [(4, 2), (7, 2), (7, 5), (4, 5)]
        x, y = self.loader.get_max_temp_coords_in_polygon(corners, scale=1)
        assert (x, y) == (5, 3)


# ═══════════════════════════════════════════════════════════════════════════
# 10. TestColorRange
# ═══════════════════════════════════════════════════════════════════════════
class TestColorRange:
    """color_range.py 綠色 mask 辨識"""

    def test_color_ranges_dict(self):
        assert "绿色" in color_ranges
        assert "红色" in color_ranges

    def test_green_range_values(self):
        lo, hi = color_ranges["绿色"]
        assert lo[0] < hi[0]  # H_min < H_max

    def test_mask_boundary_green_image(self):
        """純綠色影像 → 遮罩全部為 255"""
        green_bgr = np.zeros((50, 50, 3), dtype=np.uint8)
        green_bgr[:, :] = (0, 200, 0)  # BGR: B=0, G=200, R=0
        mask = get_mask_boundary(green_bgr)
        assert mask.shape == (50, 50)
        assert np.mean(mask) > 200  # 大部分應為 255

    def test_mask_boundary_black_image(self):
        """純黑影像 → 遮罩幾乎全為 0"""
        black = np.zeros((50, 50, 3), dtype=np.uint8)
        mask = get_mask_boundary(black)
        assert np.sum(mask) == 0

    def test_mask_boundary_raises_on_none(self):
        with pytest.raises(ValueError):
            get_mask_boundary(None)

    def test_mask_boundary_mixed(self):
        """左半綠色、右半紅色"""
        img = np.zeros((50, 100, 3), dtype=np.uint8)
        img[:, :50] = (0, 200, 0)   # 綠色
        img[:, 50:] = (0, 0, 200)   # 紅色
        mask = get_mask_boundary(img)
        green_area = np.sum(mask[:, :50] > 0)
        red_area = np.sum(mask[:, 50:] > 0)
        assert green_area > red_area


# ═══════════════════════════════════════════════════════════════════════════
# 11. Integration: PointTransformer + CoordinateConverter
# ═══════════════════════════════════════════════════════════════════════════
class TestIntegrationTransformerConverter:
    """座標變換 → 原點轉換鏈"""

    def test_A2B_then_convert_origin(self):
        pA = [[0, 0], [100, 0], [0, 100]]
        pB = [[10, 10], [110, 10], [10, 110]]
        t = PointTransformer(pA, pB)
        bx, by = t.A2B(50, 50)
        converter = CoordinateConverter(200, 200)
        rx, ry = converter.convert_coordinate(bx, by, "左上角", "右下角")
        # 反向驗證
        bx2, by2 = converter.convert_coordinate(rx, ry, "右下角", "左上角")
        assert (bx2, by2) == pytest.approx((bx, by), abs=0.01)

    def test_convert_then_B2A(self):
        pA = [[100, 100], [200, 100], [100, 200]]
        pB = [[200, 150], [300, 150], [200, 250]]
        t = PointTransformer(pA, pB)
        converter = CoordinateConverter(400, 400)
        # 先從右下角座標轉為左上角
        x_tl, y_tl = converter.convert_coordinate(200, 200, "右下角", "左上角")
        # 再從 B 轉回 A
        ax, ay = t.B2A(x_tl, y_tl)
        # 驗證可 roundtrip
        bx, by = t.A2B(ax, ay)
        assert (bx, by) == pytest.approx((x_tl, y_tl), abs=1.0)


# ═══════════════════════════════════════════════════════════════════════════
# 12. Integration: rotation_utils + draw_rect
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.skipif(not _tk_available, reason="tkinter not available")
class TestIntegrationRotationDrawRect:
    """旋轉頂點 → 名稱定位永遠在最高點上方"""

    @pytest.fixture(autouse=True)
    def reset_config(self, tmp_path, monkeypatch):
        GlobalConfig._instance = None
        if hasattr(GlobalConfig, '_initialized'):
            del GlobalConfig._initialized
        monkeypatch.chdir(tmp_path)

    def test_name_above_highest_point_various_angles(self):
        for angle in [0, 15, 30, 45, 60, 90, 120, 180, 270]:
            corners = get_rotated_corners(200, 200, 60, 30, angle)
            _, name_y = calc_name_position_for_rotated(corners, scale=1.0, gap=3)
            min_y = min(c[1] for c in corners)
            assert name_y < min_y, f"angle={angle}: name_y={name_y} >= min_y={min_y}"

    def test_rotated_corners_fed_to_name_position(self):
        corners = get_rotated_corners(100, 100, 40, 20, 37)
        cx, ny = calc_name_position_for_rotated(corners, scale=1.5, gap=5)
        min_y = min(c[1] for c in corners)
        assert ny < min_y
        # cx 應在 x 範圍內
        xs = [c[0] for c in corners]
        assert min(xs) - 10 <= cx <= max(xs) + 10


# ═══════════════════════════════════════════════════════════════════════════
# 13. Integration: GlobalConfig 完整生命週期
# ═══════════════════════════════════════════════════════════════════════════
class TestIntegrationConfigRoundTrip:
    """set → save → clear → load → verify（含中文 Unicode）"""

    @pytest.fixture(autouse=True)
    def reset(self, tmp_path, monkeypatch):
        GlobalConfig._instance = None
        if hasattr(GlobalConfig, '_initialized'):
            del GlobalConfig._initialized
        monkeypatch.chdir(tmp_path)

    def test_full_lifecycle(self, tmp_path):
        cfg = GlobalConfig()
        cfg.set("theme", "dark")
        cfg.set("count", 42)
        cfg.set("名稱", "熱力圖分析工具")
        json_file = str(tmp_path / "config" / "lifecycle.json")
        cfg.save_to_json(json_file)

        cfg.clear()
        assert cfg.get("theme") is None

        cfg.load_from_json(json_file)
        assert cfg.get("theme") == "dark"
        assert cfg.get("count") == 42
        assert cfg.get("名稱") == "熱力圖分析工具"

    def test_multiple_save_load_cycles(self, tmp_path):
        json_file = str(tmp_path / "config" / "multi.json")
        for i in range(5):
            GlobalConfig._instance = None
            if hasattr(GlobalConfig, '_initialized'):
                del GlobalConfig._initialized
            cfg = GlobalConfig()
            cfg.set("iteration", i)
            cfg.save_to_json(json_file)

        GlobalConfig._instance = None
        if hasattr(GlobalConfig, '_initialized'):
            del GlobalConfig._initialized
        cfg = GlobalConfig()
        cfg.load_from_json(json_file)
        assert cfg.get("iteration") == 4


# ═══════════════════════════════════════════════════════════════════════════
# 14. Integration: CanvasRectItem + JSON
# ═══════════════════════════════════════════════════════════════════════════
class TestIntegrationCanvasRectItemJson:
    """to_dict → json.dumps → json.loads → reconstruct"""

    def test_json_roundtrip(self):
        item = CanvasRectItem(10, 20, 110, 120, 60, 70, 85.5, "U1", 1, 2)
        d = item.to_dict()
        s = json.dumps(d)
        d2 = json.loads(s)
        item2 = CanvasRectItem(**d2)
        assert item2.x1 == item.x1
        assert item2.max_temp == item.max_temp
        assert item2.name == item.name

    def test_json_list_roundtrip(self):
        items = [
            CanvasRectItem(0, 0, 50, 50, 25, 25, 60.0, "R1"),
            CanvasRectItem(100, 100, 200, 200, 150, 150, 90.0, "C2"),
        ]
        data = [it.to_dict() for it in items]
        s = json.dumps(data)
        data2 = json.loads(s)
        reconstructed = [CanvasRectItem(**d) for d in data2]
        assert len(reconstructed) == 2
        assert reconstructed[0].name == "R1"
        assert reconstructed[1].max_temp == 90.0

    def test_unicode_name_roundtrip(self):
        item = CanvasRectItem(0, 0, 10, 10, 5, 5, 50.0, "電容C1")
        s = json.dumps(item.to_dict(), ensure_ascii=False)
        d2 = json.loads(s)
        assert d2["name"] == "電容C1"


# ═══════════════════════════════════════════════════════════════════════════
# 15. Integration: PointTransformer 壓力測試
# ═══════════════════════════════════════════════════════════════════════════
class TestIntegrationTransformerStress:
    """隨機 3/4 點集、大座標、roundtrip 精度 < 1px"""

    def test_random_3_point_roundtrip(self):
        rng = np.random.RandomState(42)
        for _ in range(10):
            pA = rng.randint(0, 1000, size=(3, 2)).tolist()
            # 建立已知的仿射變換：平移 + 縮放
            offset = rng.randint(-200, 200, size=2)
            pB = [[p[0] + offset[0], p[1] + offset[1]] for p in pA]
            t = PointTransformer(pA, pB)
            test_x, test_y = rng.randint(0, 1000, size=2).tolist()
            bx, by = t.A2B(test_x, test_y)
            ax, ay = t.B2A(bx, by)
            assert (ax, ay) == pytest.approx((test_x, test_y), abs=1.0)

    def test_random_4_point_roundtrip(self):
        rng = np.random.RandomState(123)
        for _ in range(10):
            pA = rng.randint(0, 500, size=(4, 2)).tolist()
            offset = rng.randint(-100, 100, size=2)
            pB = [[p[0] + offset[0], p[1] + offset[1]] for p in pA]
            t = PointTransformer(pA, pB)
            test_x, test_y = rng.randint(0, 500, size=2).tolist()
            bx, by = t.A2B(test_x, test_y)
            ax, ay = t.B2A(bx, by)
            assert (ax, ay) == pytest.approx((test_x, test_y), abs=1.0)

    def test_large_coordinates(self):
        pA = [[0, 0], [10000, 0], [10000, 10000]]
        pB = [[5000, 5000], [15000, 5000], [15000, 15000]]
        t = PointTransformer(pA, pB)
        bx, by = t.A2B(5000, 5000)
        ax, ay = t.B2A(bx, by)
        assert (ax, ay) == pytest.approx((5000, 5000), abs=1.0)


# ═══════════════════════════════════════════════════════════════════════════
# 報告
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
