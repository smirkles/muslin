"""SVG pattern manipulation library for sewing pattern operations.

All functions are pure: they accept a Pattern and parameters, and return a NEW
Pattern object via deep copy.  The caller's Pattern is never mutated.

Coordinate system
-----------------
SVG uses a y-downward coordinate system (the y-axis increases toward the bottom
of the screen).  This is the OPPOSITE of standard mathematical convention where
y increases upward.  All rotation, translation, and geometric calculations in
this module use SVG convention (y-down) unless explicitly noted.

  - Positive dy moves an element DOWNWARD on screen.
  - A clockwise rotation in SVG space uses the standard clockwise rotation
    matrix for y-down: (x, y) -> (x*cos - y*sin,  x*sin + y*cos).
    For 90° CW: (x, y) -> (y, -x).

Supported element types
-----------------------
<path>    — coordinates in the ``d`` attribute (M/L/Z/C/Q/S commands)
<polygon> — coordinates in the ``points`` attribute
<line>    — coordinates in x1, y1, x2, y2 attributes
<g>       — group container; translate recurses into all descendant elements
<text>    — indexed by id; translate moves x/y attributes

Curve approximation
-------------------
For V1, Bezier control points (C/Q/S commands) are treated as plain coordinates
and transformed identically to anchor points.  This preserves shape under
translation but may introduce slight distortion under rotation for curved seams.
Flag for future work: implement true bezier transformation.
"""

from __future__ import annotations

import copy
import math
import re
from collections.abc import Callable
from pathlib import Path

import numpy as np
from lxml import etree

# ---------------------------------------------------------------------------
# SVG namespace
# ---------------------------------------------------------------------------

SVG_NS = "http://www.w3.org/2000/svg"
_NS = {"svg": SVG_NS}

# Tag helpers (with and without namespace prefix)
_PATH_TAGS = {f"{{{SVG_NS}}}path", "path"}
_POLYGON_TAGS = {f"{{{SVG_NS}}}polygon", "polygon"}
_LINE_TAGS = {f"{{{SVG_NS}}}line", "line"}
_TEXT_TAGS = {f"{{{SVG_NS}}}text", "text"}
_G_TAGS = {f"{{{SVG_NS}}}g", "g"}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class PatternError(Exception):
    """Base exception for all pattern_ops errors."""


class ElementNotFound(PatternError):
    """Raised when an element_id is not present in the pattern."""


class GeometryError(PatternError):
    """Raised when a geometric operation cannot be performed."""


# ---------------------------------------------------------------------------
# Pattern type
# ---------------------------------------------------------------------------


class Pattern:
    """Thin wrapper around an lxml ElementTree with O(1) element lookup by id.

    Attributes
    ----------
    _tree:     lxml ElementTree for the SVG document.
    _id_index: mapping from ``id`` attribute value → lxml Element.
    """

    def __init__(self, tree: etree._ElementTree, id_index: dict[str, etree._Element]) -> None:
        """Initialise from an already-parsed ElementTree and pre-built id index."""
        self._tree = tree
        self._id_index = id_index

    @classmethod
    def _from_tree(cls, tree: etree._ElementTree) -> Pattern:
        """Build a Pattern from an lxml ElementTree, constructing the id index."""
        root = tree.getroot()
        id_index: dict[str, etree._Element] = {}
        for el in root.iter():
            eid = el.get("id")
            if eid:
                id_index[eid] = el
        return cls(tree, id_index)

    def _deep_copy(self) -> Pattern:
        """Return a new Pattern that is a complete deep copy of this one."""
        new_root = copy.deepcopy(self._tree.getroot())
        new_tree = etree.ElementTree(new_root)
        return Pattern._from_tree(new_tree)


# ---------------------------------------------------------------------------
# Path ``d`` attribute parsing and serialisation
# ---------------------------------------------------------------------------

# Regex that splits a path ``d`` string into tokens (commands and numbers).
_TOKEN_RE = re.compile(
    r"([MmLlHhVvCcSsQqTtAaZz])"  # command letters
    r"|([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)"  # numbers (including scientific)
)


def _parse_path_d(d: str) -> list[tuple[str, list[float]]]:
    """Parse an SVG path ``d`` attribute into a list of (command, [numbers]) tuples.

    Only absolute commands (upper-case) are produced; relative commands are
    NOT normalised here — they are returned as-is with their original letter.

    This is intentionally minimal: we only need to transform coordinate values,
    not to fully interpret path semantics.
    """
    tokens = _TOKEN_RE.findall(d)
    commands: list[tuple[str, list[float]]] = []
    current_cmd: str | None = None
    current_nums: list[float] = []

    for cmd_tok, num_tok in tokens:
        if cmd_tok:
            if current_cmd is not None:
                commands.append((current_cmd, current_nums))
            current_cmd = cmd_tok
            current_nums = []
        elif num_tok:
            current_nums.append(float(num_tok))

    if current_cmd is not None:
        commands.append((current_cmd, current_nums))

    return commands


