"""Direct smoke test of KinematicsTools against live CATIA.

Builds a fresh 2x KIN_LineRef assembly, then exercises the three kinematics
tools through the exact code path the MCP server uses.
"""
import sys, io, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import win32com.client

HELP = r"F:\Openwork\test_output\KIN_LineRef.CATPart"

catia = win32com.client.Dispatch("CATIA.Application")
catia.DisplayFileAlerts = False

# --- close stale unsaved Product docs (dead-mechanism prevention) ---
for i in range(catia.Documents.Count, 0, -1):
    d = catia.Documents.Item(i)
    try:
        if d.Path == "" and d.Name.lower().endswith(".catproduct"):
            print(f"closing stale unsaved: {d.Name}")
            d.Close()
    except Exception:
        pass

# --- fresh assembly with two helper instances ---
asm = catia.Documents.Add("Product")
root = asm.Product
try:
    root.ApplyWorkMode(0)
except Exception:
    pass
root.Products.AddComponentsFromFiles((HELP,), "All")
root.Products.AddComponentsFromFiles((HELP,), "All")
ca, cb = root.Products.Item(1), root.Products.Item(2)
print(f"assembly ready: A={ca.Name!r} B={cb.Name!r}")

from catia_mcp.connection import CATIAConnection
from catia_mcp.tools.kinematics import KinematicsTools

conn = CATIAConnection()
print("connect:", conn.connect())
kin = KinematicsTools(conn)

print("\n=== 1: create revolute joint + angle command ===")
r1 = kin.execute(
    "catia_kin_create_revolute_joint",
    {"component_a": ca.Name, "component_b": cb.Name, "command_angle_deg": 0.0},
)
print(r1)

print("\n=== 2: idempotent repeat ===")
r2 = kin.execute(
    "catia_kin_create_revolute_joint",
    {"component_a": ca.Name, "component_b": cb.Name},
)
print(r2)

print("\n=== 3: mechanism info ===")
print(kin.execute("catia_kin_get_mechanism_info", {}))

print("\n=== 4: drive to 30 deg ===")
print(kin.execute("catia_kin_drive_mechanism", {"angle_deg": 30.0}))

# assertions
import json

d1 = json.loads(r1)
assert d1["success"] is True and d1["already_existed"] is False, "create failed"
assert d1["mechanism"]["nb_joints"] == 1, f"NbJoints={d1['mechanism']['nb_joints']}"
assert d1["joint"]["type"] == "CATKinRevoluteJoint"
assert d1["mechanism"]["nb_dof"] == 1, f"NbDof={d1['mechanism']['nb_dof']}"
assert d1["mechanism"]["nb_commands"] == 1, "angle command missing"
assert d1["command"]["current_value_deg"] == 0.0, f"cmd read-back: {d1['command']}"
d2 = json.loads(r2)
assert d2["already_existed"] is True, "idempotency failed"
d4 = json.loads(kin.execute("catia_kin_drive_mechanism", {"angle_deg": 0.0}))
assert abs(d4["current_value_deg"]) < 1e-6, f"drive read-back failed: {d4}"

catia.DisplayFileAlerts = True
print("\nSMOKE TEST PASSED")
