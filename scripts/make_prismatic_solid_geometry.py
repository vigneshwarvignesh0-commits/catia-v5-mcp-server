"""Create compatible 3D mating geometry for prismatic joint testing.

Builds two solid Part Design bodies:
- Part 1 (Rail):  Rectangular block 100 x 20 x 20 mm extruded along X-axis
- Part 2 (Slider): Rectangular block 30 x 20 x 20 mm extruded along X-axis

Both parts have clean planar faces and linear edges suitable for CATIA DMU
Kinematics prismatic joint constraints.

Usage:
    python scripts/make_prismatic_solid_geometry.py
"""
import os
import win32com.client
import win32com.client.dynamic

catia = win32com.client.GetActiveObject("CATIA.Application")
catia.DisplayFileAlerts = False

OUT_DIR = r"F:\Openwork\test_output"
os.makedirs(OUT_DIR, exist_ok=True)


def close_all_docs():
    for i in range(catia.Documents.Count, 0, -1):
        try:
            catia.Documents.Item(i).Close()
        except Exception:
            pass


def create_rectangular_block(part_name: str, length: float, width: float,
                             height: float) -> str:
    """Create a rectangular block using Part Design (sketch + pad).

    Returns the path to the saved .CATPart file.
    """
    doc = catia.Documents.Add("Part")
    part = doc.Part
    hsf = win32com.client.dynamic.Dispatch(part.HybridShapeFactory._oleobj_)

    # Create Geometrical Set for sketches
    hb = part.HybridBodies.Add()
    hb.Name = "KinGeo"

    # Create sketch on XY plane
    plane_xy = part.OriginElements.PlaneXY
    ref_xy = part.CreateReferenceFromObject(plane_xy)

    # Get the factory for sketches
    # We need to use the Sketcher workbench to create a sketch
    # Actually, let's use the simpler approach: create points and lines in
    # a hybrid body, then create a sketch from them, or use ShapeFactory
    # directly with a sketch

    # For Part Design pad, we need a sketch. Let's create a simple sketch
    # using the Sketcher API through the document
    catia.StartWorkbench("Sketcher")

    # Create a sketch on the XY plane
    try:
        sketch = part.Sketches.Add(ref_xy)
    except Exception:
        # Sketches collection might be on the body
        body = part.Bodies.Item(1)
        sketch = body.Sketches.Add(ref_xy)

    # Open the sketch for editing
    sketch.OpenEdition()

    # Get the sketch factory
    fact2d = sketch.Factory2D

    # Create a rectangle centered at origin
    # Length along X, width along Y
    half_l = length / 2.0
    half_w = width / 2.0

    # Create 4 lines forming a closed rectangle
    fact2d.CreateLine(-half_l, -half_w, half_l, -half_w)  # bottom
    fact2d.CreateLine(half_l, -half_w, half_l, half_w)    # right
    fact2d.CreateLine(half_l, half_w, -half_l, half_w)    # top
    fact2d.CreateLine(-half_l, half_w, -half_l, -half_w)  # bottom

    # Close the sketch
    sketch.CloseEdition()

    # Exit Sketcher workbench
    catia.StartWorkbench("Part Design")

    # Create a pad from the sketch
    body = part.Bodies.Item(1)
    sf = part.ShapeFactory

    # Make the body the InWorkObject
    part.InWorkObject = body
    part.UpdateObject(body)

    pad = sf.AddNewPad(sketch, height)

    # Set pad properties
    pad.Name = "Block"

    part.UpdateObject(pad)

    # Save the part
    out_path = os.path.join(OUT_DIR, f"KIN_Prismatic_{part_name}.CATPart")
    doc.SaveAs(out_path)
    print(f"Created {part_name}: {out_path} ({length} x {width} x {height} mm)")

    return out_path


# ---- Main ----
close_all_docs()

# Part 1: Rail (100 x 20 x 20 mm along X)
rail_path = create_rectangular_block("Rail", 100.0, 20.0, 20.0)

# Part 2: Slider (30 x 20 x 20 mm along X)
slider_path = create_rectangular_block("Slider", 30.0, 20.0, 20.0)

# ---- Add KinGeo/Line.1 to both parts for kinematics tool compatibility ----
# The kinematics tool expects a standalone wireframe Line.1 in a Geometrical
# Set named "KinGeo" in each part. Add this after Part Design is complete.
for part_path, part_name in [(rail_path, "Rail"), (slider_path, "Slider")]:
    doc = catia.Documents.Open(part_path)
    part = doc.Part
    hsf = win32com.client.dynamic.Dispatch(part.HybridShapeFactory._oleobj_)

    # Create Geometrical Set "KinGeo" if it doesn't exist
    try:
        hb = part.HybridBodies.Item("KinGeo")
    except Exception:
        hb = part.HybridBodies.Add()
        hb.Name = "KinGeo"

    # Create Line.1 along X axis at origin on XY plane
    plane_xy = part.OriginElements.PlaneXY
    p1 = hsf.AddNewPointOnPlane(plane_xy, 0.0, 0.0)
    p1.Name = "P1"
    p2 = hsf.AddNewPointOnPlane(plane_xy, 100.0, 0.0)
    p2.Name = "P2"
    hb.AppendHybridShape(p1)
    hb.AppendHybridShape(p2)
    line = hsf.AddNewLinePtPt(p1, p2)
    line.Name = "Line.1"
    hb.AppendHybridShape(line)
    part.UpdateObject(line)

    doc.SaveAs(part_path)
    doc.Close()
    print(f"Added KinGeo/Line.1 to {part_name}")

print("\nBoth parts ready with KinGeo/Line.1 for kinematics testing.")
print(f"  Rail:   {rail_path}")
print(f"  Slider: {slider_path}")