def _format_coord(v: float) -> str:
    """Format a float coordinate for SVG output (strip unnecessary trailing zeros)."""
    if v == int(v):
        return str(int(v))
    return f"{v:.6g}"


def _serialise_path_d(commands: list[tuple[str, list[float]]]) -> str:
    """Serialise a list of (command, numbers) back to an SVG ``d`` string."""
    parts: list[str] = []
    for cmd, nums in commands:
        if nums:
            coord_str = " ".join(_format_coord(n) for n in nums)
            parts.append(f"{cmd} {coord_str}")
        else:
            parts.append(cmd)
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Coordinate pairs per command repetition (endpoint is the LAST pair).
# Used to correctly resolve relative offsets for multi-pair commands (C, S, Q).
_CMD_STRIDE: dict[str, int] = {
    "M": 1,
    "L": 1,
    "C": 3,  # x1 y1 x2 y2 x y  — endpoint is pair index 2
    "S": 2,  # x2 y2 x y        — endpoint is pair index 1
    "Q": 2,  # x1 y1 x y        — endpoint is pair index 1
    "T": 1,
}


def _transform_path_coords(
    d: str,
    fn: Callable[[float, float], tuple[float, float]],
) -> str:
    """Apply a 2-argument (x, y) → (x', y') transform to all coordinates in a path d.

    All relative commands (lowercase) are resolved to absolute coordinates
    using the tracked pen position before the transform is applied.  The output
    always uses uppercase commands.

    H and V are promoted to L by resolving the missing axis from the tracked
    pen position.  This is necessary for rotation, where a horizontal line is
    no longer horizontal after the transform.

    For multi-pair commands (C, S, Q), every pair's relative offset is measured
    from the pen position at the START of that command repetition.

    V1 assumption: Bezier control points are transformed identically to anchor
    points (slight distortion under rotation for curved seams; flagged for v2).
    """
    commands = _parse_path_d(d)
    result: list[tuple[str, list[float]]] = []
    cur_x, cur_y = 0.0, 0.0  # current pen position in original coords
    start_x, start_y = 0.0, 0.0  # subpath start (for Z)

    for cmd, nums in commands:
        upper = cmd.upper()
        is_rel = cmd.islower() and upper != "Z"

        if upper == "Z":
            result.append((cmd, []))
            cur_x, cur_y = start_x, start_y
            continue

        if upper == "H":
            # Promote H/h → L by supplying the current y from the pen
            new_nums: list[float] = []
            for x in nums:
                abs_x = cur_x + x if is_rel else x
                x2, y2 = fn(abs_x, cur_y)
                new_nums.extend([x2, y2])
                cur_x = abs_x
            result.append(("L", new_nums))
            continue

        if upper == "V":
            # Promote V/v → L by supplying the current x from the pen
            new_nums = []
            for y in nums:
                abs_y = cur_y + y if is_rel else y
                x2, y2 = fn(cur_x, abs_y)
                new_nums.extend([x2, y2])
                cur_y = abs_y
            result.append(("L", new_nums))
            continue

        if upper == "A":
            # Arc: rx ry x-rotation large-arc sweep x y (7 params per arc).
            # Only the endpoint (indices 5,6) is a coordinate; others are
            # arc parameters and must not be transformed.
            new_nums = list(nums)
            rep_x, rep_y = cur_x, cur_y
            i = 0
            while i + 6 < len(nums):
                abs_x = rep_x + nums[i + 5] if is_rel else nums[i + 5]
                abs_y = rep_y + nums[i + 6] if is_rel else nums[i + 6]
                x2, y2 = fn(abs_x, abs_y)
                new_nums[i + 5] = x2
                new_nums[i + 6] = y2
                rep_x, rep_y = abs_x, abs_y
                cur_x, cur_y = abs_x, abs_y
                i += 7
            result.append(("A", new_nums))
            continue

        # M, L, C, S, Q, T
        # For relative commands, all offsets within one repetition are measured
        # from the pen position at the START of that repetition (not cumulative).
        stride = _CMD_STRIDE.get(upper, 1)
        stride_floats = stride * 2  # number of floats per repetition

        new_nums = []
        i = 0
        rep_start_x, rep_start_y = cur_x, cur_y

        while i + 1 < len(nums):
            pair_in_rep = (i % stride_floats) // 2

            # New repetition: update rep_start to the previous endpoint
            if pair_in_rep == 0 and i > 0:
                rep_start_x, rep_start_y = cur_x, cur_y

            abs_x = rep_start_x + nums[i] if is_rel else nums[i]
            abs_y = rep_start_y + nums[i + 1] if is_rel else nums[i + 1]
            x2, y2 = fn(abs_x, abs_y)
            new_nums.extend([x2, y2])

            # Advance pen to endpoint (last pair in the repetition)
            if pair_in_rep == stride - 1:
                cur_x, cur_y = abs_x, abs_y
                # Per SVG spec, only the first pair of an M block sets subpath start.
                # Subsequent pairs are implicit lineto's and must not reset it.
                if upper == "M" and i == 0:
                    start_x, start_y = cur_x, cur_y

            i += 2

        if i < len(nums):
            new_nums.append(nums[i])  # odd trailing number — guard only
        result.append((upper, new_nums))

    return _serialise_path_d(result)


