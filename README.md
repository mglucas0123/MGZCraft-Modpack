# MGZCraft Modpacks

Repositório oficial de modpacks da rede **MGZCraft**.

Cada pasta deste repositório é um modpack. O Launcher MGZCraft sincroniza
automaticamente os arquivos: quando um mod ou config é atualizado aqui, os
jogadores baixam **apenas o que mudou** na próxima vez que clicarem em Jogar.

## Estrutura

```
MGZCraft-Modpack/
├── bin/<versao>.zip      ← camada base do Minecraft em ZIP único (minecraft.jar,
│                            json de versão, natives) — compartilhado pelos modpacks
├── bin/src/<versao>/     ← pasta de origem do ZIP (local, NÃO vai pro git)
├── <modpack>/            ← cada pasta é um modpack
│   ├── mods/             ← mods (modpack.jar = Forge fica aqui)
│   ├── config/
│   ├── resourcepacks/
│   ├── shaderspacks/
│   ├── pack.json         ← metadado: {"bin": "1.7.10"} (versão da camada base)
│   └── manifest.json     ← índice delta (gerado — NÃO editar à mão)
├── update_index.py       ← script que gera os manifest.json e o ZIP do bin
└── README.md
```

## Como atualizar um modpack

1. Altere os arquivos na pasta do modpack (mods/, config/, etc.)
2. Rode o script interativo em PowerShell:
   ```powershell
   .\gerar-manifest.ps1
   ```
   *Ou direto com a mensagem de commit:*
   ```powershell
   .\gerar-manifest.ps1 "update: novos mods adicionados"
   ```
3. Alternativamente (via comando manual):
   - `python update_index.py --repo mglucas0123/MGZCraft-Modpack`
   - `git add -A; git commit -m "update: ..."; git push`

Pronto — na próxima vez que os jogadores abrirem o jogo, o launcher baixa somente os arquivos alterados.

## Modpacks disponíveis

| Modpack | Pasta | Camada base |
|---|---|---|
| OreSpawn Resurgence | `OreSpawn-Resurgence/` | `bin/1.7.10` |

## Baixar o launcher

- **Windows**, **Linux** e **Mobile (Android)**: [https://mgzcraft.duckdns.org/](https://mgzcraft.duckdns.org/)
- **iOS**: em construção.

Mods e assets pertencem aos seus respectivos autores. A licença deste
repositório cobre apenas os arquivos próprios (script e documentação).
