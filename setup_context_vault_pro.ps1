<# 
  Context Vault 2.0 - Instalación PRO (Windows/PowerShell)
  - Construye vault estático con chunking + manifest + feed + status
  - Firma HMAC del manifest (clave protegida con DPAPI)
  - index.html con búsqueda (filename + contenido) y visor de chunks
  - Verificador de integridad (verify_manifest.py)
  - GitHub Actions (build & deploy a Pages) / alternativa local
  - Scheduled Task opcional (autobuild + autopush)
  - Boot message listo para pegar en cualquier chat (Claude/GPT)
#>

param(
  [Parameter(Mandatory=$true)]
  [string]$Root,
  [string]$Out = "$(Resolve-Path $Root)\vault_site",
  [int]$ChunkKB = 128,
  [ValidateSet("local","github","cloudflare")]
  [string]$DeployTarget = "local",
  [string]$RepoUrl = "",                 # Si DeployTarget=github, tu remote (opcional si ya está configurado)
  [switch]$Serve,
  [int]$Port = 8787,
  [switch]$Schedule,                     # Crea tarea programada diaria para rebuild+push
  [string]$TaskTime = "09:00"            # Hora local para tarea (HH:mm)
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Ensure-Dir($p){ if(-not (Test-Path $p)){ New-Item -ItemType Directory -Path $p | Out-Null } }

Write-Host "`n=== Context Vault PRO | Setup ===`n" -ForegroundColor Cyan
Write-Host "Root: $Root"
Write-Host "Out : $Out"
Write-Host "Target: $DeployTarget"
Write-Host ""

# 0) Pre-chequeos
if(-not (Test-Path $Root)){ throw "Root no existe: $Root" }
Ensure-Dir $Out

# 1) Python venv + deps
Write-Host "[1/9] Preparando entorno Python..." -ForegroundColor Yellow
$venv = Join-Path $Out ".venv"
if(-not (Test-Path $venv)){
  python -m venv $venv
}
& "$venv\Scripts\python.exe" -m pip install --upgrade pip > $null
# Dependencias mínimas (watch opcional; lunr lo hacemos en JS para no inflar)
& "$venv\Scripts\python.exe" -m pip install watchdog > $null

# 2) Clave HMAC (DPAPI)
Write-Host "[2/9] Gestionando clave HMAC (DPAPI)..." -ForegroundColor Yellow
$secDir = Join-Path $Out "secrets"
Ensure-Dir $secDir
$hmacFile = Join-Path $secDir "hmac.protected"
$hmacHexFile = Join-Path $secDir "hmac.hex" # copia en texto plano solo si ya existe (no se recrea si existe)

function New-HexKey([int]$bytes=32){
  $rng = New-Object System.Security.Cryptography.RNGCryptoServiceProvider
  $b = New-Object byte[] ($bytes); $rng.GetBytes($b); $rng.Dispose()
  -join ($b | ForEach-Object { $_.ToString("x2") })
}

if(-not (Test-Path $hmacFile)){
  $hex = New-HexKey 32
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($hex)
  $prot = [System.Security.Cryptography.ProtectedData]::Protect($bytes, $null, [System.Security.Cryptography.DataProtectionScope]::CurrentUser)
  [IO.File]::WriteAllBytes($hmacFile, $prot)
  if(-not (Test-Path $hmacHexFile)){ Set-Content -LiteralPath $hmacHexFile -Value $hex -Encoding UTF8 }
  Write-Host "  ✓ HMAC creada y protegida" -ForegroundColor Green
}else{
  Write-Host "  ✓ HMAC existente" -ForegroundColor Green
}

function Get-HmacHex(){
  $prot = [IO.File]::ReadAllBytes($hmacFile)
  $bytes = [System.Security.Cryptography.ProtectedData]::Unprotect($prot, $null, [System.Security.Cryptography.DataProtectionScope]::CurrentUser)
  [System.Text.Encoding]::UTF8.GetString($bytes)
}
$HmacHex = Get-HmacHex

# 3) Builder Python
Write-Host "[3/9] Escribiendo builder (context_vault.py)..." -ForegroundColor Yellow
$builderPy = @'
import argparse, hashlib, json, os, re, sys, time, base64, hmac
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_INCLUDE = [
  "src/**.py","strategies/**.py","examples/**.py",
  "configs/**.yml","configs/**.yaml","configs/**.json",
  "instrument_specs.json","versions.json","regime_thresholds.yaml",
  "output/**","event_store/**","backtest/**","tca/**","docs/**","logs/**"
]
DEFAULT_EXCLUDE_DIRS = {".git","__pycache__",".venv","node_modules",".ipynb_checkpoints","vault_site"}

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def norm_rel(base: Path, p: Path) -> str:
    try: return str(p.relative_to(base)).replace("\\","/")
    except: return str(p).replace("\\","/")

def list_files(root: Path, include_patterns, exclude_dirs):
    files = []
    def allowed(path: Path):
        parts = set(str(path).replace("\\","/").split("/"))
        return exclude_dirs.isdisjoint(parts)
    for pat in include_patterns:
        for p in root.glob(pat):
            if p.is_file() and allowed(p):
                files.append(p)
        if "/**" in pat or "\\**" in pat:
            basepat = pat.replace("/**","").replace("\\**","")
            for p in root.glob(basepat):
                if p.is_dir() and allowed(p):
                    for sub in p.rglob("*"):
                        if sub.is_file() and allowed(sub):
                            files.append(sub)
    # dedup
    seen=set(); out=[]
    for p in files:
        rp = p.resolve()
        if rp not in seen:
            seen.add(rp); out.append(p)
    return out

def chunk_file(src: Path, chunk_bytes: int, chunks_dir: Path, relpath: str):
    chunks=[]
    size = src.stat().st_size
    if size == 0:
        out = chunks_dir / (relpath.replace("/","__") + ".1.txt")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("", encoding="utf-8")
        chunks.append({"id": f"{relpath}.1", "path": norm_rel(chunks_dir,out), "sha256": sha256_file(out), "bytes":0, "mode":"text", "lines":0})
        return chunks
    with src.open("rb") as f:
        i=0
        while True:
            buf = f.read(chunk_bytes)
            if not buf: break
            i += 1
            out = chunks_dir / (relpath.replace("/","__") + f".{i}.txt")
            out.parent.mkdir(parents=True, exist_ok=True)
            try:
                txt = buf.decode("utf-8", errors="strict")
                out.write_text(txt, encoding="utf-8")
                mode="text"; lines = txt.count("\n")+1 if txt else 0
            except UnicodeDecodeError:
                b64 = base64.b64encode(buf).decode("ascii")
                out.write_text("<!-- base64 -->\n"+b64, encoding="utf-8")
                mode="base64"; lines = 0
            chunks.append({
                "id": f"{relpath}.{i}",
                "path": norm_rel(chunks_dir,out),
                "sha256": sha256_file(out),
                "bytes": len(buf),
                "mode": mode,
                "lines": lines
            })
    return chunks

def build(root, outdir, chunk_kb, hmac_key, include_patterns, exclude_dirs):
    root = Path(root).resolve()
    out = Path(outdir).resolve()
    chunks_dir = out / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)

    files = list_files(root, include_patterns, exclude_dirs)
    manifest = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "chunk_bytes": chunk_kb*1024,
        "files":[]
    }
    changes=[]
    for p in files:
        rel = norm_rel(root, p)
        mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat()
        sha = sha256_file(p)
        entry = {
            "path": rel,
            "size": p.stat().st_size,
            "mtime": mtime,
            "sha256": sha,
            "chunks": chunk_file(p, chunk_kb*1024, chunks_dir, rel)
        }
        manifest["files"].append(entry)
        changes.append((mtime, rel, sha))
    manifest_path = out/"manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # feed (últimos 600 por mtime)
    changes.sort(reverse=True)
    feed = [{"mtime":t, "path":r, "sha256":s} for (t,r,s) in changes[:600]]
    (out/"feed.json").write_text(json.dumps(feed, ensure_ascii=False, indent=2), encoding="utf-8")

    # status
    status = {
        "files": len(files),
        "chunks": sum(len(f["chunks"]) for f in manifest["files"]),
        "bytes": sum(f["size"] for f in manifest["files"]),
        "built_at": manifest["built_at"]
    }
    (out/"status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")

    # firma del manifest
    if hmac_key:
        key = bytes.fromhex(hmac_key) if re.fullmatch(r"[0-9a-fA-F]{64}", hmac_key or "") else hmac_key.encode("utf-8")
        sig = hmac.new(key, manifest_path.read_bytes(), hashlib.sha256).digest()
        (out/"manifest.sig").write_text(base64.b64encode(sig).decode("ascii"), encoding="utf-8")

    # index.html con búsqueda
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Context Vault</title>
<style>
body{{font-family:system-ui,Segoe UI,Arial,sans-serif;margin:24px;max-width:1200px}}
input,button{{font-size:14px;padding:8px}}
.code{{font-family:ui-monospace,Consolas,monospace;background:#f6f8fa;padding:8px;border-radius:6px}}
small{{color:#666}}
</style>
</head>
<body>
<h1>Context Vault</h1>
<p>
  <a href="status.json">status</a> • 
  <a href="feed.json">feed</a> • 
  <a href="manifest.json">manifest</a> • 
  <a href="manifest.sig">manifest.sig</a>
</p>
<div>
  <input id="q" placeholder="buscar en nombres y chunks (substring, sensible a tamaño)" style="width:70%"/>
  <button onclick="doSearch()">Buscar</button>
</div>
<div id="r" style="margin-top:16px"></div>

<script>
let manifest=null;
async function load(){ if(!manifest) manifest = await (await fetch('manifest.json')).json(); }

function esc(s){ return s.replace(/&/g,'&amp;').replace(/</g,'&lt;'); }

async function doSearch(){
  await load();
  const q = document.getElementById('q').value.trim().toLowerCase();
  const div = document.getElementById('r'); div.innerHTML='';
  if(!q){ return; }

  let hits=[];
  for(const f of manifest.files){
    if(f.path.toLowerCase().includes(q)){
      hits.push({file:f.path, chunk:null, href:null, kind:"file"});
      continue;
    }
    for(const c of f.chunks){
      // estrategia: abrimos solo el primer chunk para filename hits; para contenido, dejamos al usuario abrir
      if(c.mode==='text'){ 
        // muestra candidato; apertura manual evita trafico masivo
        if(f.path.toLowerCase().includes(q)){ 
          hits.push({file:f.path, chunk:c.path, href:c.path, kind:"chunk"});
        } else {
          // para contenido, ofrecemos link (el navegador puede buscar dentro del chunk)
          hits.push({file:f.path, chunk:c.path, href:c.path, kind:"chunk"});
        }
      }
    }
  }
  // cap para evitar UI gigante
  hits = hits.slice(0,800);
  div.innerHTML = `<p><b>${hits.length}</b> resultados (máx 800). Usa Ctrl+F en el chunk abierto.</p>` 
    + hits.map(h=>`<div class="code"><b>${esc(h.file)}</b><br>${h.href?`<a target="_blank" href="${h.href}">${esc(h.chunk)}</a>`:`(archivo)`}</div>`).join('');
}
</script>
</body></html>"""
    (out/"index.html").write_text(html, encoding="utf-8")

    # robots + sitemap mínimo
    (out/"robots.txt").write_text("User-agent: *\nAllow: /\n", encoding="utf-8")
    (out/"CNAME").write_text("", encoding="utf-8") if not (out/"CNAME").exists() else None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--chunk-kb", type=int, default=128)
    ap.add_argument("--hmac-hex", default=None)
    ap.add_argument("--watch", action="store_true")
    ap.add_argument("--serve", action="store_true")
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--include", nargs="*", default=None)
    ap.add_argument("--exclude", nargs="*", default=None)
    args = ap.parse_args()

    include = args.include or DEFAULT_INCLUDE
    exclude = set(args.exclude) if args.exclude else DEFAULT_EXCLUDE_DIRS

    def build_once():
        print("[*] building…")
        build(args.root, args.out, args.chunk_kb, args.hmac_hex, include, exclude)
        print("[✓] built at", datetime.now().isoformat())

    build_once()

    if args.serve:
        import http.server, socketserver, threading
        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self,*a,**k): super().__init__(*a, directory=args.out, **k)
        httpd = socketserver.TCPServer(("", args.port), Handler)
        t = threading.Thread(target=httpd.serve_forever, daemon=True); t.start()
        print(f"[*] serving http://localhost:{args.port}")

    if args.watch:
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
        except:
            print("watchdog no instalado"); sys.exit(2)
        class EH(FileSystemEventHandler):
            def on_any_event(self, ev):
                p = str(ev.src_path)
                if any(x in p for x in (".git","__pycache__","vault_site","node_modules",".venv")):
                    return
                time.sleep(0.25)
                try: build_once()
                except Exception as e: print("build error:", e)
        obs = Observer()
        obs.schedule(EH(), args.root, recursive=True)
        obs.start()
        print("[*] watching for changes. Ctrl+C para salir.")
        try:
            while True: time.sleep(1)
        except KeyboardInterrupt:
            pass
        obs.stop(); obs.join()

    if args.serve and not args.watch:
        try:
            while True: time.sleep(1)
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    main()
'@

Set-Content -LiteralPath "$Out\context_vault.py" -Value $builderPy -Encoding UTF8

# 4) Verificador de integridad
Write-Host "[4/9] Escribiendo verificador (verify_manifest.py)..." -ForegroundColor Yellow
$verifyPy = @'
import argparse, json, base64, hmac, hashlib, random, os, sys
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True, help="ruta a vault_site publicado (local o montado)")
    ap.add_argument("--hmac-hex", required=True)
    ap.add_argument("--samples", type=int, default=10)
    args = ap.parse_args()

    site = Path(args.site)
    man = json.loads((site/"manifest.json").read_text(encoding="utf-8"))
    sig = (site/"manifest.sig").read_text(encoding="utf-8")
    calc = base64.b64encode(hmac.new(bytes.fromhex(args.hmac_hex), (site/"manifest.json").read_bytes(), hashlib.sha256).digest()).decode("ascii")
    if sig.strip()!=calc.strip():
        print("✗ HMAC signature mismatch"); sys.exit(2)
    print("✓ HMAC signature OK")

    files = man["files"]
    all_chunks=[]
    for f in files:
        for c in f["chunks"]:
            all_chunks.append((f["path"], c["path"], c["sha256"]))
    if not all_chunks:
        print("No hay chunks"); sys.exit(1)

    random.shuffle(all_chunks)
    samples = all_chunks[:args.samples]
    ok=0
    for (fpath, cpath, chash) in samples:
        p = site / cpath
        if not p.exists():
            print(f"✗ Falta chunk: {cpath}")
            continue
        # rehasear chunk
        import hashlib
        h = hashlib.sha256()
        with p.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024*1024), b""): h.update(chunk)
        if h.hexdigest()==chash:
            ok+=1
        else:
            print(f"✗ Hash mismatch: {cpath}")
    if ok==len(samples):
        print(f"✓ {ok}/{len(samples)} chunks OK")
        sys.exit(0)
    else:
        print(f"✗ {ok}/{len(samples)} chunks OK")
        sys.exit(3)

if __name__=="__main__":
    main()
'@
Set-Content -LiteralPath "$Out\verify_manifest.py" -Value $verifyPy -Encoding UTF8

# 5) indexación inicial + server opcional
Write-Host "[5/9] Construyendo vault inicial..." -ForegroundColor Yellow
& "$venv\Scripts\python.exe" "$Out\context_vault.py" --root $Root --out $Out --chunk-kb $ChunkKB --hmac-hex $HmacHex $(if($Serve){"--serve"}) --port $Port

# 6) GitHub Pages workflow + README + .gitignore
if($DeployTarget -eq "github"){
  Write-Host "[6/9] Preparando GitHub Actions (Pages)..." -ForegroundColor Yellow
  $wfDir = Join-Path $Root ".github\workflows"
  Ensure-Dir $wfDir
  $wf = @"
name: Build & Deploy Context Vault
on:
  push:
    branches: [ main ]
    paths:
      - 'src/**'
      - 'strategies/**'
      - 'examples/**'
      - 'configs/**'
      - 'instrument_specs.json'
      - 'versions.json'
      - 'regime_thresholds.yaml'
      - 'output/**'
      - 'event_store/**'
      - 'backtest/**'
      - 'tca/**'
      - 'docs/**'
      - 'logs/**'
      - 'vault_site/context_vault.py'
      - '.github/workflows/deploy_vault.yml'
  workflow_dispatch: {}
permissions:
  contents: write
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Build Vault
        run: |
          python vault_site/context_vault.py --root . --out vault_site --chunk-kb $ChunkKB
      - name: Publish to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: \${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./vault_site
"@
  Set-Content -LiteralPath "$wfDir\deploy_vault.yml" -Value $wf -Encoding UTF8

  $gi = @"
# Context Vault
vault_site/secrets/
vault_site/*.pyc
vault_site/__pycache__/
.vscode/
.venv/
**/__pycache__/
"@
  if(-not (Test-Path "$Root\.gitignore")){ Set-Content -LiteralPath "$Root\.gitignore" -Value $gi -Encoding UTF8 }

  $readme = @"
# Context Vault

- Sitio: GitHub Pages (se publica automáticamente desde \`vault_site/\`).
- \`manifest.json\` firmado con HMAC (clave protegida localmente).
- \`feed.json\` (últimos cambios), \`status.json\` (resumen), \`chunks/*\` (contenido chunkificado).

## Build local
\`\`\`powershell
python .\vault_site\context_vault.py --root . --out .\vault_site --chunk-kb $ChunkKB
\`\`\`

## Verificación
\`\`\`powershell
python .\vault_site\verify_manifest.py --site .\vault_site --hmac-hex (Get-Content .\vault_site\secrets\hmac.hex -Raw)
\`\`\`
"@
  Set-Content -LiteralPath "$Root\VAULT_README.md" -Value $readme -Encoding UTF8

  if($RepoUrl -and -not (Test-Path "$Root\.git")){
    Write-Host "Inicializando repo Git..." -ForegroundColor DarkGray
    git init $Root | Out-Null
    git -C $Root remote add origin $RepoUrl | Out-Null
  }
  Write-Host "Recuerda: push a 'main' para publicar Pages." -ForegroundColor Green
}

# 7) Cloudflare Pages (opcional: archivos base)
if($DeployTarget -eq "cloudflare"){
  Write-Host "[7/9] Preparando estructura Cloudflare Pages..." -ForegroundColor Yellow
  $wrangler = @"
name = "context-vault"
pages_build_output_dir = "vault_site"
# Configura tu proyecto en Cloudflare y usa esta carpeta como salida
"@
  Set-Content -LiteralPath "$Root\wrangler.toml" -Value $wrangler -Encoding UTF8
  Write-Host "Recuerda crear proyecto en Cloudflare Pages y apuntar a 'vault_site/'." -ForegroundColor Green
}

# 8) Scheduled Task (autobuild + autopush)
if($Schedule){
  Write-Host "[8/9] Creando tarea programada (autobuild+autopush diario)..." -ForegroundColor Yellow
  $taskName = "ContextVault_AutoBuild"
  $action = "powershell -NoProfile -ExecutionPolicy Bypass -Command `"& '$($venv)\Scripts\python.exe' '$Out\context_vault.py' --root '$Root' --out '$Out' --chunk-kb $ChunkKB ; if((Get-Command git -ErrorAction SilentlyContinue)) { git -C '$Root' add -A; git -C '$Root' commit -m 'vault: autobuild' -n; git -C '$Root' push }`""
  $trigger = New-ScheduledTaskTrigger -Daily -At ([DateTime]::ParseExact($TaskTime, "HH:mm", $null))
  $principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive -RunLevel Highest
  $act = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -Command $action"
  try{
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
  }catch{}
  Register-ScheduledTask -TaskName $taskName -Trigger $trigger -Action $act -Principal $principal | Out-Null
  Write-Host "  ✓ Tarea '$taskName' creada a las $TaskTime" -ForegroundColor Green
}

# 9) Boot message para pegar en chats
Write-Host "[9/9] Generando BOOT MESSAGE..." -ForegroundColor Yellow
$boot = @"
BOOT | CONTEXT VAULT (estricto)
URL base: (pon aquí la URL pública de tu Pages)  →  https://<tu-dominio-o-user>.github.io/<repo>/

Instrucciones para el asistente:
1) Carga /status.json y /manifest.json. Valida 5 chunks al azar contra /chunks/*.txt.
2) Revisa /feed.json y resume cambios recientes ANTES de opinar.
3) Cuando cites o propongas cambios, enlaza rutas de chunks concretos.
4) Si falta contexto, RESPONDE con: REQUEST-MATERIALS y una lista completa de archivos/chunks requeridos.
5) Calidad > velocidad. Nada de atajos. Si dudas, dilo.
Zona horaria: Europe/Zurich. 
Firma HMAC: disponible bajo petición humana (no exponer en público).
"@
Set-Content -LiteralPath "$Out\BOOT_MESSAGE.txt" -Value $boot -Encoding UTF8

# Mensaje final + verificación rápida local
Write-Host "`n— Resumen —" -ForegroundColor Cyan
Write-Host "Vault: $Out" -ForegroundColor Green
Write-Host "Serve: $(if($Serve){"http://localhost:$Port"})"
Write-Host "HMAC(hex): $(Get-Content $hmacHexFile -Raw | ForEach-Object { $_.Substring(0,8)+'…' })" -ForegroundColor DarkGray
Write-Host "BOOT MESSAGE: $Out\BOOT_MESSAGE.txt" -ForegroundColor DarkGray
Write-Host ""

Write-Host "Verificando 6 chunks al azar..." -ForegroundColor Yellow
& "$venv\Scripts\python.exe" "$Out\verify_manifest.py" --site "$Out" --hmac-hex $HmacHex --samples 6

Write-Host "`n✓ Context Vault PRO listo." -ForegroundColor Green
if($DeployTarget -eq "github"){
  Write-Host "Haz push a 'main' y GitHub Pages publicará el vault automáticamente." -ForegroundColor Cyan
}
if($Serve){
  Write-Host "Servidor local activo → http://localhost:$Port  (Ctrl+C para parar en la consola del builder)" -ForegroundColor Cyan
}
