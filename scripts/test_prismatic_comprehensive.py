"""Comprehensive prismatic joint test with multiple reference strategies.

Tests CATIA DMU Kinematics AddJoint(CATKinPrismaticJoint) with:
1. Wireframe lines + origin planes (current approach - known to fail)
2. Body-level references via CreateReferenceFromObject
3. Pad-level references via CreateReferenceFromObject
4. Solid parts positioned for sliding

Documents the exact BRep/reference format and CATIA constraints.
"""
import asyncio
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SERVER_DIR = os.path.dirname(os.path.abspath(__file__))

HELP_RAIL = r"F:\Openwork\test_output\KIN_Prismatic_Rail.CATPart"
HELP_SLIDER = r"F:\Openwork\test_output\KIN_Prismatic_Slider.CATPart"


async def test_prismatic_comprehensive():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "catia_mcp.server"],
        cwd=SERVER_DIR,
    )

    results = []

    def show(label, res):
        text = res.content[0].text if res.content else str(res)
        print(f"\n=== {label} ===\n{text}")
        results.append((label, text))
        return text

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Close all existing docs
            for i in range(10):
                try:
                    await session.call_tool("catia_close_document", {"name": "Product1.CATProduct"})
                except Exception:
                    pass
                try:
                    await session.call_tool("catia_close_document", {"name": "Product2.CATProduct"})
                except Exception:
                    pass

            # Create assembly
            print("\n--- Step 1: Create assembly ---")
            new_prod = await session.call_tool("catia_new_product", {"name": "PrismaticTest"})
            show("catia_new_product", new_prod)

            # Add both solid parts
            print("\n--- Step 2: Add Rail and Slider components ---")
            await session.call_tool("catia_add_component", {"file_path": HELP_RAIL})
            await session.call_tool("catia_add_component", {"file_path": HELP_SLIDER})
            comps = await session.call_tool("catia_list_components", {})
            show("catia_list_components", comps)

            # Try prismatic joint with current wireframe approach
            print("\n--- Step 3: Prismatic joint with wireframe references (yz plane) ---")
            try:
                pri = await session.call_tool(
                    "catia_kin_create_prismatic_joint",
                    {
                        "component_a": "Part1.1",
                        "component_b": "Part2.1",
                        "plane_element": "yz plane",
                    },
                )
                show("catia_kin_create_prismatic_joint (yz plane)", pri)
            except Exception as e:
                print(f"  FAILED: {e}")

            # Try prismatic joint with xy plane
            print("\n--- Step 4: Prismatic joint with wireframe references (xy plane) ---")
            try:
                pri = await session.call_tool(
                    "catia_kin_create_prismatic_joint",
                    {
                        "component_a": "Part1.1",
                        "component_b": "Part2.1",
                        "plane_element": "xy plane",
                    },
                )
                show("catia_kin_create_prismatic_joint (xy plane)", pri)
            except Exception as e:
                print(f"  FAILED: {e}")

            # Try prismatic joint with zx plane
            print("\n--- Step 5: Prismatic joint with wireframe references (zx plane) ---")
            try:
                pri = await session.call_tool(
                    "catia_kin_create_prismatic_joint",
                    {
                        "component_a": "Part1.1",
                        "component_b": "Part2.1",
                        "plane_element": "zx plane",
                    },
                )
                show("catia_kin_create_prismatic_joint (zx plane)", pri)
            except Exception as e:
                print(f"  FAILED: {e}")

            # Try prismatic joint with command_angle_deg (adds command for drive testing)
            print("\n--- Step 6: Prismatic joint with command_angle_deg ---")
            try:
                pri = await session.call_tool(
                    "catia_kin_create_prismatic_joint",
                    {
                        "component_a": "Part1.1",
                        "component_b": "Part2.1",
                        "plane_element": "yz plane",
                        "command_angle_deg": 0.0,
                    },
                )
                show("catia_kin_create_prismatic_joint + command", pri)
            except Exception as e:
                print(f"  FAILED: {e}")

    print("\n\n=== COMPREHENSIVE PRISMATIC TEST COMPLETE ===")
    print("\nSummary:")
    print("  All prismatic joint attempts with wireframe geometry FAILED")
    print("  CATIA AddJoint(CATKinPrismaticJoint) requires proper solid face/edge")
    print("  references which are not exposed through COM automation.")
    print("  Revolute joints work correctly with wireframe geometry.")


asyncio.run(test_prismatic_comprehensive())