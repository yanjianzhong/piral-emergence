# v14.0 — 七阶段涌现计算框架（数值实验可复现版本）

**Release date**: 2026-09-17

**Status**: 个人独立研究 / 数值实验发布（**非同行评审，非 TOE 宣称**）

**定位**："模拟事实地基"阶段 —— 每一层都带量化守卫、负对照与诚实边界。

---

## 一、这个版本是什么

一个从**量子真空叠加**一路推到**意识自指**的七阶段离散演化框架的完整可复现快照：

| 阶段 | 内容 | v14 状态 |
|------|------|----------|
| L1 | 真空等权叠加、多种子分布诊断 | ✅ 成熟 |
| L2 | 横场 Ising 临界点、Schmidt 谱、纠缠诊断 | ✅ 成熟 |
| L3 | 幂迭代 / 递归网络自指、秩1化 | 🔶 强但 N 依赖 |
| L4 | MERA 全息压缩、尺度诊断 | 🔶 方法学 |
| L5 | 离散曲率 / 图几何映射 | ⚠️ 归因未完成 |
| L6 | Gray-Scott 反应扩散斑图 | 🔶 部分手设参数 |
| L7 | 二阶自指"照见空无" | ❌ 约定值，非物理证据 |

详见 `spiral_v14_audit.md`（七阶段模拟事实审计表）。

---

## 二、目录结构

```
.
├── README.md                     # 项目说明（叙事 × 数值 × 诚实边界）
├── spiral_model_v14.py           # 核心模型 L1–L4：真空/Ising/自指/MERA
├── spiral_metric_v14.py         # 指标与守卫：七阶段量化审计、负对照
├── spiral_v14_prepare.py        # 数据/种子准备（参考侧自建种子由此生成）
├── spiral_v14_audit.md          # 七阶段审计表（成熟度 + 诚实边界 + 理论接口）
├── spiral_v14_说明.md           # 中文补充说明
├── spiral_v14_Release.md        # 本文件
├── _v14_run.log                 # 完整运行日志（EXIT=0，守卫 39/40）
│
├── data/
│   ├── _v13_cache/              # v13 历史缓存（保留用于对照，不参与 v14 主流程）
│   │   ├── bz_reading.npz
│   │   ├── bz_soton.npz
│   │   └── clip_gs.npz
│   └── _v14_cache/              # v14 主缓存
│       ├── archive_provenance.json   # 存档来源/生成记录（可复现溯源）
│       └── gs_seeds.npz              # Gray-Scott 初始种子
│
└── result/
    ├── spiral_v14.png            # 主演化示意图
    ├── spiral_v14_metrics.png    # 指标汇总图
    ├── _v14_data.json            # 指标数值导出（供审计表引用）
    └── _v14_hj_scan.png          # H-J 参数扫描图
```

> **说明**：`data/_v13_cache/` 为历史对照数据，**v14 主流程不依赖它**；若只复现 v14，可忽略该目录。`data/_v14_cache/` 与 `result/` 由 `spiral_v14_prepare.py` 与主脚本运行后生成/读取。

---

## 三、安装与依赖

要求 **Python 3.10+**。

```bash
git clone https://github.com/yanjianzhong/piral-emergence-v14.git
cd piral-emergence-v14
```

主要依赖：`numpy`、`scipy`、`matplotlib`，以及 MERA 阶段用到的张量网络库（如 `quimb`）。

---

## 四、如何复现