# ---------------------------------------------------------------------------
# Polygon ``points`` attribute helpers
# ---------------------------------------------------------------------------


def _parse_polygon_points(points: str) -> list[tuple[float, float]]:
    """Parse an SVG polygon ``points`` attribute into a list of (x, y) tuples."""
    nums = [float(t) for t in re.split(r"[,\s]+", points.strip()) if t]
    return [(nums[i], nums[i + 1]) for i in range(0, len(nums) - 1, 2)]


def _serialise_polygon_points(pts: list[tuple[float, float]]) -> str:
    """Serialise a list of (x, y) tuples back to a polygon ``points`` string."""
    return " ".join(f"{_format_coord(x)},{_format_coord(y)}" for x, y in pts)


# ---------------------------------------------------------------------------
# Rotation math
# ---------------------------------------------------------------------------


def _rotation_matrix(angle_deg: float) -> np.ndarray:
    """Return a 2x2 clockwise rotation matrix for SVG (y-down) coordinate space.

    In SVG (y-down), a positive angle rotates CLOCKWISE on screen.
    The matrix is:
        [ cos(θ)  sin(θ) ]
        [-sin(θ)  cos(θ) ]

    For 90° CW: (x, y) → (y, -x).
    """
    theta = math.radians(angle_deg)
    c, s = math.cos(theta), math.sin(theta)
    return np.array([[c, s], [-s, c]])


def _make_rotate_fn(
    angle_deg: float,
    pivot: tuple[float, float],
) -> Callable[[float, float], tuple[float, float]]:
    """Return a coordinate-pair transform function for rotation around a pivot."""
    R = _rotation_matrix(angle_deg)
    px, py = pivot

    def rotate(x: float, y: float) -> tuple[float, float]:
        v = np.array([x - px, y - py])
        v2 = R @ v
        return float(v2[0] + px), float(v2[1] + py)

    return rotate


# ---------------------------------------------------------------------------
# Public API — load / render / get
# ---------------------------------------------------------------------------


def load_pattern(svg_path: Path) -> Pattern:
    """Parse an SVG file and return a Pattern with all elements accessible by id."""
    try:
        tree = etree.parse(str(svg_path))
    except OSError as exc:
        raise PatternError(f"Cannot open SVG file: {svg_path}") from exc
    except etree.XMLSyntaxError as exc:
        raise PatternError(f"Invalid SVG/XML in {svg_path}: {exc}") from exc
    return Pattern._from_tree(tree)


def render_pattern(pattern: Pattern) -> str:
    """Serialise a Pattern back to an SVG string."""
    return etree.tostring(
        pattern._tree.getroot(),
        pretty_print=True,
        xml_declaration=True,
        encoding="utf-8",
    ).decode("utf-8")


def get_element(pattern: Pattern, element_id: str) -> etree._Element:
    """Return the lxml Element with the given id, or raise ElementNotFound."""
    el = pattern._id_index.get(element_id)
    if el is None:
        raise ElementNotFound(f"Element '{element_id}' not found in pattern")
    return el


# ---------------------------------------------------------------------------
# Element transformation helpers
# ---------------------------------------------------------------------------


