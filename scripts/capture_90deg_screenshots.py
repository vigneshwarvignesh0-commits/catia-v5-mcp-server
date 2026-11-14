"""Create revolute joint with command, drive to 90°, capture screenshots."""
import asyncio
import io
import os
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
ARTIFACT_DIR = os.path.join(SERVER_DIR, "artifacts")
os.makedirs(ARTIFACT_DIR, exist_ok=True)

HELP = r"F:\Openwork\test_output\KIN_LineRef.CATPart"


async def main():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "catia_mcp.server"],
        cwd=SERVER_DIR,
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Close existing docs
            for i in range(5):
                try:
                    await session.call_tool("catia_close_document", {"name": "Product1.CATProduct"})
                except Exception:
                    pass
                try:
                    await session.call_tool("catia_close_document", {"name": "Product2.CATProduct"})
                except Exception:
                    pass

            # Create fresh assembly
            print("\n--- Create fresh assembly ---")
            new_prod = await session.call_tool("catia_new_product", {"name": "MechTest"})
            print(new_prod.content[0].text)

            # Add two components
            print("\n--- Add components ---")
            await session.call_tool("catia_add_component", {"file_path": HELP})
            await session.call_tool("catia_add_component", {"file_path": HELP})

            # Create revolute joint WITH command_angle_deg
            print("\n--- Create revolute joint with command ---")
            create_rev = await session.call_tool(
                "catia_kin_create_revolute_joint",
                {
                    "component_a": "Part1.1",
                    "component_b": "Part1.2",
                    "plane_element": "yz plane",
                    "command_angle_deg": 0.0,
                },
            )
            print(create_rev.content[0].text)

            # Drive to 90°
            print("\n--- Drive to 90 degrees ---")
            drive90 = await session.call_tool(
                "catia_kin_drive_mechanism", {"angle_deg": 90.0}
            )
            print(drive90.content[0].text)

    # Capture screenshots
    await asyncio.sleep(2)
    try:
        from PIL import ImageGrab

        print("\nCapturing screenshots...")
        img1 = ImageGrab.grab()
        path1 = os.path.join(ARTIFACT_DIR, "spec_tree_90deg.png")
        img1.save(path1)
        print(f"Screenshot 1: {path1} ({img1.size})")

        time.sleep(1)
        img2 = ImageGrab.grab()
        path2 = os.path.join(ARTIFACT_DIR, "assembly_90deg.png")
        img2.save(path2)
        print(f"Screenshot 2: {path2} ({img2.size})")

        print("\nScreenshots saved to:", ARTIFACT_DIR)
    except ImportError:
        print("PIL not available. Try: pip install pillow")
    except Exception as e:
        print(f"Screenshot capture failed: {e}")


asyncio.run(main())