```bash
# 数据源说明
1、Southampton · BZ 油滴网络时空图（Figure_3/4/6.zip、Figure_S1/S2/S3.zip,D0363_readme.txt）
链接：https://doi.org/10.5258/SOTON/D0363
内容：Figure_3 全时空图、Figure_4/6、Figure_S1 等 7 个压缩包；主包 Figure_S1 约 64MB，Figure_3 约 10MB
格式：归档 zip，含提取波特征的步骤说明
适合：时空图→单帧二值化→Betti/欧拉/波前密度；油滴网络可用于“连通域/空洞”统计
授权：CC BY；配套论文 Scientific Reports 2018, 10.1038/s41598-018-30819-6
2. Reading · BZ 自振荡水凝胶延时影像（T_Geher-Herczegh_PhD_Exp_data.zip，1.57GB）
链接：https://researchdata.reading.ac.uk/467 （DOI 10.17864/1947.000467）
内容：131 个延时序列，USB 显微镜拍摄，不同凝胶尺寸/几何、催化剂自由 BZ 溶液、不同压缩频率
格式：延时图像序列
适合：单通道灰度→阈值→持久同调；机械刺激下波/斑图演化、节律统计
授权：CC BY 4.0；体量按序列选，
3，CLIP 反应-扩散基准（gray_scott_data.tar.gz，442MB）
链接：https://zenodo.org/records/18345087
内容：gray_scott_data.tar.gz 约 442MB、lambda_omega 约 184MB、其余为 Lotka/MinDE；NumPy npz
适合：直接替换阶段六 v 场做“同模型不同参数”的结构对标；Betti/空洞/波长/活化面积可全内部验证
优点：格式干净、2D 网格、可复现；缺点是不算“实验”，论文里只能叫数值基

# 1. 准备数据与种子
python spiral_v14_prepare.py


# 2. 运行核心模型（L1–L4）+ 指标守卫
python spiral_model_v14.py
```

- 结果写入 `result/`（`_v14_data.json`、`spiral_v14.png` 等）
- 完整日志见 `_v14_run.log`
- **v14 目标运行基线：`EXIT=0`，守卫 39/40 通过**；未通过项在日志与审计表中明确记录为已知限制，非静默失败
- 审计表：`spiral_v14_audit.md`

> 所有随机种子与参考侧种子均由 `spiral_v14_prepare.py` 再生，确保 `result/` 可完整复现。

---

## 五、诚实边界与已知问题（重点）

详见 `spiral_v14_audit.md`，此处摘录：

- **第三层（L4→L5）结构对标降级为方法学展示**，不设物理达标线；A 段两盒子轴语义不同、B 段参考侧污染导致 `passed=None`，桥梁为空
- **参考侧用 v14 自建种子**，双侧均按 `v > median` 二值化 → `phi` 在此规则下趋于 0.5，视为**诊断恒等式，非独立度量**
- **`_char_scale` 峰值波长 `lam_pk` 缺乏独立外部校准**，仅作记录性诊断，非尺度锚点
- **读序周期检测未发现显著周期**，如实报告为"未检出"，非缺失数据
- **N=17 秩1化依赖特定尺寸**，普适性未建立（v15 P0）
- 有限尺寸截断、`max_L` 上限、负对照覆盖度，逐阶段记录于审计表

### 负对照设计

指标脚本在可行处包含改变控制（不同 χ / 预算诊断、替代种子分布、临界 vs 非临界对照），检验各指标在机制缺失时是否正确失效。定义见 `spiral_metric_v14.py` 与审计表。

---

## 六、存档与引用

本 GitHub Release 可通过 **Zenodo–GitHub 集成** 自动归档并获版本 DOI：

- Code: `https://github.com/yanjianzhong/piral-emergence/releases/tag/v14`
- Archive DOI: `https://doi.org/10.5281/zenodo.22810162`  
- 审计表：`spiral_v14_audit.md`（仓库根目录）

**引用建议（论文/README 中）**：

> Code and audit tables: GitHub release v14.0 [link]; archived with Zenodo DOI [doi]; audit table `spiral_v14_audit.md`.

`CITATION.cff`（如后续添加）示例：


## License

**MIT**

---

## 七、下一步（v15）

| 优先级 | 任务 |
|--------|------|
| P0 | N 参数扫描，验证秩1自指的普适条件 |
| P0 | L4→L5 归因桥梁：固定 f/k 的受控盒子实验 |
| P1 | L7"照见"的可测量化（整合信息 / 自指深度） |
| P1 | 负对照系统化（逐层"机制不存在时会怎样"） |
| P2 | 去掉 `max_L` 截断，改用 ξ/L 无量纲收敛 |

本版本面向**开放复现与同行检验**，不构成最终理论断言。
变化以周期性偏振，统一于空无；
增长以螺旋式上升，起始于终结。
