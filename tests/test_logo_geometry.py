import math

from alexandria.gui.logo_geometry import (
    apply_spin_squish,
    diamond_points,
    extrusion_side_quads,
    is_facing_viewer,
    offset_points,
    pinwheel_diamond_centers,
    pinwheel_diamond_rotation,
    rotate_points,
    scale_for_canvas,
    scale_points,
    shade_color,
)


def test_diamond_points_has_four_corners():
    points = diamond_points(0, 0, width=10, height=20)
    assert len(points) == 4


def test_diamond_points_are_centered_on_the_given_point():
    points = diamond_points(center_x=50, center_y=100, width=10, height=20)
    top, right, bottom, left = points
    assert top == (50, 90)
    assert right == (55, 100)
    assert bottom == (50, 110)
    assert left == (45, 100)


def test_pinwheel_has_three_centers():
    centers = pinwheel_diamond_centers(0, 0, radius=10)
    assert len(centers) == 3


def test_pinwheel_centers_are_120_degrees_apart():
    centers = pinwheel_diamond_centers(center_x=0, center_y=0, radius=10)
    # First center should point straight up: (0, -10).
    x0, y0 = centers[0]
    assert math.isclose(x0, 0, abs_tol=1e-9)
    assert math.isclose(y0, -10, abs_tol=1e-9)

    # All three should be equidistant from the shared center.
    for x, y in centers:
        distance = math.hypot(x, y)
        assert math.isclose(distance, 10, rel_tol=1e-9)


def test_pinwheel_diamond_rotation_first_diamond_stays_upright():
    assert pinwheel_diamond_rotation(0) == 0


def test_rotate_points_by_zero_degrees_is_unchanged():
    points = [(10, 5), (20, 15)]
    result = rotate_points(points, center=(0, 0), angle_degrees=0)
    for (ox, oy), (rx, ry) in zip(points, result):
        assert math.isclose(ox, rx, abs_tol=1e-9)
        assert math.isclose(oy, ry, abs_tol=1e-9)


def test_rotate_points_does_not_mutate_input():
    points = [(10, 5)]
    rotate_points(points, center=(0, 0), angle_degrees=90)
    assert points == [(10, 5)]


def test_pinwheel_rotation_points_each_diamond_outward_from_center():
    # Applying each diamond's own rotation to the default "up" tip of a
    # diamond centered at the origin should land it pointing the same
    # direction its actual pinwheel center sits away from the shared axis
    # — i.e. diamond 0 straight up, diamond 1 down-left, diamond 2
    # down-right, matching pinwheel_diamond_centers' layout.
    centers = pinwheel_diamond_centers(center_x=0, center_y=0, radius=1)
    up_tip = [(0, -1)]  # the "top" point of an unrotated diamond

    for index, (expected_x, expected_y) in enumerate(centers):
        rotation = pinwheel_diamond_rotation(index)
        (rotated_x, rotated_y) = rotate_points(up_tip, center=(0, 0), angle_degrees=rotation)[0]
        assert math.isclose(rotated_x, expected_x, abs_tol=1e-9)
        assert math.isclose(rotated_y, expected_y, abs_tol=1e-9)


def test_spin_squish_at_zero_degrees_is_unchanged():
    points = [(10, 5), (20, 15)]
    result = apply_spin_squish(points, axis_x=0, angle_degrees=0)
    for (ox, oy), (rx, ry) in zip(points, result):
        assert math.isclose(ox, rx, abs_tol=1e-9)
        assert math.isclose(oy, ry, abs_tol=1e-9)


def test_spin_squish_at_90_degrees_flattens_to_the_axis():
    points = [(10, 5), (30, 15)]
    result = apply_spin_squish(points, axis_x=0, angle_degrees=90)
    for x, _y in result:
        assert math.isclose(x, 0, abs_tol=1e-9)


def test_spin_squish_at_180_degrees_mirrors_across_the_axis():
    points = [(10, 5)]
    result = apply_spin_squish(points, axis_x=0, angle_degrees=180)
    (x, y) = result[0]
    assert math.isclose(x, -10, abs_tol=1e-9)
    assert math.isclose(y, 5, abs_tol=1e-9)


def test_spin_squish_preserves_y_and_does_not_mutate_input():
    points = [(10, 5)]
    apply_spin_squish(points, axis_x=0, angle_degrees=45)
    assert points == [(10, 5)]  # original list untouched


def test_spin_squish_default_depth_matches_no_depth_argument():
    points = [(10, 5), (30, 15)]
    for angle in (0, 37, 90, 180, 271):
        default = apply_spin_squish(points, axis_x=0, angle_degrees=angle)
        explicit_zero = apply_spin_squish(points, axis_x=0, angle_degrees=angle, depth=0.0)
        assert default == explicit_zero


def test_spin_squish_depth_vanishes_when_facing_the_viewer():
    # A point genuinely behind another (same x, y, different depth) must
    # land at the exact same screen position at angle 0 or 180 — that's
    # what "directly behind, no offset" actually means: true occlusion,
    # only separating as the shape turns away from facing the viewer.
    points = [(10, 5)]
    for angle in (0, 180, 360):
        (fx, fy) = apply_spin_squish(points, axis_x=0, angle_degrees=angle, depth=0.0)[0]
        (bx, by) = apply_spin_squish(points, axis_x=0, angle_degrees=angle, depth=25.0)[0]
        assert math.isclose(fx, bx, abs_tol=1e-9)
        assert math.isclose(fy, by, abs_tol=1e-9)


