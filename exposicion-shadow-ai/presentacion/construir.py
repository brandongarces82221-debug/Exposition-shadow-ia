"""Genera diapositivas.html (un solo archivo) a partir de fuente/.

Uso: python3 construir.py
Controles: ← → (o clic) para avanzar, N muestra las notas del expositor, F pantalla completa.
"""
import html
import json
from pathlib import Path

base = Path(__file__).parent
deck = json.loads((base / "fuente/deck.json").read_text())
css = (base / "fuente/deck.css").read_text()
slides = "\n".join((base / f"fuente/slides/{i}.html").read_text() for i in deck["order"])
fuentes = sorted({f["href"] for f in deck["faces"].values() if "href" in f})

pagina = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(deck["title"])}</title>
{"".join(f'<link rel="stylesheet" href="{h}">' for h in fuentes)}
<style>
* {{ box-sizing: border-box; margin: 0; }}
html, body {{ height: 100%; background: #05070A; overflow: hidden; }}
#escena {{ position: absolute; width: 1920px; height: 1080px; left: 50%; top: 50%; transform-origin: center; }}
#escena > section {{ position: absolute; inset: 0; width: 1920px; height: 1080px; display: none; }}
#escena > section.activa {{ display: flex; }}
section aside {{ display: none; }}
x-shape {{ display: block; flex: none; }}
x-shape[kind="arrow-right"] {{ clip-path: polygon(0 35%, 60% 35%, 60% 0, 100% 50%, 60% 100%, 60% 65%, 0 65%); }}
table {{ border-collapse: collapse; }}
th, td {{ text-align: left; padding: 20px 24px; border-bottom: 2px solid rgba(128,128,128,.35); vertical-align: top; }}
th {{ font-weight: 700; }}
#notas {{ position: fixed; left: 0; right: 0; bottom: 0; max-height: 38vh; overflow: auto; background: #111722ee; color: #F2EFE8;
  font: 18px/1.5 'IBM Plex Sans', Arial, sans-serif; padding: 16px 24px; display: none; border-top: 2px solid #FF8A4C; }}
#notas.ver {{ display: block; }}
#num {{ position: fixed; right: 16px; bottom: 12px; color: #B4BCC9; font: 14px 'JetBrains Mono', monospace; opacity: .7; }}
{css}
</style>
</head>
<body>
<div id="escena">
{slides}
</div>
<div id="notas"></div>
<div id="num"></div>
<script>
const s = [...document.querySelectorAll('#escena > section')];
const escena = document.getElementById('escena');
let i = Math.max(0, Math.min(s.length - 1, (parseInt(location.hash.replace('#slide-', '')) || 1) - 1));
function ajustar() {{
  const k = Math.min(innerWidth / 1920, innerHeight / 1080);
  escena.style.transform = `translate(-50%, -50%) scale(${{k}})`;
}}
function ir(n) {{
  i = Math.max(0, Math.min(s.length - 1, n));
  s.forEach((x, j) => x.classList.toggle('activa', j === i));
  const nota = s[i].querySelector('aside');
  document.getElementById('notas').textContent = nota ? nota.textContent : '(Sin notas)';
  document.getElementById('num').textContent = `${{i + 1}} / ${{s.length}} · N: notas · F: pantalla completa`;
  history.replaceState(null, '', '#slide-' + (i + 1));
}}
addEventListener('resize', ajustar);
addEventListener('keydown', e => {{
  if (['ArrowRight', 'PageDown', ' ', 'Enter'].includes(e.key)) ir(i + 1);
  else if (['ArrowLeft', 'PageUp', 'Backspace'].includes(e.key)) ir(i - 1);
  else if (e.key === 'Home') ir(0);
  else if (e.key === 'End') ir(s.length - 1);
  else if (e.key.toLowerCase() === 'n') document.getElementById('notas').classList.toggle('ver');
  else if (e.key.toLowerCase() === 'f') document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen();
}});
escena.addEventListener('click', e => ir(e.clientX > innerWidth / 2 ? i + 1 : i - 1));
ajustar(); ir(i);
</script>
</body>
</html>
"""
(base / "diapositivas.html").write_text(pagina)
print("diapositivas.html generado con", len(deck["order"]), "diapositivas")
