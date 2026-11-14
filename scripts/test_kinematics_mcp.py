"""End-to-end MCP test: spawn catia_mcp.server over stdio and call the
kinematics tools against live CATIA."""
import sys, io, os, json, asyncio

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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

            tools = await session.list_tools()
            names = sorted(t.name for t in tools.tools)
            print(f"{len(names)} tools registered:")
            for n in names:
                print("  ", n)
            kin = [n for n in names if n.startswith("catia_kin_")]
            assert len(kin) == 3, f"expected 3 kinematics tools, got {kin}"

            def show(label, res):
                text = res.content[0].text if res.content else str(res)
                print(f"\n--- {label} ---\n{text}")
                return text

            comps_text = show("MCP: list components",
                              await session.call_tool("catia_list_components", {}))
            comps = json.loads(comps_text)
            assert isinstance(comps, list) and len(comps) >= 2, "need 2 components"
            a, b = comps[0]["name"], comps[1]["name"]
            print(f"\nusing A={a!r} B={b!r}")

            info = show("MCP: mechanism info",
                        await session.call_tool("catia_kin_get_mechanism_info", {}))
            d = json.loads(info)
            mech = d["mechanisms"][0]
            assert mech["nb_joints"] == 1, f"NbJoints={mech['nb_joints']}"
            assert mech["joints"][0]["type"] == "CATKinRevoluteJoint"
            assert mech["nb_dof"] == 1

            created = show("MCP: create revolute (idempotent path)",
                           await session.call_tool(
                               "catia_kin_create_revolute_joint",
                               {"component_a": a, "component_b": b}))
            dc = json.loads(created)
            assert dc["already_existed"] is True, "expected idempotent detection"

            driven = show("MCP: drive to 60 deg",
                          await session.call_tool(
                              "catia_kin_drive_mechanism", {"angle_deg": 60.0}))
            dd = json.loads(driven)
            assert dd["success"] is True
            assert abs(dd["current_value_deg"] - 60.0) < 1e-6, f"read-back {dd}"
            back = await session.call_tool("catia_kin_drive_mechanism",
                                           {"angle_deg": 0.0})
            db = json.loads(back.content[0].text)
            assert abs(db["current_value_deg"]) < 1e-6

    print("\nMCP END-TO-END TEST PASSED")


asyncio.run(main())