def test_spin_squish_depth_separates_away_from_zero_and_180():
    points = [(10, 5)]
    front = apply_spin_squish(points, axis_x=0, angle_degrees=45, depth=0.0)
    behind = apply_spin_squish(points, axis_x=0, angle_degrees=45, depth=25.0)
    assert front != behind
    assert not math.isclose(front[0][0], behind[0][0], abs_tol=1e-9)


def test_spin_squish_depth_at_90_degrees_shifts_by_the_full_depth():
    # At the edge-on point cos(90)=0, so the reference plane collapses
    # exactly onto the axis — a point at `depth` behind it should show up
    # exactly `depth` away from the axis, the full parallax swing.
    points = [(10, 5)]
    result = apply_spin_squish(points, axis_x=0, angle_degrees=90, depth=25.0)
    (x, _y) = result[0]
    assert math.isclose(x, 25.0, abs_tol=1e-9)


def test_is_facing_viewer_true_at_zero_degrees():
    assert is_facing_viewer(0) is True


def test_is_facing_viewer_false_at_180_degrees():
    assert is_facing_viewer(180) is False


def test_is_facing_viewer_flips_between_front_and_back_half():
    assert is_facing_viewer(45) is True
    assert is_facing_viewer(135) is False
    assert is_facing_viewer(225) is False
    assert is_facing_viewer(315) is True


def test_shade_color_darkens_by_factor():
    assert shade_color("#2dd4bf", 0.5) == "#166a60"


def test_shade_color_full_factor_is_unchanged():
    assert shade_color("#2dd4bf", 1.0) == "#2dd4bf"


def test_shade_color_clamps_to_black_and_white():
    assert shade_color("#000000", 0.5) == "#000000"
    assert shade_color("#ffffff", 2.0) == "#ffffff"


def test_shade_color_accepts_color_without_leading_hash():
    assert shade_color("2dd4bf", 0.5) == "#166a60"


def test_offset_points_translates_by_dx_dy():
    points = [(10, 5), (20, 15)]
    result = offset_points(points, dx=3, dy=-2)
    assert result == [(13, 3), (23, 13)]


def test_scale_points_shrinks_toward_center():
    points = [(20, 0), (0, 20)]
    result = scale_points(points, center=(0, 0), factor=0.5)
    assert result == [(10, 0), (0, 10)]


def test_scale_points_at_factor_one_is_unchanged():
    points = [(10, 5), (20, 15)]
    result = scale_points(points, center=(3, 4), factor=1.0)
    for (ox, oy), (rx, ry) in zip(points, result):
        assert math.isclose(ox, rx, abs_tol=1e-9)
        assert math.isclose(oy, ry, abs_tol=1e-9)


def test_scale_points_leaves_the_center_point_itself_unchanged():
    points = [(50, 50)]
    result = scale_points(points, center=(50, 50), factor=0.3)
    assert result == [(50, 50)]


def test_scale_points_does_not_mutate_input():
    points = [(10, 5)]
    scale_points(points, center=(0, 0), factor=0.5)
    assert points == [(10, 5)]


def test_offset_points_does_not_mutate_input():
    points = [(10, 5)]
    offset_points(points, dx=3, dy=-2)
    assert points == [(10, 5)]


def test_extrusion_side_quads_returns_one_quad_per_edge():
    front = diamond_points(0, 0, width=10, height=20)
    back = offset_points(front, dx=4, dy=4)
    quads = extrusion_side_quads(front, back)
    assert len(quads) == 4
    assert all(len(quad) == 4 for quad in quads)


def test_extrusion_side_quads_connects_matching_edge_correctly():
    front = [(0, 0), (10, 0), (10, 10), (0, 10)]  # a simple square
    back = offset_points(front, dx=2, dy=2)
    quads = extrusion_side_quads(front, back)
    # The first quad should connect front[0]->front[1] with the
    # corresponding back points, in matching order (not crossed/twisted).
    assert quads[0] == [(0, 0), (10, 0), (12, 2), (2, 2)]


def test_scale_for_canvas_is_one_at_the_base_size():
    assert math.isclose(scale_for_canvas(130, 130, base_size=130), 1.0)


def test_scale_for_canvas_scales_up_for_a_bigger_canvas():
    assert math.isclose(scale_for_canvas(260, 260, base_size=130), 2.0)


def test_scale_for_canvas_uses_the_smaller_dimension():
    # A wide-but-short canvas should scale to fit the constrained
    # dimension, not overflow it by scaling off the larger one.
    assert math.isclose(scale_for_canvas(1000, 65, base_size=130), 0.5)


def test_scale_for_canvas_never_goes_below_the_minimum():
    assert scale_for_canvas(1, 1, base_size=130, minimum=0.3) == 0.3


def test_scale_for_canvas_respects_a_custom_minimum():
    assert scale_for_canvas(0, 0, base_size=130, minimum=0.1) == 0.1
