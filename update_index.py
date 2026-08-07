#!/usr/bin/env python3
"""Gera os índices delta (manifest.json) dos modpacks para o Launcher MGZ.

O launcher usa esses índices para baixar SOMENTE os arquivos que mudaram:
substituir um mod, rodar o script e dar push = todos os jogadores atualizam
na próxima vez que clicarem em Jogar, sem baixar o modpack inteiro de novo.

Modo multi-pack (recomendado — um repo com vários modpacks):
    python update_index.py --repo mglucas0123/MGZCraft-Modpack

    Cada pasta de topo do repo (ex.: OreSpawn-Resurgence/) é um modpack.
    Gera <pasta>/manifest.json para cada um, com base_url inferido:
    https://raw.githubusercontent.com/<repo>/<branch>/<pasta>/

Modo single-pack (um repo por modpack):
    python update_index.py --dir pack \
        --base-url https://raw.githubusercontent.com/mglucas0123/OreSpawn-Resurgence-Modpack/main/pack

Opções:
    --repo user/repo  Repo GitHub (modo multi-pack; ignora --dir/--base-url/--out)
    --branch NAME     Branch usada no base_url (padrão: main)
    --repo-root PATH  Raiz do repo (padrão: pasta onde o script está)
    --dir PATH        Pasta de UM modpack (modo single-pack)
    --base-url URL    URL raw de onde o launcher baixa os arquivos
    --out PATH        Arquivo de saída (padrão: manifest.json)

Formato de saída (por modpack):
{
  "revision":     "<sha1 canônico do mapa de arquivos>",
  "generated_at": "2026-08-06T12:00:00Z",
  "base_url":     "https://raw.githubusercontent.com/.../OreSpawn-Resurgence",
  "tracked":      ["config", "mods", ...],   <- escopo de deleção segura no launcher
  "files": {
    "mods/ModA.jar": {"sha1": "...", "size": 1234},
    ...
  },
  "bin": {                                     <- opcional; quando pack.json tem {"bin": "1.7.10"}
    "url": "https://raw.githubusercontent.com/.../bin/1.7.10.zip",
    "sha1": "...",
    "size": 1234
  }
}

Camada base centralizada e ZIPADA: cada pack declara no pack.json qual versão
de bin/ usa (ex.: {"bin": "1.7.10"}); o binário base (minecraft.jar, json de
versão, natives) vive em bin/<versao>.zip, gerado pelo script a partir da
pasta local bin/src/<versao>/ (gitignored). O launcher baixa o ZIP e extrai
em .minecraft/bin/ — uma única entrada no índice, e modpacks de versões
diferentes podem usar bins diferentes. O modpack.jar (Forge) vai na pasta
mods/ do pack — não no bin.

Regra de ouro: NÃO inclua saves/, logs/, etc. no índice — arquivos fora do
índice nunca são apagados nem tocados pelo launcher. Evite nomes de pasta com
espaço ou caracteres especiais (viram parte da URL).
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import sys
from pathlib import Path

DEFAULT_BASE_URL = (
    "https://raw.githubusercontent.com/mglucas0123/"
    "OreSpawn-Resurgence-Modpack/main/pack"
)


def sha1_file(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_files(pack_dir: Path, out_path: Path | None) -> dict[str, dict]:
    """Mapa caminho-relativo (posix) -> {sha1, size}.

    Ignora o próprio arquivo de saída, o metadado `pack.json` e diretórios
    ocultos (.git, etc.).
    """
    files: dict[str, dict] = {}
    pack_dir = pack_dir.resolve()
    out_resolved = out_path.resolve() if out_path else None
    root = pack_dir
    for dirpath, dirnames, filenames in os.walk(pack_dir):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        for name in sorted(filenames):
            full = Path(dirpath) / name
            if out_resolved is not None and full.resolve() == out_resolved:
                continue
            if name == "pack.json" and full.parent.resolve() == root:
                continue
            rel = full.relative_to(root).as_posix()
            files[rel] = {
                "sha1": sha1_file(full),
                "size": full.stat().st_size,
            }
    return files


def load_pack_meta(pack_dir: Path) -> dict:
    """Lê pack.json do modpack (ex.: {"bin": "1.7.10"})."""
    meta_path = pack_dir / "pack.json"
    if not meta_path.is_file():
        return {}
    try:
        data = json.loads(meta_path.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def collect_bin_files(bin_dir: Path) -> dict[str, dict]:
    """Mapa dos arquivos da camada base (pasta de origem do bin)."""
    files: dict[str, dict] = {}
    bin_dir = bin_dir.resolve()
    if not bin_dir.is_dir():
        return files
    for dirpath, dirnames, filenames in os.walk(bin_dir):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        for name in sorted(filenames):
            full = Path(dirpath) / name
            rel = full.relative_to(bin_dir).as_posix()
            files[rel] = {
                "sha1": sha1_file(full),
                "size": full.stat().st_size,
            }
    return files


def build_bin_zip(src_dir: Path, out_zip: Path) -> tuple[str, int]:
    """Empacota a pasta de origem num ZIP determinístico.

    Timestamp fixo (1980-01-01) e ordem ordenada para que conteúdo idêntico
    gere bytes idênticos (sem diff no git nem re-download no launcher).
    """
    import zipfile

    files = collect_bin_files(src_dir)
    if not files:
        raise ValueError(f"pasta de origem do bin vazia/ausente: {src_dir}")
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    tmp_zip = out_zip.with_suffix(out_zip.suffix + ".tmp")
    with zipfile.ZipFile(tmp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in sorted(files):
            info = zipfile.ZipInfo(f"{rel}", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100644 << 16) | 0x8000
            info.create_system = 3
            zf.writestr(info, (src_dir / rel).read_bytes())
    tmp_zip.replace(out_zip)
    digest = hashlib.sha1()
    with out_zip.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest(), out_zip.stat().st_size


def compute_revision(files: dict[str, dict]) -> str:
    """Revisão = sha1 do JSON canônico do mapa de arquivos.

    Qualquer alteração (adicionar/remover/mudar conteúdo) muda a revisão;
    conteúdo idêntico = mesma revisão = launcher não re-sincroniza.
    """
    canonical = json.dumps(files, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha1(canonical.encode("utf-8")).hexdigest()


def build_index(pack_dir: Path, base_url: str, out_path: Path | None,
                bin_root: Path | None = None) -> dict:
    files = collect_files(pack_dir, out_path)
    if not files:
        raise ValueError(f"nenhum arquivo encontrado em {pack_dir}")
    tracked = sorted({rel.split("/", 1)[0] for rel in files})
    index = {
        "revision": compute_revision(files),
        "generated_at": datetime.datetime.now(datetime.timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "base_url": base_url.rstrip("/"),
        "tracked": tracked,
        "files": files,
    }
    meta = load_pack_meta(pack_dir)
    bin_name = str(meta.get("bin", "")).strip()
    if bin_name:
        bin_root_dir = (bin_root or pack_dir.parent / "bin")
        src_dir = bin_root_dir / "src" / bin_name
        out_zip = bin_root_dir / f"{bin_name}.zip"
        try:
            sha1, size = build_bin_zip(src_dir, out_zip)
        except ValueError as exc:
            raise ValueError(f"pack.json pede bin '{bin_name}': {exc}") from None
        bin_url = f"{base_url.rstrip('/').rsplit('/', 1)[0]}/bin/{bin_name}.zip"
        index["bin"] = {
            "url": bin_url,
            "sha1": sha1,
            "size": size,
        }
    return index


def write_index(index: dict, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(index, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera os índices delta dos modpacks MGZ")
    parser.add_argument("--repo", help="user/repo do GitHub (modo multi-pack)")
    parser.add_argument("--branch", default="main", help="Branch usada no base_url (padrão: main)")
    parser.add_argument("--repo-root", default=None,
                        help="Pasta raiz do repo (padrão: pasta onde o script está)")
    parser.add_argument("--dir", default=".", help="Pasta de UM modpack (padrão: atual)")
    parser.add_argument("--base-url", default=os.environ.get("MODPACK_BASE_URL", DEFAULT_BASE_URL),
                        help="URL raw de onde o launcher baixa os arquivos")
    parser.add_argument("--out", default="manifest.json", help="Arquivo de saída")
    parser.add_argument("--bin-root", default=None,
                        help="Pasta raiz das camadas bin (padrão: <pasta do repo>/bin)")
    args = parser.parse_args()

    if args.repo:
        if "/" not in args.repo:
            print(f"ERRO: --repo deve ser user/repo (recebi: {args.repo})", file=sys.stderr)
            return 1
        repo_root = Path(args.repo_root) if args.repo_root else Path(__file__).resolve().parent
        packs = sorted(
            p for p in repo_root.iterdir()
            if p.is_dir() and not p.name.startswith(".") and p.name != "bin"
        )
        if not packs:
            print(f"ERRO: nenhuma pasta de modpack em {repo_root}", file=sys.stderr)
            return 1
        bin_root = Path(args.bin_root) if args.bin_root else repo_root / "bin"
        generated = 0
        for pack_dir in packs:
            base_url = f"https://raw.githubusercontent.com/{args.repo}/{args.branch}/{pack_dir.name}"
            out_path = pack_dir / "manifest.json"
            try:
                index = build_index(pack_dir, base_url, out_path, bin_root)
            except ValueError as exc:
                print(f"  [pulado] {pack_dir.name}: {exc}", file=sys.stderr)
                continue
            write_index(index, out_path)
            generated += 1
            bin_label = index.get("bin", {}).get("url", "")
            print(f"Índice gerado: {out_path.resolve()}")
            print(f"  {pack_dir.name}: {len(index['files'])} arquivos · tracked: {', '.join(index['tracked'])}")
            if bin_label:
                print(f"  bin: {bin_label}")
            print(f"  base_url: {index['base_url']}")
            print(f"  revision: {index['revision']}")
        print(f"\n{generated} modpack(s) indexados. Dê push junto com os arquivos alterados.")
        print("Ex.: git add -A && git commit -m 'update: novo ModA' && git push")
        return 0

    pack_dir = Path(args.dir)
    if not pack_dir.is_dir():
        print(f"ERRO: pasta do modpack não encontrada: {pack_dir}", file=sys.stderr)
        return 1
    out_path = Path(args.out)
    try:
        index = build_index(
            pack_dir, args.base_url, out_path,
            Path(args.bin_root) if args.bin_root else None,
        )
    except ValueError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1
    write_index(index, out_path)
    print(f"Índice gerado: {out_path.resolve()}")
    print(f"  arquivos: {len(index['files'])}  ·  tracked: {', '.join(index['tracked'])}")
    print(f"  base_url: {index['base_url']}")
    print(f"  revision: {index['revision']}")
    print("\nDê push no manifest.json junto com os arquivos alterados.")
    print("Ex.: git add -A && git commit -m 'update: novo ModA' && git push")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