def _translate_element(el: etree._Element, dx: float, dy: float) -> None:
    """Translate a single lxml element in-place by (dx, dy).

    Modifies the element directly — caller must be working on a deep copy.
    Supports <path>, <polygon>, <line>, <text>.
    """
    tag = el.tag

    if tag in _PATH_TAGS:
        d = el.get("d", "")
        el.set("d", _transform_path_coords(d, lambda x, y: (x + dx, y + dy)))

    elif tag in _POLYGON_TAGS:
        pts = _parse_polygon_points(el.get("points", ""))
        shifted = [(x + dx, y + dy) for x, y in pts]
        el.set("points", _serialise_polygon_points(shifted))

    elif tag in _LINE_TAGS:
        for attr_x, attr_y in (("x1", "y1"), ("x2", "y2")):
            x = float(el.get(attr_x, 0))
            y = float(el.get(attr_y, 0))
            el.set(attr_x, _format_coord(x + dx))
            el.set(attr_y, _format_coord(y + dy))

    elif tag in _TEXT_TAGS:
        x = float(el.get("x", 0))
        y = float(el.get("y", 0))
        el.set("x", _format_coord(x + dx))
        el.set("y", _format_coord(y + dy))

    elif tag in _G_TAGS:
        # Recurse into all direct children; this handles nested <g> automatically
        # because each child <g> will again hit this branch.
        for child in el:
            _translate_element(child, dx, dy)


def _rotate_element(
    el: etree._Element,
    angle_deg: float,
    pivot: tuple[float, float],
) -> None:
    """Rotate a single lxml element in-place around a pivot point.

    Modifies the element directly — caller must be working on a deep copy.
    """
    rotate = _make_rotate_fn(angle_deg, pivot)
    tag = el.tag

    if tag in _PATH_TAGS:
        d = el.get("d", "")
        el.set("d", _transform_path_coords(d, rotate))

    elif tag in _POLYGON_TAGS:
        pts = _parse_polygon_points(el.get("points", ""))
        rotated = [rotate(x, y) for x, y in pts]
        el.set("points", _serialise_polygon_points(rotated))

    elif tag in _LINE_TAGS:
        for attr_x, attr_y in (("x1", "y1"), ("x2", "y2")):
            x = float(el.get(attr_x, 0))
            y = float(el.get(attr_y, 0))
            x2, y2 = rotate(x, y)
            el.set(attr_x, _format_coord(x2))
            el.set(attr_y, _format_coord(y2))

    elif tag in _TEXT_TAGS:
        x = float(el.get("x", 0))
        y = float(el.get("y", 0))
        x2, y2 = rotate(x, y)
        el.set("x", _format_coord(x2))
        el.set("y", _format_coord(y2))


# ---------------------------------------------------------------------------
# Public API — geometric operations
# ---------------------------------------------------------------------------


def translate_element(
    pattern: Pattern,
    element_id: str,
    dx: float,
    dy: float,
) -> Pattern:
    """Move element ``element_id`` by (dx, dy); return a new Pattern.

    Raises ElementNotFound if element_id is not in the pattern.
    SVG convention: positive dy moves the element downward on screen.
    """
    # Validate before copying for a cleaner error (no wasted allocation)
    if element_id not in pattern._id_index:
        raise ElementNotFound(f"Element '{element_id}' not found in pattern")

    new_pattern = pattern._deep_copy()
    el = new_pattern._id_index[element_id]
    _translate_element(el, dx, dy)
    return new_pattern


def rotate_element(
    pattern: Pattern,
    element_id: str,
    angle_deg: float,
    pivot: tuple[float, float],
) -> Pattern:
    """Rotate element ``element_id`` by ``angle_deg`` clockwise around ``pivot``; return a new Pattern.

    In SVG (y-down) space, positive angles produce clockwise screen rotation.
    For example: rotate_element(p, "foo", 90, (0, 0)) maps (1,0) → (0,-1).

    Raises ElementNotFound if element_id is not in the pattern.
    """
    if element_id not in pattern._id_index:
        raise ElementNotFound(f"Element '{element_id}' not found in pattern")

    new_pattern = pattern._deep_copy()
    el = new_pattern._id_index[element_id]
    _rotate_element(el, angle_deg, pivot)
    return new_pattern


def scale_element(
    pattern: Pattern,
    element_id: str,
    sx: float,
    sy: float,
    pivot: tuple[float, float],
) -> Pattern:
    """Scale element ``element_id`` by (sx, sy) around ``pivot``; return a new Pattern.

    The transform applied to each coordinate is:
        x' = pivot_x + (x - pivot_x) * sx
        y' = pivot_y + (y - pivot_y) * sy

    For a <g> element, all descendants are scaled around the SAME pivot (the
    pivot computed once at the piece level, not per-child bounding-box centres).

    Raises ElementNotFound if element_id is not in the pattern.
    """
    if element_id not in pattern._id_index:
        raise ElementNotFound(f"Element '{element_id}' not found in pattern")

    new_pattern = pattern._deep_copy()
    el = new_pattern._id_index[element_id]
    _scale_element(el, sx, sy, pivot)
    return new_pattern


