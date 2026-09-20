# -*- coding: utf-8 -*-
"""
v15 · W2 离线准备 —— A 段参考侧的"同单位受控"重建

为什么要有这个脚本:
    v14 的 A 段参考侧 (spiral_v14_prepare.py) 与模型侧处在完全不同的单位制与相区:

        模型侧  h = L_domain / N     = 0.5 / 36      = 0.013889  每格
        参考侧  h = PHY_SIZE / MESH  = 447.21 / 128  = 3.4939    每格

    每格物理长度差 252 倍, 而 A 段的核心读数 lam_pk 的单位是"格"。相区参数也不同
    (模型 F,k = 0.035/0.060; v14 参考侧 F,k = 0.01/0.042)。两个混杂因子叠加, 使
    A 段报出的 D_struct 无法单独归因。

    W2 按锁定决策走"方案 B · 同单位受控": 参考侧改用与模型侧**逐字相同**的
    (Du, Dv, F, k, L_domain), 只变网格分辨率 N = 36/72/144。dt 随 h^2 同比缩,
    使 stab = dt*Du/h^2 在所有 N 上相同。这样"格"在两侧是同一个物理长度。

这个重建把 A 段变成了什么 (必须说清楚, 否则是自欺):
    两侧现在是同一个方程、同一组参数、同一个盒子, 所以 A 段不再是"与外部数据
    对标", 而是**模型侧自己那个读数的分辨率收敛检验**:
      - N=36 恰是模型侧实际派生的分辨率 (见 spiral_model_v15.derive_L6_grid);
      - N=72/144 是同一物理、更细的网格。
    它能回答的是: 模型侧在 h=0.013889 上读到的 6 个结构描述子是否已经收敛。
    收敛 => A 段读数不含未量化的离散化误差; 不收敛 => 模型侧那个读数带着一个
    此前没被量化的分辨率误差 —— 这是负面事实, 如实登记, 不调参掩盖。

积分器为什么用模型侧自己的:
    spiral_model_v15.stage6_life 用显式欧拉 + 5 点 np.roll 拉普拉斯 (周期边界)。
    本脚本**逐字复刻这套离散化**, 不用 v14 的 ETDRK4 —— 否则积分器又成为新的
    混杂因子。冒烟测试已确认: N=36 同步数下与 stage6_life 的 v/u 逐点差为 0。

边界声明:
    - 离线一次性准备脚本, 不进入模型运行的时间预算。产出
      data/_v15_cache/gs_v15seed.npz, 由 spiral_metric_v15 的 A 段读取。
    - 参考侧**不是独立数据源**, 是同一物理的受控重算。它没有资格回答"模型像
      不像外部实验数据" —— 那个问题在 v14 把 A 段降级为方法学展示后就不再问了。
    - 不掩盖死场: 每个种子都报对比度/活化占比与连续 u 场的标准差。健康判据用
      stage6_life **自己**的 emerged 判据 (对比度>0.2 且 活化>5%), **不搬** v14 的
      MIN_U_STD=0.15。理由见下面第 4 条。
    - **MIN_U_STD=0.15 是 v14 相区的常数, 在本相区失标。** v14 的参数是
      (F,k)=(0.01,0.042), h=3.49, 那里死场 u_std~0.04, 所以 0.15 有余量。本脚本
      换到模型侧相区 (F,k)=(0.035,0.060), h=0.0139 后, 实测健康斑图的 u_std 就落在
      0.1494~0.1548 —— 阈值恰好压在健康场的分布上, 会把对比度 0.35、活化 63% 的
      **健康斑图误判成死场**。搬一个失标的常数过来当门是可证伪性上的错误, 故不用它,
      而用 stage6_life 自己的 emerged 判据 (那才是模型侧的判据)。u_std 仍然照报,
      供读者自行判断。
"""
import json
import os
import sys
import time

import numpy as np

# ---- 与 spiral_model_v15.KNOBS 逐字相同的模型侧参数 (同单位受控的前提) ----
L_DOMAIN = 0.5
DU, DV = 2e-5, 1e-5
F_PARAM, K_PARAM = 0.035, 0.060
DT_REF = 1.0            # N=36 上的时间步, 其余 N 按 (36/N)^2 缩
N_REF = 36              # 模型侧实际派生的分辨率 (h = L_DOMAIN/N_REF)
T_PHYS = 40000.0        # 物理总时长 = 模型侧 steps*dt, 所有 N 相同
STAB_LIMIT = 0.25       # 显式欧拉稳定上界 dt*Du/h^2 <= 1/4

N_LIST = (36, 72, 144)
SEEDS = (0, 1, 2)
# 健康判据来自 stage6_life 的 emerged: 对比度 > 0.2 且 活化面积占比 > 5%。
# 不用 v14 的 MIN_U_STD=0.15 —— 那个常数在模型侧相区失标 (见文件头边界声明)。
EMERGE_CONTRAST, EMERGE_ACTIVE = 0.2, 0.05

