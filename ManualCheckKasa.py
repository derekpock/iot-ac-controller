import asyncio
import kasa


async def main():
    plug = kasa.SmartPlug("10.0.0.206")
    await plug.update()
    print(plug.emeter_realtime.power)
    print(plug.is_on)


loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
loop.run_until_complete(main())