def slash_line(
    pattern: Pattern,
    from_pt: tuple[float, float],
    to_pt: tuple[float, float],
    slash_id: str,
) -> Pattern:
    """Add a <line> element to the pattern as a slash/spread guide; return a new Pattern.

    The line does not split any existing geometry — it is a marker that
    ``spread_at_line`` uses to determine where to divide the pattern.

    The element is appended as a direct child of the SVG root (or the first <g>
    if a top-level group is present).
    """
    new_pattern = pattern._deep_copy()
    root = new_pattern._tree.getroot()

    # Build the line element (with namespace if root uses one)
    ns_uri = _element_namespace(root)
    if ns_uri:
        tag = f"{{{ns_uri}}}line"
    else:
        tag = "line"

    line_el = etree.SubElement(root, tag)
    line_el.set("id", slash_id)
    line_el.set("x1", _format_coord(from_pt[0]))
    line_el.set("y1", _format_coord(from_pt[1]))
    line_el.set("x2", _format_coord(to_pt[0]))
    line_el.set("y2", _format_coord(to_pt[1]))
    line_el.set("stroke", "red")
    line_el.set("stroke-width", "1")
    line_el.set("stroke-dasharray", "4,2")

    # Update the index
    new_pattern._id_index[slash_id] = line_el
    return new_pattern


def spread_at_line(
    pattern: Pattern,
    slash_id: str,
    distance: float,
    direction: tuple[float, float],
) -> Pattern:
    """Split the pattern at a slash line and spread one side by ``distance`` in ``direction``.

    Assumptions (V1 — document these for future callers):
    - The slash line is a straight <line> element added by ``slash_line``.
    - The pattern is topologically simple (no holes, no overlapping regions).
    - Elements are classified by the position of their geometric centroid relative
      to the slash line.  Elements whose centroid lies on or to the *right* of the
      directed line (from_pt → to_pt) are translated.  Elements on the left are
      left in place.  Elements crossing the line are translated with the right side
      (conservative choice — flag for future improvement).
    - The slash line element itself is extended by ``distance`` in ``direction``
      to cover the gap.

    Raises GeometryError if ``slash_id`` is not in the pattern.
    """
    if slash_id not in pattern._id_index:
        raise GeometryError(f"Slash line '{slash_id}' not found in pattern")

    slash_el = pattern._id_index[slash_id]
    x1 = float(slash_el.get("x1", 0))
    y1 = float(slash_el.get("y1", 0))
    x2 = float(slash_el.get("x2", 0))
    y2 = float(slash_el.get("y2", 0))

    # Direction vector along the slash line (from_pt → to_pt)
    line_vec = np.array([x2 - x1, y2 - y1], dtype=float)
    line_len = float(np.linalg.norm(line_vec))

    # Perpendicular (right-side normal in y-down SVG space)
    if line_len > 1e-9:
        normal = np.array([line_vec[1], -line_vec[0]]) / line_len
    else:
        normal = np.array([1.0, 0.0])

    dx = direction[0] * distance
    dy = direction[1] * distance

    new_pattern = pattern._deep_copy()
    root = new_pattern._tree.getroot()

    for el in root.iter():
        eid = el.get("id")
        if eid == slash_id:
            continue  # handled separately below

        centroid = _element_centroid(el)
        if centroid is None:
            continue

        # Signed distance from centroid to the slash line
        # Positive → right side (translate); negative → left side (leave)
        rel = np.array([centroid[0] - x1, centroid[1] - y1])
        signed_dist = float(np.dot(rel, normal))

        if signed_dist >= 0:
            _translate_element(el, dx, dy)

    # Extend the slash line to cover the gap
    slash_copy = new_pattern._id_index[slash_id]
    slash_copy.set("x2", _format_coord(float(slash_copy.get("x2")) + dx))
    slash_copy.set("y2", _format_coord(float(slash_copy.get("y2")) + dy))

    return new_pattern


