"""Part Design tools for CATIA V5.

3D feature creation: Pad, Pocket, Fillet, Chamfer, Shaft, Groove, Hole,
RectPattern, CircPattern, Mirror, Rib, Slot, Shell, Thickness, Draft.
"""

from __future__ import annotations

import json
from typing import Any

from catia_mcp.connection import CATIAConnection


class PartDesignTools:
    """Tools for 3D Part Design features in CATIA V5."""

    def __init__(self, connection: CATIAConnection) -> None:
        self.conn = connection

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "catia_pad",
                "description": (
                    "Create a Pad (extrusion) from the last sketch. "
                    "Extrudes a 2D profile into a 3D solid along the normal to the sketch plane."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "height": {
                            "type": "number",
                            "description": "Extrusion height/depth in mm",
                        },
                        "direction": {
                            "type": "string",
                            "description": "Extrusion direction: 'normal' (default), 'reverse', 'both'",
                            "enum": ["normal", "reverse", "both"],
                            "default": "normal",
                        },
                        "symmetric": {
                            "type": "boolean",
                            "description": "If true, extrude equally on both sides (total = height)",
                            "default": False,
                        },
                        "sketch_name": {
                            "type": "string",
                            "description": "Name of sketch to use. If not specified, uses the last created sketch.",
                        },
                    },
                    "required": ["height"],
                },
            },
            {
                "name": "catia_pocket",
                "description": (
                    "Create a Pocket (cut extrusion) from the last sketch. "
                    "Removes material by extruding a 2D profile inward."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "depth": {
                            "type": "number",
                            "description": "Cut depth in mm",
                        },
                        "direction": {
                            "type": "string",
                            "description": "Cut direction: 'normal' (default), 'reverse'",
                            "enum": ["normal", "reverse"],
                            "default": "normal",
                        },
                        "sketch_name": {
                            "type": "string",
                            "description": "Name of sketch to use. If not specified, uses the last sketch.",
                        },
                    },
                    "required": ["depth"],
                },
            },
            {
                "name": "catia_shaft",
                "description": (
                    "Create a Shaft (revolution) from the last sketch. "
                    "Revolves a 2D profile around an axis to create a solid of revolution. "
                    "The sketch must contain a line to use as the revolution axis."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "angle": {
                            "type": "number",
                            "description": "Revolution angle in degrees (default: 360 for full revolution)",
                            "default": 360,
                        },
                        "sketch_name": {
                            "type": "string",
                            "description": "Name of sketch to use.",
                        },
                    },
                },
            },
            {
                "name": "catia_groove",
                "description": (
                    "Create a Groove (revolution cut). "
                    "Removes material by revolving a 2D profile around an axis."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "angle": {
                            "type": "number",
                            "description": "Revolution angle in degrees (default: 360)",
                            "default": 360,
                        },
                        "sketch_name": {
                            "type": "string",
                            "description": "Name of sketch to use.",
                        },
                    },
                },
            },
            {
                "name": "catia_fillet",
                "description": (
                    "Add a fillet (rounded edge) to one or more edges of the current solid. "
                    "Specify the radius and the edge names or feature to fillet."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "radius": {
                            "type": "number",
                            "description": "Fillet radius in mm",
                        },
                        "edge_name": {
                            "type": "string",
                            "description": (
                                "Name of the edge to fillet (e.g., 'Edge.1'). "
                                "Use catia_list_edges to find edge names."
                            ),
                        },
                    },
                    "required": ["radius"],
                },
            },
            {
                "name": "catia_chamfer",
                "description": "Add a chamfer (beveled edge) to an edge of the current solid.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "length": {
                            "type": "number",
                            "description": "Chamfer length in mm",
                        },
                        "angle": {
                            "type": "number",
                            "description": "Chamfer angle in degrees (default: 45)",
                            "default": 45,
                        },
                        "edge_name": {
                            "type": "string",
                            "description": "Name of the edge to chamfer",
                        },
                    },
                    "required": ["length"],
                },
            },
            {
                "name": "catia_hole",
                "description": (
                    "Create a Hole feature at a point in the active sketch. "
                    "Supports simple, tapered, counterbored, and countersunk holes."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "diameter": {
                            "type": "number",
                            "description": "Hole diameter in mm",
                        },
                        "depth": {
                            "type": "number",
                            "description": "Hole depth in mm",
                        },
                        "type": {
                            "type": "string",
                            "description": "Hole type: 'simple', 'counterbored', 'countersunk', 'tapered'",
                            "enum": ["simple", "counterbored", "countersunk", "tapered"],
                            "default": "simple",
                        },
                        "threaded": {
                            "type": "boolean",
                            "description": "Whether to add threading (default: false)",
                            "default": False,
                        },
                        "sketch_name": {
                            "type": "string",
                            "description": "Sketch containing the hole center point",
                        },
                    },
                    "required": ["diameter", "depth"],
                },
            },
            {
                "name": "catia_rect_pattern",
                "description": (
                    "Create a Rectangular Pattern of the last feature. "
                    "Duplicates a feature in a grid along two directions."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "dir1_count": {
                            "type": "integer",
                            "description": "Number of instances in first direction",
                        },
                        "dir1_spacing": {
                            "type": "number",
                            "description": "Spacing in first direction (mm)",
                        },
                        "dir2_count": {
                            "type": "integer",
                            "description": "Number of instances in second direction (default: 1)",
                            "default": 1,
                        },
                        "dir2_spacing": {
                            "type": "number",
                            "description": "Spacing in second direction (mm)",
                            "default": 0,
                        },
                        "feature_name": {
                            "type": "string",
                            "description": "Name of the feature to pattern. Defaults to last feature.",
                        },
                    },
                    "required": ["dir1_count", "dir1_spacing"],
                },
            },
            {
                "name": "catia_circ_pattern",
                "description": (
                    "Create a Circular Pattern of the last feature. "
                    "Duplicates a feature around a central axis."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "count": {
                            "type": "integer",
                            "description": "Number of instances around the circle",
                        },
                        "angular_spacing": {
                            "type": "number",
                            "description": "Angular spacing in degrees (default: equal spacing = 360/count)",
                        },
                        "feature_name": {
                            "type": "string",
                            "description": "Feature to pattern. Defaults to last feature.",
                        },
                    },
                    "required": ["count"],
                },
            },
            {
                "name": "catia_mirror",
                "description": (
                    "Mirror a feature or body about a plane. "
                    "Creates a symmetric copy of the geometry."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "plane": {
                            "type": "string",
                            "description": "Mirror plane: 'xy', 'yz', or 'zx'",
                            "enum": ["xy", "yz", "zx"],
                        },
                        "feature_name": {
                            "type": "string",
                            "description": "Feature to mirror. Defaults to last feature.",
                        },
                    },
                    "required": ["plane"],
                },
            },
            {
                "name": "catia_shell",
                "description": (
                    "Create a Shell feature: hollows out a solid leaving walls of specified thickness. "
                    "Optionally remove faces to create openings."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "thickness": {
                            "type": "number",
                            "description": "Wall thickness in mm",
                        },
                        "faces_to_remove": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "BRepNames of faces to remove (create openings). At least one is required. Use catia_list_faces to see available faces.",
                        },
                    },
                    "required": ["thickness", "faces_to_remove"],
                },
            },
            {
                "name": "catia_draft",
                "description": (
                    "Add a Draft Angle to faces for mold-release purposes. "
                    "Tapers faces by a given angle relative to a pulling direction. "
                    "The face to draft and the neutral face are supplied independently "
                    "as BRepName identifiers (e.g. 'Pad.1;3'). Use catia_list_faces to "
                    "discover the available face identifiers."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "angle": {
                            "type": "number",
                            "description": "Draft angle in degrees",
                        },
                        "face_name": {
                            "type": "string",
                            "description": (
                                "BRepName of the face to draft (e.g. 'Pad.1;3'). "
                                "Use catia_list_faces to see available faces."
                            ),
                        },
                        "neutral_face": {
                            "type": "string",
                            "description": (
                                "BRepName of the neutral face (e.g. 'Pad.1;2'). "
                                "This is the fixed reference face for the draft and is "
                                "also used as the Parting element. Use catia_list_faces "
                                "to see available faces."
                            ),
                        },
                        "pulling_direction": {
                            "type": "string",
                            "description": (
                                "Pulling direction plane: 'xy', 'yz', 'zx'. "
                                "The draft is pulled along the normal to this plane "
                                "(xy -> +Z, yz -> +X, zx -> +Y)."
                            ),
                            "enum": ["xy", "yz", "zx"],
                            "default": "xy",
                        },
                        "parting_face": {
                            "type": "string",
                            "description": (
                                "Optional BRepName of the parting element. Defaults to "
                                "neutral_face if omitted. Override when the neutral face "
                                "is parallel to the pulling direction (e.g. lifter draft)."
                            ),
                        },
                    },
                    "required": ["angle", "face_name", "neutral_face"],
                },
            },
            {
                "name": "catia_thickness",
                "description": (
                    "Add or remove thickness from a face of a solid. "
                    "Offsets the selected face inward or outward. Use "
                    "catia_list_faces to discover available BRepName identifiers. "
                    "Negative values remove material inward; positive add outward."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "offset": {
                            "type": "number",
                            "description": "Thickness offset in mm (positive = outward, negative = inward)",
                        },
                        "face_name": {
                            "type": "string",
                            "description": (
                                "BRepName of the face to offset (e.g. 'Pad.1;3'). "
                                "Use catia_list_faces to see available faces."
                            ),
                        },
                    },
                    "required": ["offset", "face_name"],
                },
            },
            {
                "name": "catia_split_solid",
                "description": (
                    "Split the active solid body with a plane or surface, removing "
                    "the material on one side of the splitting element. The splitting "
                    "element can be a named plane/surface in a geometrical set "
                    "(e.g. 'Plane.1', 'SplitSurface') or an origin plane "
                    "('xy', 'yz', 'zx'). The 'side' parameter selects which side of "
                    "the splitting element is removed: 'positive' removes material in "
                    "the direction of the element's normal vector, 'negative' removes "
                    "the opposite side. The splitting element must fully intersect "
                    "the solid."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "splitting_element": {
                            "type": "string",
                            "description": (
                                "Name of the splitting element: a plane or surface in "
                                "a geometrical set (e.g. 'Plane.1'), or an origin plane "
                                "('xy', 'yz', 'zx'). Use catia_gsd_list_elements to see "
                                "available element names."
                            ),
                        },
                        "side": {
                            "type": "string",
                            "description": (
                                "Which side of the splitting element is removed: "
                                "'positive' (default) removes material in the direction "
                                "of the element's normal vector, 'negative' removes the "
                                "opposite side."
                            ),
                            "enum": ["positive", "negative"],
                            "default": "positive",
                        },
                    },
                    "required": ["splitting_element"],
                },
            },
            {
                "name": "catia_list_features",
                "description": "List all features in the active Part Body with their names and types.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "catia_list_edges",
                "description": "List all edges of the active solid body with their names for use with fillet/chamfer.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "catia_list_faces",
                "description": (
                    "List all faces of the active solid body with their BRepName identifiers "
                    "and orientation labels for use with catia_draft (face to draft and neutral face)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "catia_boolean_add",
                "description": (
                    "Boolean Add (Union): merge a reference body into the target body. "
                    "The reference body's volume is added to the target body. "
                    "Requires two separate Part Design bodies. The target body becomes the "
                    "InWorkObject and the reference body is merged into it."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "body_name": {
                            "type": "string",
                            "description": "Name of the reference body to add into the target body (e.g. 'Body.2').",
                        },
                        "target_body": {
                            "type": "string",
                            "description": "Name of the target body to modify. Defaults to the current InWorkObject / active body.",
                        },
                    },
                    "required": ["body_name"],
                },
            },
            {
                "name": "catia_boolean_remove",
                "description": (
                    "Boolean Remove (Cut): subtract the reference body's volume from the target body. "
                    "Requires two separate Part Design bodies. The target body becomes the "
                    "InWorkObject and the reference body is cut out of it."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "body_name": {
                            "type": "string",
                            "description": "Name of the reference body to remove from the target body (e.g. 'Body.2').",
                        },
                        "target_body": {
                            "type": "string",
                            "description": "Name of the target body to modify. Defaults to the current InWorkObject / active body.",
                        },
                    },
                    "required": ["body_name"],
                },
            },
            {
                "name": "catia_boolean_intersect",
                "description": (
                    "Boolean Intersect: keep only the volume common to the target body and the "
                    "reference body. Requires two separate Part Design bodies. The target body "
                    "becomes the InWorkObject and is reduced to the intersection with the reference body."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "body_name": {
                            "type": "string",
                            "description": "Name of the reference body to intersect with the target body (e.g. 'Body.2').",
                        },
                        "target_body": {
                            "type": "string",
                            "description": "Name of the target body to modify. Defaults to the current InWorkObject / active body.",
                        },
                    },
                    "required": ["body_name"],
                },
            },
            {
                "name": "catia_boolean_assemble",
                "description": (
                    "Boolean Assemble: assemble the reference body into the target body as a "
                    "separate, non-merged component. Unlike Add, Assemble keeps the reference "
                    "body as a distinct sub-body within the target. Requires two separate Part "
                    "Design bodies. The target body becomes the InWorkObject."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "body_name": {
                            "type": "string",
                            "description": "Name of the reference body to assemble into the target body (e.g. 'Body.2').",
                        },
                        "target_body": {
                            "type": "string",
                            "description": "Name of the target body to modify. Defaults to the current InWorkObject / active body.",
                        },
                    },
                    "required": ["body_name"],
                },
            },
            {
                "name": "catia_boolean_union_trim",
                "description": (
                    "Boolean Union Trim: union the reference body with the target body and trim "
                    "the result, removing the overlapping volume between them. Requires two "
                    "separate Part Design bodies. The target body becomes the InWorkObject."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "body_name": {
                            "type": "string",
                            "description": "Name of the reference body to union-trim with the target body (e.g. 'Body.2').",
                        },
                        "target_body": {
                            "type": "string",
                            "description": "Name of the target body to modify. Defaults to the current InWorkObject / active body.",
                        },
                    },
                    "required": ["body_name"],
                },
            },
            {
                "name": "catia_create_body",
                "description": (
                    "Create a new Part Design Body (e.g. DOG_HOUSE_1, DG_1.1, DG_1.2, "
                    "PLASTIC_BODY). The new body becomes the active InWorkObject, so "
                    "subsequent sketches and Part Design features are created inside it. "
                    "This is a solid Part Design Body (not a Geometrical Set) and can be "
                    "used in Boolean operations."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name for the new body (e.g. 'DOG_HOUSE_1'). If omitted, CATIA assigns a default name.",
                        },
                    },
                },
            },
            {
                "name": "catia_set_active_body",
                "description": (
                    "Set the active InWorkObject to an existing Part Design Body by name. "
                    "Use this to switch between the host PartBody and construction bodies "
                    "(DOG_HOUSE_1, DG_1.1, ...) before creating features. Verifies the "
                    "body exists and reports the new active body."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "body_name": {
                            "type": "string",
                            "description": "Name of the Part Design Body to make active (e.g. 'PartBody', 'DOG_HOUSE_1').",
                        },
                    },
                    "required": ["body_name"],
                },
            },
            {
                "name": "catia_list_bodies",
                "description": (
                    "List all Part Design Bodies in the active part with their names, "
                    "feature counts, and which one is the current active InWorkObject. "
                    "Use this to verify the correct body is active before creating "
                    "Part Design features."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
        ]

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> str:
        match tool_name:
            case "catia_pad":
                return self._pad(arguments)
            case "catia_pocket":
                return self._pocket(arguments)
            case "catia_shaft":
                return self._shaft(arguments)
            case "catia_groove":
                return self._groove(arguments)
            case "catia_fillet":
                return self._fillet(arguments)
            case "catia_chamfer":
                return self._chamfer(arguments)
            case "catia_hole":
                return self._hole(arguments)
            case "catia_rect_pattern":
                return self._rect_pattern(arguments)
            case "catia_circ_pattern":
                return self._circ_pattern(arguments)
            case "catia_mirror":
                return self._mirror(arguments)
            case "catia_shell":
                return self._shell(arguments)
            case "catia_draft":
                return self._draft(arguments)
            case "catia_thickness":
                return self._thickness(arguments)
            case "catia_split_solid":
                return self._split_solid(arguments)
            case "catia_list_features":
                return self._list_features()
            case "catia_list_edges":
                return self._list_edges()
            case "catia_list_faces":
                return self._list_faces()
            case "catia_boolean_add":
                return self._boolean_add(arguments)
            case "catia_boolean_remove":
                return self._boolean_remove(arguments)
            case "catia_boolean_intersect":
                return self._boolean_intersect(arguments)
            case "catia_boolean_assemble":
                return self._boolean_assemble(arguments)
            case "catia_boolean_union_trim":
                return self._boolean_union_trim(arguments)
            case "catia_create_body":
                return self._create_body(arguments)
            case "catia_set_active_body":
                return self._set_active_body(arguments)
            case "catia_list_bodies":
                return self._list_bodies()
            case _:
                raise ValueError(f"Unknown part design tool: {tool_name}")

    def _get_last_sketch(self, sketch_name: str | None = None) -> Any:
        """Get a sketch by name or the last sketch in the body."""
        part = self.conn.get_active_part()
        body = self.conn.get_active_part_body()
        sketches = body.Sketches

        if sketch_name:
            return sketches.Item(sketch_name)

        # Get the last sketch
        if sketches.Count == 0:
            raise RuntimeError("No sketches found in the active body. Create a sketch first.")
        return sketches.Item(sketches.Count)

    def _get_last_shape(self, feature_name: str | None = None) -> Any:
        """Get a shape/feature by name or the last one in the body."""
        body = self.conn.get_active_part_body()
        shapes = body.Shapes

        if feature_name:
            return shapes.Item(feature_name)

        if shapes.Count == 0:
            raise RuntimeError("No features found in the active body.")
        return shapes.Item(shapes.Count)

    def _pad(self, args: dict[str, Any]) -> str:
        self.conn.ensure_connected()
        part = self.conn.get_active_part()
        body = self.conn.get_active_part_body()
        sf = part.ShapeFactory
        # ShapeFactory targets the part's InWorkObject; ensure it is the active body.
        # A geometrical set as InWorkObject (e.g. after GSD operations) causes E_FAIL.
        part.InWorkObject = self.conn.get_active_part_body()

        sketch = self._get_last_sketch(args.get("sketch_name"))
        height = args["height"]
        direction = args.get("direction", "normal")
        symmetric = args.get("symmetric", False)

        pad = sf.AddNewPad(sketch, height)

        if symmetric:
            pad.IsSymmetric = True
        elif direction == "reverse":
            pad.DirectionOrientation = 1  # catReverse
        elif direction == "both":
            pad.IsSymmetric = True

        part.UpdateObject(pad)
        self.conn.refresh_display()
        return f"Pad created: {height} mm ({direction}). Feature: '{pad.Name}'"

    def _pocket(self, args: dict[str, Any]) -> str:
        self.conn.ensure_connected()
        part = self.conn.get_active_part()
        body = self.conn.get_active_part_body()
        sf = part.ShapeFactory
        # ShapeFactory targets the part's InWorkObject; ensure it is the active body.
        # A geometrical set as InWorkObject (e.g. after GSD operations) causes E_FAIL.
        part.InWorkObject = self.conn.get_active_part_body()

        sketch = self._get_last_sketch(args.get("sketch_name"))
        depth = args["depth"]

        pocket = sf.AddNewPocket(sketch, depth)

        if args.get("direction") == "reverse":
            pocket.DirectionOrientation = 1

        part.UpdateObject(pocket)
        self.conn.refresh_display()
        return f"Pocket created: {depth} mm deep. Feature: '{pocket.Name}'"

    def _shaft(self, args: dict[str, Any]) -> str:
        self.conn.ensure_connected()
        part = self.conn.get_active_part()
        body = self.conn.get_active_part_body()
        sf = part.ShapeFactory
        # ShapeFactory targets the part's InWorkObject; ensure it is the active body.
        # A geometrical set as InWorkObject (e.g. after GSD operations) causes E_FAIL.
        part.InWorkObject = self.conn.get_active_part_body()

        sketch = self._get_last_sketch(args.get("sketch_name"))
        angle = args.get("angle", 360)

        shaft = sf.AddNewShaft(sketch)
        shaft.FirstAngle = angle

        part.UpdateObject(shaft)
        self.conn.refresh_display()
        return f"Shaft (revolution) created: {angle}°. Feature: '{shaft.Name}'"

    def _groove(self, args: dict[str, Any]) -> str:
        self.conn.ensure_connected()
        part = self.conn.get_active_part()
        body = self.conn.get_active_part_body()
        sf = part.ShapeFactory
        # ShapeFactory targets the part's InWorkObject; ensure it is the active body.
        # A geometrical set as InWorkObject (e.g. after GSD operations) causes E_FAIL.
        part.InWorkObject = self.conn.get_active_part_body()

        sketch = self._get_last_sketch(args.get("sketch_name"))
        angle = args.get("angle", 360)

        groove = sf.AddNewGroove(sketch)
        groove.FirstAngle = angle

        part.UpdateObject(groove)
        self.conn.refresh_display()
        return f"Groove (revolution cut) created: {angle}°. Feature: '{groove.Name}'"

    def _fillet(self, args: dict[str, Any]) -> str:
        """Create a Fillet on edges.

        NOTE: This requires a 'References' collection to pass edge selections to the
        CATIA API. The 'References' collection type is NOT accessible through COM
        late-binding (pywin32 or VBScript). This is a fundamental CATIA V5 COM API
        limitation when the type library is not registered for automation.

        Workaround: Use CATIA's GUI (Insert > Dressed Up > Edge Fillet) manually.
        """
        raise NotImplementedError(
            "catia_fillet is not supported through COM automation. "
            "The CATIA API requires a 'References' collection (part.References) to pass "
            "edge selections to AddNewSolidEdgeFilletWithConstantRadius, but this collection "
            "is not accessible through COM late-binding. "
            "Use CATIA's GUI: Insert > Dressed Up > Edge Fillet."
        )

    def _chamfer(self, args: dict[str, Any]) -> str:
        """Create a Chamfer on edges.

        NOTE: Same limitation as _fillet - requires References collection.
        """
        raise NotImplementedError(
            "catia_chamfer is not supported through COM automation. "
            "The CATIA API requires a 'References' collection to pass edge selections "
            "to AddNewChamfer, but this collection is not accessible through COM late-binding. "
            "Use CATIA's GUI: Insert > Dressed Up > Chamfer."
        )

    def _hole(self, args: dict[str, Any]) -> str:
        self.conn.ensure_connected()
        part = self.conn.get_active_part()
        body = self.conn.get_active_part_body()
        sf = part.ShapeFactory
        # ShapeFactory targets the part's InWorkObject; ensure it is the active body.
        # A geometrical set as InWorkObject (e.g. after GSD operations) causes E_FAIL.
        part.InWorkObject = self.conn.get_active_part_body()

        sketch = self._get_last_sketch(args.get("sketch_name"))
        diameter = args["diameter"]
        depth = args["depth"]

        hole = sf.AddNewHole(sketch, depth)
        hole.Diameter = diameter
        hole.BottomType = 0  # catFlatBottom

        if args.get("threaded", False):
            hole.ThreadingMode = 1  # catThreaded

        part.UpdateObject(hole)
        self.conn.refresh_display()
        return f"Hole created: D{diameter} mm, depth {depth} mm. Feature: '{hole.Name}'"

    def _rect_pattern(self, args: dict[str, Any]) -> str:
        self.conn.ensure_connected()
        part = self.conn.get_active_part()
        body = self.conn.get_active_part_body()
        sf = part.ShapeFactory
        # ShapeFactory targets the part's InWorkObject; ensure it is the active body.
        # A geometrical set as InWorkObject (e.g. after GSD operations) causes E_FAIL.
        part.InWorkObject = self.conn.get_active_part_body()

        feature = self._get_last_shape(args.get("feature_name"))
        d1_count = args["dir1_count"]
        d1_spacing = args["dir1_spacing"]
        d2_count = args.get("dir2_count", 1)
        d2_spacing = args.get("dir2_spacing", 0)

        pattern = sf.AddNewRectPattern(
            feature,
            d1_count, d2_count,
            d1_spacing, d2_spacing,
            1, 1,  # direction specification
            True,   # keep specification
        )

        part.UpdateObject(pattern)
        self.conn.refresh_display()
        return (
            f"Rectangular pattern created: {d1_count}x{d2_count}, "
            f"spacing {d1_spacing}x{d2_spacing} mm. Feature: '{pattern.Name}'"
        )

    def _circ_pattern(self, args: dict[str, Any]) -> str:
        self.conn.ensure_connected()
        part = self.conn.get_active_part()
        body = self.conn.get_active_part_body()
        sf = part.ShapeFactory
        # ShapeFactory targets the part's InWorkObject; ensure it is the active body.
        # A geometrical set as InWorkObject (e.g. after GSD operations) causes E_FAIL.
        part.InWorkObject = self.conn.get_active_part_body()

        feature = self._get_last_shape(args.get("feature_name"))
        count = args["count"]
        angular_spacing = args.get("angular_spacing", 360.0 / count)

        pattern = sf.AddNewCircPattern(
            feature,
            count,
            1,              # rows
            angular_spacing,
            0,              # row spacing
            1, 1,           # direction specification
            True,           # keep specification
        )

        part.UpdateObject(pattern)
        self.conn.refresh_display()
        return (
            f"Circular pattern created: {count} instances, "
            f"{angular_spacing}° spacing. Feature: '{pattern.Name}'"
        )

    def _mirror(self, args: dict[str, Any]) -> str:
        self.conn.ensure_connected()
        part = self.conn.get_active_part()
        body = self.conn.get_active_part_body()
        sf = part.ShapeFactory
        # ShapeFactory targets the part's InWorkObject; ensure it is the active body.
        # A geometrical set as InWorkObject (e.g. after GSD operations) causes E_FAIL.
        part.InWorkObject = self.conn.get_active_part_body()

        plane_key = args["plane"].lower()
        planes = self.conn.get_origin_elements()
        if plane_key not in planes:
            raise ValueError(f"Unknown plane '{plane_key}'. Use 'xy', 'yz', or 'zx'.")

        mirror_plane = planes[plane_key]
        ref = part.CreateReferenceFromObject(mirror_plane)

        feature = self._get_last_shape(args.get("feature_name"))
        mirror = sf.AddNewMirror(ref)

        part.UpdateObject(mirror)
        self.conn.refresh_display()
        return f"Mirror created about {plane_key.upper()} plane. Feature: '{mirror.Name}'"

    def _draft(self, args: dict[str, Any]) -> str:
        """Create a Draft angle on faces.

        Draft is supported through the available CATIA COM interface. The required
        neutral Reference must also be supplied as the Parting argument unless
        parting_face is provided. Passing None as Parting causes UpdateObject failure.

        Optional parting_face BRepName overrides the Parting element (defaults to
        neutral_face). Use this when the neutral face is parallel to the pulling
        direction (e.g. lifter draft with +Y pulling and TOP neutral).

        Verified signature (via ShapeFactory):
            sf.AddNewDraft(face_ref, neutral_ref, 0, parting_ref,
                           dir_x, dir_y, dir_z, 0, angle, 0)
        where:
            face_ref     = face to draft (Reference)
            neutral_ref  = neutral element (Reference)
            0            = mode (catStandardDraftMode)
            parting_ref  = parting element (defaults to neutral_ref)
            dir_x/y/z    = pulling direction vector
            0            = direction/mode parameter
            angle        = draft angle (degrees)
            0            = multiselection mode

        Both face references are resolved independently via
        part.CreateReferenceFromBRepName(bn, body). The neutral face is never
        inferred from the draft face.
        """
        self.conn.ensure_connected()
        part = self.conn.get_active_part()
        body = self.conn.get_active_part_body()
        sf = part.ShapeFactory
        # ShapeFactory targets the part's InWorkObject; ensure it is the active body.
        # A geometrical set as InWorkObject (e.g. after GSD operations) causes E_FAIL.
        part.InWorkObject = self.conn.get_active_part_body()

        face_name = args.get("face_name")
        neutral_face = args.get("neutral_face")
        parting_face = args.get("parting_face")  # optional; defaults to neutral_face
        angle = args["angle"]
        pulling_direction = args.get("pulling_direction", "xy")

        if not face_name:
            raise ValueError(
                "face_name is required: the BRepName of the face to draft "
                "(e.g. 'Pad.1;3'). Use catia_list_faces to see available faces."
            )
        if not neutral_face:
            raise ValueError(
                "neutral_face is required: the BRepName of the neutral face "
                "(e.g. 'Pad.1;2'). Use catia_list_faces to see available faces."
            )

        # Resolve references independently (never infer neutral from draft face).
        face_ref = part.CreateReferenceFromBRepName(face_name, body)
        neutral_ref = part.CreateReferenceFromBRepName(neutral_face, body)
        # Parting element: try None first (CATIA default), fall back to
        # neutral_ref if None causes UpdateObject failure.
        parting_ref = None

        # Map pulling direction plane to a direction vector (normal to the plane).
        dir_map = {
            "xy": (0.0, 0.0, 1.0),  # normal to xy plane -> +Z
            "yz": (1.0, 0.0, 0.0),  # normal to yz plane -> +X
            "zx": (0.0, 1.0, 0.0),  # normal to zx plane -> +Y
        }
        if pulling_direction not in dir_map:
            raise ValueError(
                f"Unknown pulling_direction '{pulling_direction}'. Use 'xy', 'yz', or 'zx'."
            )
        dx, dy, dz = dir_map[pulling_direction]

        # Test signature: Parting=None, Limiting=None (both default).
        draft = sf.AddNewDraft(
            face_ref, neutral_ref, 0, parting_ref, dx, dy, dz, 0, angle, 0
        )
        part.UpdateObject(draft)
        self.conn.refresh_display()
        return (
            f"Draft created: {angle} deg on face '{face_name}' with neutral "
            f"'{neutral_face}', pulling {pulling_direction}. Feature: '{draft.Name}'"
        )

    def _shell(self, args: dict[str, Any]) -> str:
        """Create a Shell (hollow) feature.

        Uses ShapeFactory.AddNewShell(face_ref, thickness, orientation) which is
        accessible through COM. The face(s) to remove create openings in the shell.
        """
        self.conn.ensure_connected()
        part = self.conn.get_active_part()
        body = self.conn.get_active_part_body()
        sf = part.ShapeFactory
        # ShapeFactory targets the part's InWorkObject; ensure it is the active body.
        # A geometrical set as InWorkObject (e.g. after GSD operations) causes E_FAIL.
        part.InWorkObject = self.conn.get_active_part_body()

        thickness = args["thickness"]
        faces_to_remove = args.get("faces_to_remove") or []

        if not faces_to_remove:
            raise ValueError(
                "faces_to_remove is required: at least one face must be removed to "
                "create an opening. Use catia_list_faces to see available faces."
            )

        # Create a reference for the first face to remove.
        face_name = faces_to_remove[0]
        face_ref = part.CreateReferenceFromBRepName(face_name, body)

        shell = sf.AddNewShell(face_ref, thickness, 0)
        part.UpdateObject(shell)
        self.conn.refresh_display()
        return (
            f"Shell created: {thickness} mm wall on feature '{shell.Name}' "
            f"with opening on face '{face_name}'."
        )

    def _thickness(self, args: dict[str, Any]) -> str:
        """Add or remove thickness from a face of a solid.

        Uses ShapeFactory.AddNewThickness(face_ref, offset) where face_ref is
        a Reference created from a BRepName identifier.

        NOTE: this CATIA version's AddNewThickness takes exactly 2 positional
        args (Reference + offset), not 3 (Reference + inside + outside).
        Positive offset adds material outward; negative removes inward.
        """
        self.conn.ensure_connected()
        part = self.conn.get_active_part()
        body = self.conn.get_active_part_body()
        sf = part.ShapeFactory
        # ShapeFactory targets the part's InWorkObject; ensure it is the active body.
        # A geometrical set as InWorkObject (e.g. after GSD operations) causes E_FAIL.
        part.InWorkObject = self.conn.get_active_part_body()

        offset = args["offset"]
        face_name = args["face_name"]

        if not face_name:
            raise ValueError(
                "face_name is required: the BRepName of the face to offset "
                "(e.g. 'Pad.1;3'). Use catia_list_faces to see available faces."
            )

        # Create a proper Reference from the BRepName — passing a raw shape
        # object causes AddNewThickness to misinterpret arguments.
        face_ref = part.CreateReferenceFromBRepName(face_name, body)

        # CRITICAL: this CATIA version's AddNewThickness takes exactly 2
        # positional args (Reference + offset), NOT 3 (Reference + inside +
        # outside).  The 3-arg signature causes:
        #   TypeError: AddNewThickness() takes from 1 to 3 positional
        #   arguments but 4 were given
        thickness = sf.AddNewThickness(face_ref, offset)

        part.UpdateObject(thickness)
        self.conn.refresh_display()
        return (
            f"Thickness added: {offset} mm offset on face '{face_name}'. "
            f"Feature: '{thickness.Name}'"
        )

    def _split_solid(self, args: dict[str, Any]) -> str:
        """Split the active solid body with a plane or surface.

        Uses ShapeFactory.AddNewSplit(splitting_ref, side) where side is the
        CatSplitSide enum (1 = catPositiveSide, 2 = catNegativeSide).

        CRITICAL: the ShapeFactory targets the part's InWorkObject. If the
        InWorkObject is a geometrical set (e.g. after creating GSD elements),
        AddNewSplit fails with E_FAIL. The InWorkObject must be set to the
        MainBody before calling AddNewSplit.
        """
        self.conn.ensure_connected()
        part = self.conn.get_active_part()
        sf = part.ShapeFactory

        element_name = args["splitting_element"]
        side = args.get("side", "positive")

        # Resolve the splitting element (origin plane alias or hybrid shape)
        element = self._find_splitting_element(part, element_name)
        ref = part.CreateReferenceFromObject(element)

        # Map side to CatSplitSide enum (verified: 1 removes material in the
        # direction of the splitting element's normal vector)
        side_map = {"positive": 1, "negative": 2}
        side_value = side_map[side]

        # CRITICAL: set InWorkObject to the active body — the ShapeFactory targets
        # the InWorkObject, and a geometrical set cannot be split (E_FAIL).
        part.InWorkObject = self.conn.get_active_part_body()

        split = sf.AddNewSplit(ref, side_value)
        part.UpdateObject(split)
        self.conn.refresh_display()
        return (
            f"Split created: solid split by '{element_name}', "
            f"removed {side} side. Feature: '{split.Name}'"
        )

    def _find_splitting_element(self, part: Any, name: str) -> Any:
        """Find a splitting element by name: origin plane alias or hybrid shape.

        Search order: origin planes (xy/yz/zx aliases), then hybrid shapes in
        all geometrical sets (nested included).
        """
        key = name.lower()
        plane_map = {"xy": "PlaneXY", "yz": "PlaneYZ", "zx": "PlaneZX"}
        if key in plane_map:
            return getattr(part.OriginElements, plane_map[key])

        def iter_geosets(hbs):
            for i in range(1, hbs.Count + 1):
                hb = hbs.Item(i)
                yield hb
                try:
                    yield from iter_geosets(hb.HybridBodies)
                except Exception:
                    pass

        for hb in iter_geosets(part.HybridBodies):
            try:
                return hb.HybridShapes.Item(name)
            except Exception:
                pass

        raise RuntimeError(
            f"Splitting element '{name}' not found. Use a plane/surface name from "
            "catia_gsd_list_elements, or an origin plane ('xy', 'yz', 'zx')."
        )

    def _resolve_boolean_bodies(self, args: dict[str, Any]) -> tuple[Any, Any]:
        """Resolve the target body and reference body for a Boolean op.

        Returns (target_body, reference_body). The reference body is resolved by name
        from args['body_name']. The target body defaults to the main PartBody, or can
        be specified via args['target_body'].

        NOTE: the target must be a Body, never the InWorkObject getter, which returns
        the last feature (e.g. a Pad) rather than the body.
        """
        part = self.conn.get_active_part()
        bodies = part.Bodies

        body_name = args["body_name"]
        target_name = args.get("target_body")

        # Resolve reference body by name
        reference_body = None
        for i in range(1, bodies.Count + 1):
            b = bodies.Item(i)
            if b.Name == body_name:
                reference_body = b
                break
        if reference_body is None:
            raise RuntimeError(
                f"Reference body '{body_name}' not found. Available bodies: "
                + ", ".join(bodies.Item(i).Name for i in range(1, bodies.Count + 1))
            )

        # Resolve target body
        if target_name:
            target_body = None
            for i in range(1, bodies.Count + 1):
                b = bodies.Item(i)
                if b.Name == target_name:
                    target_body = b
                    break
            if target_body is None:
                raise RuntimeError(f"Target body '{target_name}' not found.")
        else:
            # Default to the main body (the primary PartBody). NOTE: we must NOT
            # use part.InWorkObject here, because its getter returns the last
            # feature (e.g. a Pad), not the body. The Boolean target must be a Body.
            target_body = part.MainBody

        if target_body.Name == reference_body.Name:
            raise RuntimeError(
                "Target body and reference body must be different. "
                "A Boolean operation requires two separate bodies."
            )

        return target_body, reference_body

    def _boolean_op(self, args: dict[str, Any], method_name: str, op_label: str) -> str:
        """Generic Boolean operation executor.

        Sets the target body as InWorkObject, then calls the ShapeFactory Boolean
        method (AddNewAdd / AddNewRemove / AddNewIntersect / AddNewAssemble /
        AddNewTrim) with the reference body, then updates.
        """
        self.conn.ensure_connected()
        part = self.conn.get_active_part()
        sf = part.ShapeFactory

        target_body, reference_body = self._resolve_boolean_bodies(args)

        # Set the target body as InWorkObject (required for Boolean ops)
        part.InWorkObject = target_body

        # Call the Boolean method
        method = getattr(sf, method_name)
        feature = method(reference_body)

        part.UpdateObject(feature)
        self.conn.refresh_display()
        return (
            f"Boolean {op_label} created: '{feature.Name}' "
            f"({reference_body.Name} {op_label.lower()} into {target_body.Name})."
        )

    def _boolean_add(self, args: dict[str, Any]) -> str:
        return self._boolean_op(args, "AddNewAdd", "Add")

    def _boolean_remove(self, args: dict[str, Any]) -> str:
        return self._boolean_op(args, "AddNewRemove", "Remove")

    def _boolean_intersect(self, args: dict[str, Any]) -> str:
        return self._boolean_op(args, "AddNewIntersect", "Intersect")

    def _boolean_assemble(self, args: dict[str, Any]) -> str:
        return self._boolean_op(args, "AddNewAssemble", "Assemble")

    def _boolean_union_trim(self, args: dict[str, Any]) -> str:
        return self._boolean_op(args, "AddNewTrim", "Union Trim")

    def _create_body(self, args: dict[str, Any]) -> str:
        """Create a new Part Design Body and make it the active InWorkObject."""
        self.conn.ensure_connected()
        part = self.conn.get_active_part()

        new_body = part.Bodies.Add()
        if args.get("name"):
            new_body.Name = args["name"]

        # Make the new body the active InWorkObject so subsequent sketches and
        # Part Design features land inside it.
        part.InWorkObject = new_body
        part.UpdateObject(new_body)
        self.conn.refresh_display()

        return (
            f"Part Design Body created: '{new_body.Name}'. "
            f"Active InWorkObject set to '{new_body.Name}'."
        )

    def _set_active_body(self, args: dict[str, Any]) -> str:
        """Set the active InWorkObject to an existing Part Design Body by name."""
        self.conn.ensure_connected()
        part = self.conn.get_active_part()
        body_name = args["body_name"]

        bodies = part.Bodies
        target = None
        for i in range(1, bodies.Count + 1):
            b = bodies.Item(i)
            if b.Name == body_name:
                target = b
                break
        if target is None:
            available = ", ".join(
                bodies.Item(i).Name for i in range(1, bodies.Count + 1)
            )
            raise RuntimeError(
                f"Body '{body_name}' not found. Available Part Design bodies: {available}"
            )

        part.InWorkObject = target
        self.conn.refresh_display()
        return f"Active InWorkObject set to Part Design Body '{target.Name}'."

    def _list_bodies(self) -> str:
        """List all Part Design Bodies with feature counts and the active one."""
        self.conn.ensure_connected()
        part = self.conn.get_active_part()
        bodies = part.Bodies

        # The InWorkObject getter returns the last feature (e.g. a Pad) or the
        # body itself when one was explicitly set. Identify the active body by
        # checking whether the InWorkObject IS a body or belongs to one.
        active_feature = None
        try:
            active_feature = part.InWorkObject
        except Exception:
            pass

        result = []
        for i in range(1, bodies.Count + 1):
            b = bodies.Item(i)
            shapes = b.Shapes
            count = shapes.Count
            is_active = False
            if active_feature is not None:
                try:
                    if hasattr(active_feature, "Shapes") and active_feature.Name == b.Name:
                        is_active = True
                    else:
                        for j in range(1, count + 1):
                            if shapes.Item(j).Name == active_feature.Name:
                                is_active = True
                                break
                except Exception:
                    pass
            result.append({
                "index": i,
                "name": b.Name,
                "feature_count": count,
                "active": is_active,
            })

        return json.dumps(result, indent=2)

    def _list_features(self) -> str:
        self.conn.ensure_connected()
        body = self.conn.get_active_part_body()
        shapes = body.Shapes

        features = []
        for i in range(1, shapes.Count + 1):
            shape = shapes.Item(i)
            features.append({
                "index": i,
                "name": shape.Name,
                "type": shape.Type if hasattr(shape, "Type") else "unknown",
            })

        if not features:
            return "No features in the active body"
        return json.dumps(features, indent=2)

    def _list_edges(self) -> str:
        self.conn.ensure_connected()
        part = self.conn.get_active_part()
        body = self.conn.get_active_part_body()

        # Get edges from the last shape
        last_shape = self._get_last_shape()
        edges = []
        try:
            # Access boundary representation
            sel = self.conn.hso
            sel.Clear()
            sel.Add(last_shape)
            sel.Search("Topology.Edge,sel")

            for i in range(1, sel.Count + 1):
                edges.append({
                    "index": i,
                    "name": sel.Item(i).Value.Name if hasattr(sel.Item(i).Value, "Name") else f"Edge.{i}",
                })
            sel.Clear()
        except Exception as e:
            return f"Could not enumerate edges: {e}. Use CATIA selection to identify edge names."

        if not edges:
            return "No edges found on the last feature"
        return json.dumps(edges, indent=2)

    def _list_faces(self) -> str:
        """List all faces of the active solid body with BRepName identifiers and
        orientation labels for use with catia_draft."""
        self.conn.ensure_connected()
        part = self.conn.get_active_part()
        body = self.conn.get_active_part_body()

        last_shape = self._get_last_shape()
        faces = []
        try:
            sel = self.conn.hso
            sel.Clear()
            sel.Add(last_shape)
            sel.Search("Topology.Face,sel")

            for i in range(1, sel.Count + 1):
                item = sel.Item(i)
                # Get the face's full reference name. Prefer item.Value.Name (a proper
                # Reference name when the gen_py cache is healthy); fall back to
                # item.Reference.Name which is always a Reference object.
                try:
                    name = item.Value.Name
                except Exception:
                    try:
                        name = item.Reference.Name
                    except Exception:
                        name = ""
                # Extract the BRepName that CreateReferenceFromBRepName accepts.
                # The working format is the content between 'Selection_RSur:(' and
                # ');<Feature>_ResultOUT', e.g. 'Face:(Brp:(Pad.1;2);None:();Cf12:()'.
                brep = name
                start = name.find("Selection_RSur:(")
                marker = ");" + last_shape.Name + "_ResultOUT"
                end = name.find(marker)
                if start >= 0 and end >= 0:
                    start += len("Selection_RSur:(")
                    brep = name[start:end]
                # Orientation label via point-on-plane local frame normal
                label = self._face_orientation_label(part, body, brep)
                faces.append({
                    "index": i,
                    "brep_name": brep,
                    "orientation": label,
                })
            sel.Clear()
        except Exception as e:
            return f"Could not enumerate faces: {e}. Use CATIA selection to identify face names."

        if not faces:
            return "No faces found on the last feature"
        return json.dumps(faces, indent=2)

    def _face_orientation_label(self, part: Any, body: Any, brep: str) -> str:
        """Classify a face by its outward normal using the point-on-plane local frame.

        Returns a label like TOP/BOTTOM/LEFT/RIGHT/FRONT/REAR or 'unknown'.
        """
        try:
            ref = part.CreateReferenceFromBRepName(brep, body)
            # Create a point on the plane at the face origin to read its local frame.
            hsf = part.HybridShapeFactory
            pt = hsf.AddNewPointOnPlane(ref, 0.5, 0.5)
            # The point's plane local frame: FirstDirection (property) and
            # GetSecondDirection() (method). Normal = First x Second.
            fd = pt.FirstDirection
            sd = pt.GetSecondDirection()

            def _val(v):
                try:
                    return v.Value
                except Exception:
                    return v

            fx, fy, fz = _val(fd.GetX()), _val(fd.GetY()), _val(fd.GetZ())
            # GetSecondDirection() returns a tuple (x, y, z) directly in this
            # environment, not a Direction object. Handle both.
            if isinstance(sd, (tuple, list)):
                sx, sy, sz = sd[0], sd[1], sd[2]
            else:
                sx, sy, sz = _val(sd.GetX()), _val(sd.GetY()), _val(sd.GetZ())
            # Cross product
            nx = fy * sz - fz * sy
            ny = fz * sx - fx * sz
            nz = fx * sy - fy * sx
            # Normalize
            mag = (nx * nx + ny * ny + nz * nz) ** 0.5
            if mag < 1e-9:
                return "unknown"
            nx, ny, nz = nx / mag, ny / mag, nz / mag
            # Map dominant axis
            ax = max(abs(nx), abs(ny), abs(nz))
            if abs(nx) == ax:
                return "RIGHT" if nx > 0 else "LEFT"
            if abs(ny) == ax:
                return "REAR" if ny > 0 else "FRONT"
            return "TOP" if nz > 0 else "BOTTOM"
        except Exception:
            return "unknown"
