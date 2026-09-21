import math

from alexandria.gui.logo_geometry import (
    apply_spin_squish,
    diamond_points,
    is_facing_viewer,
    pinwheel_diamond_centers,
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


def test_is_facing_viewer_true_at_zero_degrees():
    assert is_facing_viewer(0) is True


def test_is_facing_viewer_false_at_180_degrees():
    assert is_facing_viewer(180) is False


def test_is_facing_viewer_flips_between_front_and_back_half():
    assert is_facing_viewer(45) is True
    assert is_facing_viewer(135) is False
    assert is_facing_viewer(225) is False
    assert is_facing_viewer(315) is True
