# MHGU Mod Maker — 工作区说明

面向 **MHGURecomp**（RTHKKona 的原生 PC 移植版）的 MHGU mod 制作环境。
所有工具、原始资源、中间产物均集中在本目录，与游戏目录分离。

创建时间：2026-11-02　｜　游戏：Monster Hunter Generations Ultimate（Title ID `0100770008DD8000`）

---

## 目录结构

```
D:\MHGU mod maker\
├── 00_Tools\                        工具链（约 200 MB）
│   ├── 01_Arc_SaladSoftware\        SaladSoftware 2.4.2 —— .arc 解包 / 高保真回封
│   ├── 02_Texture_SoupTextures\     TEX 编解码（含修正版 mhgu_tex.py + texconv.exe）
│   ├── 02_Texture_MHGUTexTool\      MHGU Tex Tool —— 按名批量替换贴图（备用）
│   ├── 04_Audio_IFRIT\              HBMK IFRIT v0.1.1 —— 音频转换 / 循环点 / Opus
│   ├── 05_venv\                     独立 Python 3.13 + Pillow + numpy
│   └── 90_Reference_MHGU-Modding\   官方社区资料（音频库、文件类型表、arc 清单）
├── 01_Original_romfs\romfs\         原始 romfs 只读副本（35,531 个文件 / 11.47 GB）
├── 02_Workspace\                    解包与编辑区（可随时清空）
├── 03_Output\                       成品 mod 目录（部署源）
├── 90_Backup\                       load_order 备份、旧 arc 备份
├── bin\                             Python 脚本（部署 / 转换 / 自检）
├── 0_Check_Env.bat                  环境自检
├── 1_Unpack_Arc.bat                 解包 arc（拖拽）
├── 2_Repack_Arc.bat                 回封 arc（拖拽）
├── 3_Tex_To_Png.bat                 TEX → PNG（拖拽）
├── 4_Png_To_Tex.bat                 PNG → TEX（拖拽）
└── 5_Deploy_Mod.bat                 部署 mod 到游戏（拖拽）
```

---

## 核心机制（务必先理解这条）

MHGURecomp 的 mod 加载是 **文件级覆盖 + 加载顺序**：

- 游戏读 `mods/<名字>/romfs/nativeNX/...`，路径必须与原版完全一致
- `mods/load_order.txt` 决定覆盖次序：**同一文件，越靠后（越下面）的 mod 生效**
- `# off: <名字>` 表示该 mod 存在但关闭
- 未列入 load_order 的新文件夹默认排在最后

因此：**一个 mod 只放你真正改过的文件**。放整个 `nativeNX`（数十 GB）会拖慢加载且极易冲突。

---

## 标准工作流（以改贴图为 example）

### 1. 解包目标 arc