def add_dart(
    pattern: Pattern,
    position: tuple[float, float],
    width: float,
    length: float,
    angle_deg: float,
    dart_id: str,
) -> Pattern:
    """Add a dart-shaped triangle polygon to the pattern; return a new Pattern.

    The dart is modelled as an isosceles triangle:
    - Tip (apex) at ``position``.
    - Base centred along the direction defined by ``angle_deg`` (measured
      clockwise from the positive-x axis in SVG y-down space).
    - ``width`` is the base width of the dart.
    - ``length`` is the distance from tip to base centre.

    Convention: ``position`` should be the interior-facing point (i.e., toward
    the pattern body), and ``angle_deg`` should point toward the seam edge.
    Callers are responsible for choosing these values to produce a dart that
    points toward the pattern interior; this function does not validate
    orientation.

    The element is appended to the SVG root and registered in the id index.
    """
    new_pattern = pattern._deep_copy()
    root = new_pattern._tree.getroot()

    # Tip of the dart
    tip = np.array(position, dtype=float)

    # Direction from tip toward base (angle_deg CW from +x in SVG coords)
    theta = math.radians(angle_deg)
    base_dir = np.array([math.cos(theta), math.sin(theta)])

    # Base centre
    base_centre = tip + base_dir * length

    # Perpendicular to base_dir (90° CW in SVG y-down)
    perp = np.array([base_dir[1], -base_dir[0]])

    # Two base corners
    half_w = width / 2.0
    corner_a = base_centre + perp * half_w
    corner_b = base_centre - perp * half_w

    pts = [
        (float(tip[0]), float(tip[1])),
        (float(corner_a[0]), float(corner_a[1])),
        (float(corner_b[0]), float(corner_b[1])),
    ]

    ns_uri = _element_namespace(root)
    tag = f"{{{ns_uri}}}polygon" if ns_uri else "polygon"
    poly = etree.SubElement(root, tag)
    poly.set("id", dart_id)
    poly.set("points", _serialise_polygon_points(pts))
    poly.set("fill", "white")
    poly.set("stroke", "black")
    poly.set("stroke-width", "1")

    new_pattern._id_index[dart_id] = poly
    return new_pattern


def true_seam_length(
    pattern: Pattern,
    seam_a_id: str,
    seam_b_id: str,
) -> Pattern:
    """Adjust seam A's endpoint to match the length of seam B; return a new Pattern.

    The START point of seam A is held fixed.  The END point (last coordinate)
    is moved along the seam direction so the total Euclidean length equals that
    of seam B.

    Both seams must be <path> elements with at least two coordinate pairs.

    Raises ElementNotFound if either seam id is absent.
    Raises GeometryError if a seam cannot be measured (e.g. zero-length start).
    """
    # Validate both ids exist before copying
    if seam_a_id not in pattern._id_index:
        raise ElementNotFound(f"Element '{seam_a_id}' not found in pattern")
    if seam_b_id not in pattern._id_index:
        raise ElementNotFound(f"Element '{seam_b_id}' not found in pattern")

    el_b = pattern._id_index[seam_b_id]
    len_b = _path_length(el_b)

    new_pattern = pattern._deep_copy()
    el_a = new_pattern._id_index[seam_a_id]
    _adjust_path_endpoint_length(el_a, len_b)
    return new_pattern


# ---------------------------------------------------------------------------
# Internal geometry helpers
# ---------------------------------------------------------------------------


def _element_namespace(el: etree._Element) -> str:
    """Return the namespace URI of an element, or empty string if none."""
    tag = el.tag
    if tag.startswith("{"):
        return tag[1 : tag.index("}")]
    return ""