OUT_DIR = os.path.join('data', '_v15_cache')
OUT_NPZ = os.path.join(OUT_DIR, 'gs_v15seed.npz')


def _lap(a, h):
    """5 点拉普拉斯, 周期边界 —— 与 stage6_life 内的写法逐字相同。"""
    return (np.roll(a, 1, 0) + np.roll(a, -1, 0) +
            np.roll(a, 1, 1) + np.roll(a, -1, 1) - 4 * a) / h ** 2


def _nucleus(N, seed):
    """初值: 与 stage6_life 逐字同一机制 —— u 背景 1, v 背景 0, 方块 (u=0.5, v=0.25)。

    seed=0 复刻模型侧那个**确定性**初值 (半宽 max(1,N//18), 居中), 与它硬核对。
    seed>0 把同一机制随机化: 方块个数 1..3, 位置随机, 半宽 N//36..N//12。
    **只随机化"核在哪、有几个、多大", 不改变成核机制本身** —— 否则种子间散布里
    就混进了"机制不同", 而它本来是当噪声底用的。
    """
    u = np.ones((N, N))
    v = np.zeros((N, N))
    if seed == 0:
        c, w = N // 2, max(1, N // 18)
        u[c - w:c + w, c - w:c + w] = 0.5
        v[c - w:c + w, c - w:c + w] = 0.25
        return u, v, {'n_nuclei': 1, 'blocks': [[c - w, c - w, w]]}
    rng = np.random.default_rng(1000 + seed)
    n = int(rng.integers(1, 4))
    blocks = []
    for _ in range(n):
        w = max(1, int(round(float(rng.integers(1, 4)) * N / float(N_REF))))
        w = min(w, N // 4)
        r = int(rng.integers(w, N - w))
        c = int(rng.integers(w, N - w))
        u[r - w:r + w, c - w:c + w] = 0.5
        v[r - w:r + w, c - w:c + w] = 0.25
        blocks.append([r - w, c - w, w])
    return u, v, {'n_nuclei': n, 'blocks': blocks}


def _spacing(v, L, N):
    """斑图波长: v 沿 x 的平均零交叉间隔 * 2 —— 与 stage6_life 内的算式逐字相同。"""
    zc = np.mean([len(np.where(np.diff(np.sign(v[i] - v[i].mean())))[0])
                  for i in range(N)])
    return float(2.0 * L / zc) if zc > 0 else float('inf')


def gs_run_v15(N, seed):
    """在分辨率 N 上跑一次受控 Gray-Scott, 返回末态与诊断。

    dt = DT_REF * (N_REF/N)^2, 步数 = T_PHYS/dt, 所以 stab 与物理时长都与 N 无关。
    """
    h = L_DOMAIN / N
    dt = DT_REF * (float(N_REF) / N) ** 2
    stab = dt * DU / h ** 2
    steps = int(round(T_PHYS / dt))
    if stab > STAB_LIMIT:
        # 与 stage6_life 同样的硬拒绝: 不用 clip 掩盖失稳。
        raise RuntimeError(
            f'N={N}: dt*Du/h^2={stab:.4f} > {STAB_LIMIT}, 拒绝给出可能失稳的结果')

    u, v, ic = _nucleus(N, seed)
    for _ in range(steps):
        uv2 = u * v ** 2
        u = u + dt * (DU * _lap(u, h) - uv2 + F_PARAM * (1 - u))
        v = v + dt * (DV * _lap(v, h) + uv2 - (F_PARAM + K_PARAM) * v)

    finite = bool(np.isfinite(u).all() and np.isfinite(v).all())
    if not finite:
        raise RuntimeError(f'N={N} seed={seed}: 出现非有限值 (数值失稳), 拒绝写缓存')
    u_std = float(u.std())
    contrast = float(v.max() - v.min())
    active = float((v > 0.1).mean())
    diag = {'N': N, 'seed': seed, 'h': h, 'dt': dt, 'steps': steps,
            'stab': stab, 'T_phys': steps * dt,
            'contrast': contrast, 'active_frac': active,
            'spacing': _spacing(v, L_DOMAIN, N),
            'u_std': u_std,
            # 与 stage6_life 的 emerged 判据逐字相同, 便于两侧直接对照。
            'emerged': bool(contrast > EMERGE_CONTRAST and active > EMERGE_ACTIVE),
            'ic': ic}
    return u, v, diag


def main():
    smoke = 'smoke' in sys.argv
    t0 = time.perf_counter()
    os.makedirs(OUT_DIR, exist_ok=True)

    print('=' * 72)
    print('  v15 · W2 参考侧"同单位受控"重建')
    print('=' * 72)
    print(f'  与模型侧逐字相同的参数: L={L_DOMAIN}, Du={DU}, Dv={DV}, '
          f'F={F_PARAM}, k={K_PARAM}')
    print(f'  dt 随 h^2 同比缩 (以 N={N_REF} 的 dt={DT_REF} 为基准), '
          f'物理总时长 T={T_PHYS:.0f} 在所有 N 上相同')
    print(f'  分辨率 N ∈ {N_LIST}; 每 N 种子 seed ∈ {SEEDS}')
    print(f'  N={N_REF} 恰为模型侧 derive_L6_grid 派生出的分辨率 -> 可作为硬核对点')
    if smoke:
        print('  ** 冒烟模式: 每 N 只跑 2000 步, 不写缓存 **')

    store, metas = {}, []
    for N in N_LIST:
        h = L_DOMAIN / N
        dt = DT_REF * (float(N_REF) / N) ** 2
        steps = int(round(T_PHYS / dt))
        print(f'\n--- N={N} (h={h:.6f}, dt={dt:.4f}, '
              f'满程 steps={steps}, stab={dt * DU / h ** 2:.5f}) ---')
        for seed in SEEDS:
            ts = time.perf_counter()
            if smoke:
                # 冒烟: 只跑前 2000 步。走的是同一条数值路径, 只是提前停。
                u, v, ic = _nucleus(N, seed)
                for _ in range(2000):
                    uv2 = u * v ** 2
                    u = u + dt * (DU * _lap(u, h) - uv2 + F_PARAM * (1 - u))
                    v = v + dt * (DV * _lap(v, h) + uv2 - (F_PARAM + K_PARAM) * v)
                diag = {'N': N, 'seed': seed, 'h': h, 'dt': dt, 'steps': 2000,
                        'stab': dt * DU / h ** 2, 'T_phys': 2000 * dt,
                        'contrast': float(v.max() - v.min()),
                        'active_frac': float((v > 0.1).mean()),
                        'spacing': _spacing(v, L_DOMAIN, N),
                        'u_std': float(u.std()),
                        'emerged': bool(float(v.max() - v.min()) > EMERGE_CONTRAST
                                        and float((v > 0.1).mean()) > EMERGE_ACTIVE),
                        'ic': ic}
            else:
                u, v, diag = gs_run_v15(N, seed)
            cost = time.perf_counter() - ts

            # 二值化: 与 _binarize_median / v14 prepare 完全相同的中位数规则
            b = v > np.median(v)
            store[f'bool_{N}_{seed}'] = b[np.newaxis, ...]   # (1,N,N), 供 _late_frame
            store[f'v_{N}_{seed}'] = v
            store[f'u_{N}_{seed}'] = u
            diag['cost'] = cost
            diag['phi'] = float(b.mean())
            metas.append(diag)
            print(f'  seed {seed}: {cost:7.2f}s | 对比度 {diag["contrast"]:.4f} | '
                  f'活化占比 {diag["active_frac"]:.4f} | phi {diag["phi"]:.4f} | '
                  f'波长 {diag["spacing"]:.4f} | u_std {diag["u_std"]:.4f} | '
                  f'{"涌现" if diag["emerged"] else "**未涌现**"}')

    store['meta'] = json.dumps(
        {'version': 'v15', 'work_package': 'W2',
         'contract': {'L_domain': L_DOMAIN, 'Du': DU, 'Dv': DV,
                      'F': F_PARAM, 'k': K_PARAM,
                      'dt_ref': DT_REF, 'N_ref': N_REF,
                      'T_phys': T_PHYS, 'stab_limit': STAB_LIMIT,
                      'binarize': 'v > median(v) 逐场',
                      'integrator': '显式欧拉 + 5 点 np.roll 拉普拉斯 (周期)',
                      'N_list': list(N_LIST), 'seeds': list(SEEDS),
                      'nucleus': 'seed=0 复刻 stage6_life 确定性初值; '
                                 'seed>0 同机制随机化 (个数/位置/半宽)'},
         'smoke': smoke,
         'runs': metas},
        ensure_ascii=False)

    if smoke:
        print(f'\n[冒烟] 不写缓存, 用时 {time.perf_counter() - t0:.1f}s')
        return
    np.savez_compressed(OUT_NPZ, **store)
    size_mb = os.path.getsize(OUT_NPZ) / 1e6
    bad = [m for m in metas if not m['emerged']]
    print(f'\n写入 {OUT_NPZ} ({size_mb:.2f} MB), {len(metas)} 个场')
    print(f'  未涌现 (对比度<=0.2 或 活化<=5%): '
          f'{[(m["N"], m["seed"]) for m in bad] if bad else "无"}')
    print(f'  总用时 {time.perf_counter() - t0:.1f}s')


if __name__ == '__main__':
    main()