把 `...\nativeNX\arc\enemy\em001_00.arc` 拖到 `1_Unpack_Arc.bat`。
产物：同目录出现 `em001_00_arc\` 文件夹（549 个文件，含 .tex / .mod / .mrl / .mca）。

> 建议始终在 `02_Workspace` 里操作副本，原始 romfs 保持只读。

### 2. TEX → PNG

把目标 `.tex`（或整个文件夹）拖到 `3_Tex_To_Png.bat`。
PNG 输出到 `.tex` 同目录。

### 3. 在 PS / GIMP 里编辑 PNG

- **尺寸必须与原贴图完全一致**（脚本会拒绝尺寸不符的文件）
- 不要改变贴图布局，只改颜色/细节
- 保留 alpha 语义（部分贴图的 alpha 是遮罩）

### 4. PNG → TEX

把改好的 PNG 拖到 `4_Png_To_Tex.bat`。
脚本自动使用同目录同名 `.tex` 作为格式模板（继承格式、alpha 标志、mip 链）。
若同目录没有，会提示你指定原始 `.tex`。

### 5. 回封 arc

把 `em001_00_arc\` 文件夹拖到 `2_Repack_Arc.bat`。
要求：原始 `em001_00.arc` 与该文件夹同目录。工具只重压缩改动过的文件，其余字节原样沿用。

### 6. 组装 mod

```
03_Output\MyModName\romfs\nativeNX\arc\enemy\em001_00.arc
```

### 7. 部署

把 `03_Output\MyModName` 拖到 `5_Deploy_Mod.bat`。
脚本复制到游戏 `mods\` 并追加到 `load_order.txt` 末尾。
撤销：`python bin\deploy_mod.py "<路径>" --remove`。

---

## 工具清单与能力边界

| 环节 | 状态 | 说明 |
|---|---|---|
| `.arc` 解包 / 回封 | ✅ | SaladSoftware 2.4.2，支持部分注入与高保真回封 |
| `.tex` 编解码 | ✅ | 已修正上游缺陷，支持 DXT1 / DXT5 / ATI1 / ATI2 / BGRA8888 |
| 音频（Opus / MCA / ADPCM） | ✅ 待用 | HBMK IFRIT，需自己走 `HBMK_IFRIT_HUB.bat` |
| 批量同名贴图替换 | ✅ 备用 | MHGU Tex Tool（.NET 程序，需 NI 运行时） |
| 数值 / 平衡表 | ❌ 缺 | 需自行逆向 `.user` 等二进制表，可参考 `MHGU-Rebalanced-Mod` |
| 模型（.mod / .mrl） | ❌ 缺 | 需 Blender + MT Framework 导入插件，生态薄弱 |
| 任务 / 文本 | ❌ 缺 | `.gmd` / STQR 可用 IFRIT 内 STQREditor.html 处理 |
| 从 NSP 提取 romfs | 不需要 | 你已有 romfs，故未装 hactoolnet |

---

## 已实测验证的结论（2026-11-02）

| 验证项 | 结果 |
|---|---|
| swizzle 闭环（5 种格式 × 4 种尺寸） | 全部字节一致 |
| BGRA8888 贴图往返 | 字节完全一致（无损路径） |
| DXT5 1024×1024 / 11 mip 往返 | mip 链完整保留，文件等长 |
| ATI1 字体图集解码 | 拉丁 / 西里尔 / 日文汉字全部正确还原 |
| 修改 → 回封 → 解包 全链路 | 549 个文件中仅目标 1 个变化，其余 md5 完全一致 |
| 贴图色差 | 平均 1.44/255（纯 DXT5 量化误差） |
| 部署 / 撤销 | load_order 撤销后与备份完全一致 |

### 一个关键修正

上游 SoupTextures 的 deswizzle 序列被写死为 512 个块（等价于仅支持 16 字节/块），
导致 ATI1（8B）、BGRA8888（4B）解码报错或出条纹伪影 —— 而 MHGU 的怪物 arc 里
BGRA8888 占 64/67。
本工作区的 `mhgu_tex.py` 改为按硬件真实的 **16 字节块粒度** 构造置换，
并对任意块大小严格可逆，已用字体图集与 DXT5 原生结果交叉验证。

---

## 已知坑

1. **回封会生成 `xxx_original.arc` 备份**：若该文件已存在，工具会直接报错退出。
   `2_Repack_Arc.bat` 已自动把旧备份移到 `90_Backup\`。
2. **只替换 mip0**：mip1..N 沿用原文件字节，远处观察时细节仍是原色。若需完全一致，
   需要自行重采样各级 mip（当前未实现）。
3. **尺寸不可变**：改尺寸会破坏 UV 与 mip 链，工具会拒绝。
4. **回封后体积可能略变**（压缩器差异），属正常，不影响游戏读取。
5. **不要在 Mod 里放整个 nativeNX**：只放改动文件。
6. **改数值 / 判定的 mod 不要联机**（此点对 Recomp 同样适用）。

---

## 常用命令

```bat
:: 环境自检（15 项）
0_Check_Env.bat

:: 手动调用 TEX 工具
00_Tools\05_venv\Scripts\python.exe 00_Tools\02_Texture_SoupTextures\soup_tex_cli.py info <tex或目录>
00_Tools\05_venv\Scripts\python.exe 00_Tools\02_Texture_SoupTextures\soup_tex_cli.py tex2png <tex或目录> --out <输出目录>
00_Tools\05_venv\Scripts\python.exe 00_Tools\02_Texture_SoupTextures\soup_tex_cli.py selftest

:: 部署 / 移除
00_Tools\05_venv\Scripts\python.exe bin\deploy_mod.py "D:\MHGU mod maker\03_Output\MyMod"
00_Tools\05_venv\Scripts\python.exe bin\deploy_mod.py "D:\MHGU mod maker\03_Output\MyMod" --remove
```

---

## 参考资料

- `00_Tools\90_Reference_MHGU-Modding\` —— 音频数据库（xlsx/csv）、`MHGU-Filetypes_Hashes.txt`（文件类型对照）、`MHGU_Extractedarc.txt`（arc 内容清单）
- 上游项目：`RTHKKona/SaladSoftware`、`RTHKKona/SoupTextures`、`RTHKKona/HBMK-IFRIT`、`RTHKKona/MHGURecomp`
- 成品 mod 结构参考：`Monkbreh/MHGU-HD-Project`、`Potobc/MHGU-Rebalanced-mod`

---

## 边界

仅对自己 dump 的游戏资源做修改；对外分享时只发布改动后的差异文件，不打包游戏原始资源。