def _element_centroid(el: etree._Element) -> tuple[float, float] | None:
    """Return the approximate centroid (mean of coordinates) of an element, or None.

    This is used only for side-of-slash classification in spread_at_line.
    """
    tag = el.tag
    coords: list[tuple[float, float]] = []

    if tag in _PATH_TAGS:
        d = el.get("d", "")
        if not d:
            return None
        commands = _parse_path_d(d)
        for cmd, nums in commands:
            upper = cmd.upper()
            if upper in ("Z", "H", "V", "A"):
                continue
            i = 0
            while i + 1 < len(nums):
                coords.append((nums[i], nums[i + 1]))
                i += 2

    elif tag in _POLYGON_TAGS:
        pts_str = el.get("points", "")
        if not pts_str:
            return None
        coords = _parse_polygon_points(pts_str)

    elif tag in _LINE_TAGS:
        x1 = float(el.get("x1", 0))
        y1 = float(el.get("y1", 0))
        x2 = float(el.get("x2", 0))
        y2 = float(el.get("y2", 0))
        coords = [(x1, y1), (x2, y2)]

    elif tag in _TEXT_TAGS:
        x = float(el.get("x", 0))
        y = float(el.get("y", 0))
        coords = [(x, y)]

    if not coords:
        return None

    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def _element_bbox(
    el: etree._Element,
) -> tuple[float, float, float, float] | None:
    """Return (min_x, min_y, max_x, max_y) bounding box of an element or <g> subtree.

    Recursively gathers coordinates from all descendant elements.
    Returns None if no coordinates can be extracted.
    """
    tag = el.tag
    coords: list[tuple[float, float]] = []

    if tag in _PATH_TAGS:
        d = el.get("d", "")
        if d:
            # Normalise relative commands to absolute before collecting
            d_norm = _transform_path_coords(d, lambda x, y: (x, y))
            commands = _parse_path_d(d_norm)
            for cmd, nums in commands:
                upper = cmd.upper()
                if upper in ("Z",):
                    continue
                i = 0
                while i + 1 < len(nums):
                    coords.append((nums[i], nums[i + 1]))
                    i += 2

    elif tag in _POLYGON_TAGS:
        pts_str = el.get("points", "")
        if pts_str:
            coords = _parse_polygon_points(pts_str)

    elif tag in _LINE_TAGS:
        x1 = float(el.get("x1", 0))
        y1 = float(el.get("y1", 0))
        x2 = float(el.get("x2", 0))
        y2 = float(el.get("y2", 0))
        coords = [(x1, y1), (x2, y2)]

    elif tag in _TEXT_TAGS:
        x = float(el.get("x", 0))
        y = float(el.get("y", 0))
        coords = [(x, y)]

    elif tag in _G_TAGS:
        # Recurse into all direct children, collecting their bboxes
        for child in el:
            child_bbox = _element_bbox(child)
            if child_bbox is not None:
                min_x, min_y, max_x, max_y = child_bbox
                coords.extend([(min_x, min_y), (max_x, max_y)])

    if not coords:
        return None

    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    return (min(xs), min(ys), max(xs), max(ys))


def _scale_element(
    el: etree._Element,
    sx: float,
    sy: float,
    pivot: tuple[float, float],
) -> None:
    """Scale a single lxml element in-place around a pivot point.

    Applies transform: (pivot_x + (x - pivot_x) * sx, pivot_y + (y - pivot_y) * sy).
    Modifies the element directly — caller must be working on a deep copy.
    All descendant elements in a <g> use the same pivot (not per-child bbox centres).
    """
    px, py = pivot

    def scale_coord(x: float, y: float) -> tuple[float, float]:
        return (px + (x - px) * sx, py + (y - py) * sy)

    tag = el.tag

    if tag in _PATH_TAGS:
        d = el.get("d", "")
        el.set("d", _transform_path_coords(d, scale_coord))

    elif tag in _POLYGON_TAGS:
        pts = _parse_polygon_points(el.get("points", ""))
        scaled = [scale_coord(x, y) for x, y in pts]
        el.set("points", _serialise_polygon_points(scaled))

    elif tag in _LINE_TAGS:
        for attr_x, attr_y in (("x1", "y1"), ("x2", "y2")):
            x = float(el.get(attr_x, 0))
            y = float(el.get(attr_y, 0))
            x2, y2 = scale_coord(x, y)
            el.set(attr_x, _format_coord(x2))
            el.set(attr_y, _format_coord(y2))

    elif tag in _TEXT_TAGS:
        x = float(el.get("x", 0))
        y = float(el.get("y", 0))
        x2, y2 = scale_coord(x, y)
        el.set("x", _format_coord(x2))
        el.set("y", _format_coord(y2))

    elif tag in _G_TAGS:
        # Recurse into all direct children with the SAME pivot (not per-child)
        for child in el:
            _scale_element(child, sx, sy, pivot)


def _path_anchor_points(d: str) -> list[tuple[float, float]]:
    """Return the on-curve anchor points of a path, normalised to absolute first.

    For each command repetition, only the endpoint is included — Bezier control
    points are skipped.  This gives exact arc length for M/L paths and a
    chord-length lower-bound approximation for curved segments (spec-10 handles
    full Bezier arc length).
    """
    d_norm = _transform_path_coords(d, lambda x, y: (x, y))
    commands = _parse_path_d(d_norm)

    # pairs per command repetition / which pair (0-indexed) is the endpoint
    _STRIDE: dict[str, int] = {"M": 1, "L": 1, "C": 3, "S": 2, "Q": 2, "T": 1}
    _EP: dict[str, int] = {"M": 0, "L": 0, "C": 2, "S": 1, "Q": 1, "T": 0}

    anchors: list[tuple[float, float]] = []
    for cmd, nums in commands:
        upper = cmd.upper()
        if upper not in _STRIDE:
            continue  # Z, A (H/V already normalised to L)
        stride = _STRIDE[upper]
        ep = _EP[upper]
        stride_floats = stride * 2
        i = 0
        while i < len(nums):
            ep_i = i + ep * 2
            if ep_i + 1 < len(nums):
                anchors.append((nums[ep_i], nums[ep_i + 1]))
            i += stride_floats

    return anchors


