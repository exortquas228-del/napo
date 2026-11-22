import asyncio
import io
import json
from aiohttp import web
import mss
import pyautogui

# Защита от потери контроля: курсор в верхний левый угол останавливает pyautogui
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


async def get_screen_size(request: web.Request) -> web.Response:
    width, height = pyautogui.size()
    return web.json_response({"width": width, "height": height})


async def get_screenshot(request: web.Request) -> web.Response:
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        sct_img = sct.grab(monitor)
        img = mss.tools.to_png(sct_img.rgb, sct_img.size)

    return web.Response(body=img, content_type="image/png")


async def mouse_move(request: web.Request) -> web.Response:
    try:
        data = await request.json()
        x = int(data.get("x", 0))
        y = int(data.get("y", 0))
        duration = float(data.get("duration", 0.1))
        pyautogui.moveTo(x, y, duration=duration)
        return web.json_response({"status": "ok", "x": x, "y": y})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)


async def mouse_click(request: web.Request) -> web.Response:
    try:
        data = await request.json()
        x = data.get("x")
        y = data.get("y")
        button = data.get("button", "left")
        clicks = int(data.get("clicks", 1))

        if x is not None and y is not None:
            pyautogui.click(x=int(x), y=int(y), button=button, clicks=clicks)
        else:
            pyautogui.click(button=button, clicks=clicks)

        return web.json_response({"status": "ok"})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)


async def mouse_scroll(request: web.Request) -> web.Response:
    try:
        data = await request.json()
        clicks = int(data.get("clicks", 0))
        pyautogui.scroll(clicks)
        return web.json_response({"status": "ok"})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)


async def keyboard_type(request: web.Request) -> web.Response:
    try:
        data = await request.json()
        text = str(data.get("text", ""))
        interval = float(data.get("interval", 0.02))
        pyautogui.write(text, interval=interval)
        return web.json_response({"status": "ok"})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)


async def keyboard_press(request: web.Request) -> web.Response:
    try:
        data = await request.json()
        key = data.get("key")
        keys = data.get("keys")

        if keys and isinstance(keys, list):
            pyautogui.hotkey(*keys)
        elif key:
            pyautogui.press(str(key))
        else:
            return web.json_response({"error": "Требуется параметр key или keys"}, status=400)

        return web.json_response({"status": "ok"})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)


async def index_viewer(request: web.Request) -> web.Response:
    html = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>Desktop Agent Bridge</title>
<style>
body { margin: 0; background: #0A0A0C; color: #fff; font-family: sans-serif; display: flex; flex-direction: column; align-items: center; padding: 20px; }
h1 { font-size: 20px; margin-bottom: 8px; }
p { font-size: 13px; color: #888; margin-bottom: 16px; }
#screen { max-width: 90vw; border: 1px solid rgba(255,255,255,0.15); border-radius: 8px; cursor: crosshair; }
.controls { margin-top: 14px; display: flex; gap: 10px; }
input { background: #16161a; border: 1px solid #333; color: #fff; padding: 8px 12px; border-radius: 6px; }
button { background: #4F46E5; border: none; color: #fff; padding: 8px 16px; border-radius: 6px; cursor: pointer; }
</style>
</head>
<body>
<h1>Desktop Agent Bridge</h1>
<p>Интерфейс удаленного просмотра и управления экраном для ИИ</p>
<img id="screen" src="/screen" alt="Экран">
<div class="controls">
<button onclick="refreshScreen()">Обновить снимок</button>
<input type="text" id="typeInput" placeholder="Текст для ввода">
<button onclick="sendText()">Ввести текст</button>
</div>
<script>
function refreshScreen() {
    document.getElementById('screen').src = '/screen?t=' + Date.now();
}
async function sendText() {
    const val = document.getElementById('typeInput').value;
    if (!val) return;
    await fetch('/keyboard/type', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({text: val})
    });
    document.getElementById('typeInput').value = '';
    setTimeout(refreshScreen, 300);
}
document.getElementById('screen').addEventListener('click', async (e) => {
    const img = e.target;
    const rect = img.getBoundingClientRect();
    const scaleX = img.naturalWidth / rect.width;
    const scaleY = img.naturalHeight / rect.height;
    const realX = Math.round((e.clientX - rect.left) * scaleX);
    const realY = Math.round((e.clientY - rect.top) * scaleY);
    await fetch('/mouse/click', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({x: realX, y: realY, button: 'left'})
    });
    setTimeout(refreshScreen, 300);
});
</script>
</body>
</html>
"""
    return web.Response(text=html, content_type="text/html")


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", index_viewer)
    app.router.add_get("/screen", get_screenshot)
    app.router.add_get("/screen/size", get_screen_size)
    app.router.add_post("/mouse/move", mouse_move)
    app.router.add_post("/mouse/click", mouse_click)
    app.router.add_post("/mouse/scroll", mouse_scroll)
    app.router.add_post("/keyboard/type", keyboard_type)
    app.router.add_post("/keyboard/press", keyboard_press)
    return app


if __name__ == "__main__":
    app = create_app()
    print("Desktop Agent Bridge запущен на http://127.0.0.1:5000")
    print("Эндпоинты API:")
    print("  GET  /screen        - получить снимок экрана (PNG)")
    print("  GET  /screen/size   - получить разрешение экрана")
    print("  POST /mouse/click   - клик мышью (x, y, button, clicks)")
    print("  POST /mouse/move    - перемещение курсора (x, y)")
    print("  POST /keyboard/type - ввод текста (text)")
    print("  POST /keyboard/press - нажатие клавиш (key или keys)")
    web.run_app(app, host="127.0.0.1", port=5000)