def _path_length(el: etree._Element) -> float:
    """Return the polyline arc length of a path element.

    Arc length is the sum of Euclidean distances between consecutive on-curve
    anchor points.  For Bezier commands only the segment endpoint is used
    (chord-length approximation); full Bezier arc length is deferred to spec-10.

    Raises GeometryError if the path has fewer than 2 anchor points.
    """
    anchors = _path_anchor_points(el.get("d", ""))
    if len(anchors) < 2:
        raise GeometryError("Path has fewer than 2 coordinates; cannot measure length")
    return sum(
        float(np.linalg.norm(np.array(anchors[i + 1]) - np.array(anchors[i])))
        for i in range(len(anchors) - 1)
    )


def _adjust_path_endpoint_length(el: etree._Element, target_length: float) -> None:
    """Move the endpoint of a path in-place so its polyline arc length equals target_length.

    All intermediate anchor points are held fixed.  For extension, the last
    segment is lengthened in its own direction.  For shortening, the path is
    truncated at the correct arc position with the final point interpolated.

    Chord-length approximation is used for Bezier segments (spec-10 will fix).
    """
    d = el.get("d", "")
    # Normalise to absolute/uppercase so index arithmetic is straightforward
    d_norm = _transform_path_coords(d, lambda x, y: (x, y))
    commands = list(_parse_path_d(d_norm))
    anchors = _path_anchor_points(d)

    if len(anchors) < 2:
        raise GeometryError("Path has fewer than 2 coordinates; cannot adjust length")

    # Build cumulative arc lengths
    cumulative = [0.0]
    for i in range(1, len(anchors)):
        seg = float(np.linalg.norm(np.array(anchors[i]) - np.array(anchors[i - 1])))
        cumulative.append(cumulative[-1] + seg)

    total = cumulative[-1]
    if total < 1e-9:
        raise GeometryError("Cannot adjust endpoint of a zero-length path")

    if target_length >= total:
        # Extend: move the last anchor along the last segment's direction
        p0 = np.array(anchors[-2], dtype=float)
        p1 = np.array(anchors[-1], dtype=float)
        seg_vec = p1 - p0
        seg_len = float(np.linalg.norm(seg_vec))
        if seg_len < 1e-9:
            raise GeometryError("Cannot extend: last segment has zero length")
        extra = target_length - cumulative[-2]
        new_end = p0 + (seg_vec / seg_len) * extra
        anchor_idx = len(anchors) - 1  # update the last anchor in the command list
    else:
        # Shorten: find which segment contains the target, interpolate
        new_end = np.array(anchors[0], dtype=float)
        anchor_idx = 1
        for i in range(1, len(anchors)):
            if cumulative[i] >= target_length:
                seg_len = cumulative[i] - cumulative[i - 1]
                t = (target_length - cumulative[i - 1]) / seg_len
                new_end = np.array(anchors[i - 1]) + t * (
                    np.array(anchors[i]) - np.array(anchors[i - 1])
                )
                anchor_idx = i
                break

    # Rewrite commands: find the command whose endpoint is anchor_idx and update it;
    # drop any commands beyond that point.
    _STRIDE: dict[str, int] = {"M": 1, "L": 1, "C": 3, "S": 2, "Q": 2, "T": 1}
    _EP: dict[str, int] = {"M": 0, "L": 0, "C": 2, "S": 1, "Q": 1, "T": 0}

    ai = 0  # current anchor index
    new_commands: list[tuple[str, list[float]]] = []
    done = False

    for cmd, nums in commands:
        if done:
            break
        upper = cmd.upper()
        if upper not in _STRIDE:
            new_commands.append((cmd, list(nums)))
            continue

        stride = _STRIDE[upper]
        ep = _EP[upper]
        stride_floats = stride * 2
        new_nums: list[float] = []
        i = 0

        while i < len(nums) and not done:
            ep_i = i + ep * 2
            if ep_i + 1 >= len(nums):
                break
            if ai == anchor_idx:
                # Replace this endpoint with new_end; keep preceding params in repetition
                new_nums.extend(nums[i:ep_i])
                new_nums.extend([float(new_end[0]), float(new_end[1])])
                done = True
            else:
                new_nums.extend(nums[i : i + stride_floats])
                ai += 1
            i += stride_floats

        if new_nums:
            new_commands.append((upper, new_nums))

    el.set("d", _serialise_path_d(new_commands))
